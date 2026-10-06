import json
import os
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import delete, inspect, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from riskdesk_ai import models
from riskdesk_ai.database import create_database_engine, get_db
from riskdesk_ai.main import app
from riskdesk_ai.services.audit_service import AuditService

pytestmark = pytest.mark.integration


def required_test_url(name: str) -> str:
    value = os.getenv(name)
    if not value:
        pytest.skip(f"{name} is required for PostgreSQL integration tests")

    parsed = make_url(value)
    if parsed.get_backend_name() != "postgresql" or "test" not in (parsed.database or ""):
        pytest.fail(f"{name} must identify a PostgreSQL database whose name contains 'test'")
    return value


@pytest.fixture(scope="session")
def postgres_urls() -> tuple[str, str]:
    return (
        required_test_url("RISKDESK_TEST_DATABASE_URL"),
        required_test_url("RISKDESK_TEST_MIGRATION_DATABASE_URL"),
    )


@pytest.fixture(scope="session")
def migrated_postgres(postgres_urls: tuple[str, str]) -> Generator[str, None, None]:
    application_url, migration_url = postgres_urls
    previous_url = os.environ.get("RISKDESK_MIGRATION_DATABASE_URL")
    os.environ["RISKDESK_MIGRATION_DATABASE_URL"] = migration_url
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))

    command.downgrade(config, "base")
    command.upgrade(config, "head")
    try:
        yield application_url
    finally:
        if previous_url is None:
            os.environ.pop("RISKDESK_MIGRATION_DATABASE_URL", None)
        else:
            os.environ["RISKDESK_MIGRATION_DATABASE_URL"] = previous_url


@pytest.fixture()
def postgres_client(
    migrated_postgres: str,
    auth_headers: dict[str, str],
) -> Generator[TestClient, None, None]:
    engine = create_database_engine(migrated_postgres)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with testing_session() as db:
        db.execute(delete(models.AuditLog))
        db.execute(delete(models.RiskCase))
        db.execute(delete(models.Event))
        db.commit()

    def override_get_db() -> Generator[Session, None, None]:
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, headers=auth_headers) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


def test_migrations_create_the_postgresql_schema(migrated_postgres: str) -> None:
    engine = create_database_engine(migrated_postgres)
    try:
        database_inspector = inspect(engine)
        assert {"alembic_version", "audit_logs", "events", "risk_cases"}.issubset(
            database_inspector.get_table_names(),
        )
        index_names = {
            index["name"] for index in database_inspector.get_indexes("risk_cases")
        }
        assert {
            "ix_risk_cases_queue",
            "ix_risk_cases_recommended_action",
        }.issubset(index_names)
        risk_case_columns = {
            column["name"] for column in database_inspector.get_columns("risk_cases")
        }
        assert "version" in risk_case_columns
    finally:
        engine.dispose()


def seed_case_queue(client: TestClient) -> tuple[int, int]:
    medium_response = client.post(
        "/api/v1/simulator/run",
        json={
            "scenario": "high_value_withdrawal_incomplete_kyc",
            "player_id": "plr_pg_medium",
        },
    )
    assert medium_response.status_code == 200
    medium_case_id = medium_response.json()["case_ids"][0]

    high_response = client.post(
        "/api/v1/simulator/run",
        json={"scenario": "high_risk_country_withdrawal", "player_id": "plr_pg_high"},
    )
    assert high_response.status_code == 200
    high_case_id = high_response.json()["case_ids"][-1]

    hold_response = client.post(
        f"/api/v1/cases/{medium_case_id}/decision",
        json={"action": "hold", "expected_version": 1},
    )
    assert hold_response.status_code == 200
    return medium_case_id, high_case_id


def test_postgresql_combined_case_filters(postgres_client: TestClient) -> None:
    medium_case_id, _ = seed_case_queue(postgres_client)

    response = postgres_client.get(
        "/api/v1/cases",
        params={
            "status": "on_hold",
            "risk_level": "MEDIUM",
            "player_id": "plr_pg_medium",
            "recommended_action": "manual_review",
        },
    )

    assert response.status_code == 200
    assert [risk_case["id"] for risk_case in response.json()] == [medium_case_id]


def test_postgresql_decision_and_audit_persist_across_sessions(
    postgres_client: TestClient,
    migrated_postgres: str,
) -> None:
    medium_case_id, _ = seed_case_queue(postgres_client)

    engine = create_database_engine(migrated_postgres)
    try:
        with Session(engine) as db:
            risk_case = db.get(models.RiskCase, medium_case_id)
            audit_log = db.scalars(
                select(models.AuditLog)
                .where(models.AuditLog.action == "case_decision_recorded")
                .where(models.AuditLog.entity_id == medium_case_id),
            ).one()

            assert risk_case is not None
            assert risk_case.status == "on_hold"
            details = json.loads(audit_log.details)
            assert details["previous_status"] == "open"
            assert details["new_status"] == "on_hold"
            assert details["actor"] == "portfolio_operator"
            assert details["version"] == 2
    finally:
        engine.dispose()


def test_postgresql_rolls_back_case_update_when_audit_write_fails(
    postgres_client: TestClient,
    migrated_postgres: str,
    monkeypatch: pytest.MonkeyPatch,
    auth_headers: dict[str, str],
) -> None:
    medium_case_id, _ = seed_case_queue(postgres_client)

    def fail_audit_write(*args: object, **kwargs: object) -> None:
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr(AuditService, "record", fail_audit_write)
    with TestClient(
        app,
        headers=auth_headers,
        raise_server_exceptions=False,
    ) as non_raising_client:
        response = non_raising_client.post(
            f"/api/v1/cases/{medium_case_id}/decision",
            json={"action": "escalate", "expected_version": 2},
        )
    assert response.status_code == 500

    engine = create_database_engine(migrated_postgres)
    try:
        with Session(engine) as db:
            risk_case = db.get(models.RiskCase, medium_case_id)
            assert risk_case is not None
            assert risk_case.status == "on_hold"
            assert risk_case.version == 2
            decision_logs = db.scalars(
                select(models.AuditLog)
                .where(models.AuditLog.action == "case_decision_recorded")
                .where(models.AuditLog.entity_id == medium_case_id),
            ).all()
            assert len(decision_logs) == 1
            assert all(json.loads(log.details)["action"] != "escalate" for log in decision_logs)
    finally:
        engine.dispose()


def test_postgresql_allows_only_one_concurrent_decision(
    postgres_client: TestClient,
    migrated_postgres: str,
) -> None:
    simulator_response = postgres_client.post(
        "/api/v1/simulator/run",
        json={
            "scenario": "high_value_withdrawal_incomplete_kyc",
            "player_id": "plr_pg_concurrent",
        },
    )
    assert simulator_response.status_code == 200
    case_id = simulator_response.json()["case_ids"][0]

    def decide(action: str) -> tuple[int, dict[str, object]]:
        response = postgres_client.post(
            f"/api/v1/cases/{case_id}/decision",
            json={"action": action, "expected_version": 1},
        )
        return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(decide, ("hold", "escalate")))

    assert sorted(status_code for status_code, _ in results) == [200, 409]
    conflict = next(body for status_code, body in results if status_code == 409)
    assert conflict["detail"] == "Case changed since it was loaded; refresh and try again"

    engine = create_database_engine(migrated_postgres)
    try:
        with Session(engine) as db:
            risk_case = db.get(models.RiskCase, case_id)
            assert risk_case is not None
            assert risk_case.version == 2
            assert risk_case.status in {"on_hold", "escalated"}
            decision_logs = db.scalars(
                select(models.AuditLog)
                .where(models.AuditLog.action == "case_decision_recorded")
                .where(models.AuditLog.entity_id == case_id),
            ).all()
            assert len(decision_logs) == 1
    finally:
        engine.dispose()


def test_postgresql_routes_reject_unauthorized_requests(
    postgres_client: TestClient,
) -> None:
    with TestClient(app) as unauthenticated_client:
        responses = [
            unauthenticated_client.get("/api/v1/cases"),
            unauthenticated_client.post(
                "/api/v1/cases/1/decision",
                json={"action": "hold", "expected_version": 1},
            ),
        ]

    assert all(response.status_code == 401 for response in responses)
    assert all(
        response.json() == {"detail": "Invalid operator credentials"} for response in responses
    )
