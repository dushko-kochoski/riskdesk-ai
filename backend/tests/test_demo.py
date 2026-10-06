from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from riskdesk_ai.database import Base, get_db
from riskdesk_ai.main import app


@pytest.fixture()
def client(auth_headers: dict[str, str]) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, headers=auth_headers) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_demo_reset_removes_events_cases_and_audit_logs(client: TestClient) -> None:
    simulator_response = client.post(
        "/api/v1/simulator/run",
        json={
            "scenario": "high_value_withdrawal_incomplete_kyc",
            "player_id": "plr_reset_test",
        },
    )
    assert simulator_response.status_code == 200

    reset_response = client.post("/api/v1/demo/reset")

    assert reset_response.status_code == 200
    body = reset_response.json()
    assert body["status"] == "reset_complete"
    assert body["deleted"]["events"] == 3
    assert body["deleted"]["cases"] == 1
    assert body["deleted"]["audit_logs"] > 0
    assert body["deleted"]["triggered_rules"] > 0

    assert client.get("/api/v1/events").json() == []
    assert client.get("/api/v1/cases").json() == []
    assert client.get("/api/v1/audit-logs").json() == []


def test_demo_seed_creates_expected_events_and_cases(client: TestClient) -> None:
    response = client.post("/api/v1/demo/seed")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "seed_complete"
    assert body["scenarios_run"] == 4
    assert body["events_created"] == 14
    assert body["cases_created"] == 4

    summary_response = client.get("/api/v1/dashboard/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["total_events"] == 14
    assert summary["total_cases"] == 4


def test_demo_seed_includes_all_case_ids(client: TestClient) -> None:
    response = client.post("/api/v1/demo/seed")

    assert response.status_code == 200
    body = response.json()
    assert len(body["case_ids"]) == body["cases_created"]

    listed_case_ids = {risk_case["id"] for risk_case in client.get("/api/v1/cases").json()}
    assert set(body["case_ids"]) == listed_case_ids
