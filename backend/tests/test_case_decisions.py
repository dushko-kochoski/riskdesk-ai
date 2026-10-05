import json
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from riskdesk_ai.database import Base, get_db
from riskdesk_ai.main import app


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_case(client: TestClient) -> int:
    response = client.post(
        "/api/v1/simulator/run",
        json={
            "scenario": "high_value_withdrawal_incomplete_kyc",
            "player_id": "plr_decision_test",
        },
    )
    assert response.status_code == 200
    return response.json()["case_ids"][0]


def test_hold_decision_updates_case_status_to_on_hold(client: TestClient) -> None:
    case_id = create_case(client)

    response = client.post(
        f"/api/v1/cases/{case_id}/decision",
        json={
            "action": "hold",
            "analyst": "demo_analyst",
            "note": "High withdrawal with incomplete KYC. Holding for review.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == case_id
    assert body["action"] == "hold"
    assert body["previous_status"] == "open"
    assert body["new_status"] == "on_hold"
    assert body["analyst"] == "demo_analyst"
    assert body["note"] == "High withdrawal with incomplete KYC. Holding for review."

    case_response = client.get(f"/api/v1/cases/{case_id}")
    assert case_response.status_code == 200
    assert case_response.json()["status"] == "on_hold"


def test_escalate_decision_updates_case_status_to_escalated(client: TestClient) -> None:
    case_id = create_case(client)

    response = client.post(
        f"/api/v1/cases/{case_id}/decision",
        json={"action": "escalate"},
    )

    assert response.status_code == 200
    assert response.json()["new_status"] == "escalated"

    case_response = client.get(f"/api/v1/cases/{case_id}")
    assert case_response.status_code == 200
    assert case_response.json()["status"] == "escalated"


def test_unsupported_decision_action_returns_400(client: TestClient) -> None:
    case_id = create_case(client)

    response = client.post(
        f"/api/v1/cases/{case_id}/decision",
        json={"action": "defer"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported case decision action: defer"}


def test_missing_case_decision_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/cases/999/decision",
        json={"action": "hold"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Risk case not found"}


def test_decision_creates_audit_log(client: TestClient) -> None:
    case_id = create_case(client)

    decision_response = client.post(
        f"/api/v1/cases/{case_id}/decision",
        json={"action": "request_kyc", "analyst": "ops_analyst", "note": "Need documents."},
    )
    assert decision_response.status_code == 200
    audit_log_id = decision_response.json()["audit_log_id"]

    audit_response = client.get("/api/v1/audit-logs")

    assert audit_response.status_code == 200
    decision_logs = [
        log
        for log in audit_response.json()
        if log["action"] == "case_decision_recorded" and log["id"] == audit_log_id
    ]
    assert len(decision_logs) == 1

    details = json.loads(decision_logs[0]["details"])
    assert details == {
        "case_id": case_id,
        "action": "request_kyc",
        "previous_status": "open",
        "new_status": "pending_kyc",
        "analyst": "ops_analyst",
        "note": "Need documents.",
    }
