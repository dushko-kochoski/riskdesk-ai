from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from riskdesk_ai.database import Base, get_db
from riskdesk_ai.main import app

EXPECTED_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH"}
EXPECTED_STATUSES = {
    "open",
    "on_hold",
    "escalated",
    "pending_kyc",
    "rejected",
    "false_positive",
    "closed",
    "resolved",
}


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


def test_empty_database_returns_zero_summary_with_expected_keys(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total_events": 0,
        "total_cases": 0,
        "open_cases": 0,
        "high_risk_cases": 0,
        "on_hold_cases": 0,
        "escalated_cases": 0,
        "cases_by_risk_level": {"LOW": 0, "MEDIUM": 0, "HIGH": 0},
        "cases_by_status": {
            "open": 0,
            "on_hold": 0,
            "escalated": 0,
            "pending_kyc": 0,
            "rejected": 0,
            "false_positive": 0,
            "closed": 0,
            "resolved": 0,
        },
        "prevented_exposure_estimate": 0.0,
        "recent_audit_logs": [],
    }


def test_summary_after_simulator_counts_events_and_cases(client: TestClient) -> None:
    simulator_response = client.post(
        "/api/v1/simulator/run",
        json={"scenario": "high_value_withdrawal_incomplete_kyc"},
    )
    assert simulator_response.status_code == 200

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["total_events"] >= 3
    assert body["total_cases"] >= 1
    assert body["open_cases"] >= 1
    assert body["cases_by_risk_level"]["MEDIUM"] >= 1
    assert "prevented_exposure_estimate" in body
    assert "recent_audit_logs" in body


def test_summary_after_hold_decision_counts_on_hold_cases_and_exposure(
    client: TestClient,
) -> None:
    simulator_response = client.post(
        "/api/v1/simulator/run",
        json={"scenario": "high_value_withdrawal_incomplete_kyc"},
    )
    assert simulator_response.status_code == 200
    case_id = simulator_response.json()["case_ids"][0]

    decision_response = client.post(
        f"/api/v1/cases/{case_id}/decision",
        json={"action": "hold", "expected_version": 1},
    )
    assert decision_response.status_code == 200

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["on_hold_cases"] == 1
    assert body["cases_by_status"]["on_hold"] == 1
    assert body["prevented_exposure_estimate"] == 2500


def test_prevented_exposure_increases_after_escalating_withdrawal_case(
    client: TestClient,
) -> None:
    simulator_response = client.post(
        "/api/v1/simulator/run",
        json={"scenario": "high_value_withdrawal_incomplete_kyc"},
    )
    assert simulator_response.status_code == 200
    case_id = simulator_response.json()["case_ids"][0]

    before_response = client.get("/api/v1/dashboard/summary")
    assert before_response.status_code == 200
    assert before_response.json()["prevented_exposure_estimate"] == 0

    decision_response = client.post(
        f"/api/v1/cases/{case_id}/decision",
        json={"action": "escalate", "expected_version": 1},
    )
    assert decision_response.status_code == 200

    after_response = client.get("/api/v1/dashboard/summary")
    assert after_response.status_code == 200
    assert after_response.json()["prevented_exposure_estimate"] == 2500


def test_recent_audit_logs_returns_latest_logs(client: TestClient) -> None:
    simulator_response = client.post(
        "/api/v1/simulator/run",
        json={"scenario": "high_value_withdrawal_incomplete_kyc"},
    )
    assert simulator_response.status_code == 200
    case_id = simulator_response.json()["case_ids"][0]

    decision_response = client.post(
        f"/api/v1/cases/{case_id}/decision",
        json={"action": "hold", "expected_version": 1},
    )
    assert decision_response.status_code == 200

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    recent_audit_logs = response.json()["recent_audit_logs"]
    assert len(recent_audit_logs) == 5
    assert recent_audit_logs[0]["action"] == "case_decision_recorded"
    assert {"id", "action", "entity_type", "entity_id", "details", "created_at"}.issubset(
        recent_audit_logs[0],
    )


def test_summary_includes_all_risk_levels_even_if_zero(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    assert set(response.json()["cases_by_risk_level"]) == EXPECTED_RISK_LEVELS


def test_summary_includes_all_statuses_even_if_zero(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    assert set(response.json()["cases_by_status"]) == EXPECTED_STATUSES
