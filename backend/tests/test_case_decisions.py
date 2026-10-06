import json
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


def create_case(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/simulator/run",
        json={
            "scenario": "high_value_withdrawal_incomplete_kyc",
            "player_id": "plr_decision_test",
        },
    )
    assert response.status_code == 200
    case_id = response.json()["case_ids"][0]
    return client.get(f"/api/v1/cases/{case_id}").json()


def test_hold_decision_updates_case_status_to_on_hold(client: TestClient) -> None:
    risk_case = create_case(client)
    case_id = risk_case["id"]

    response = client.post(
        f"/api/v1/cases/{case_id}/decision",
        json={
            "action": "hold",
            "expected_version": risk_case["version"],
            "note": "High withdrawal with incomplete KYC. Holding for review.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == case_id
    assert body["action"] == "hold"
    assert body["previous_status"] == "open"
    assert body["new_status"] == "on_hold"
    assert body["actor"] == "portfolio_operator"
    assert body["version"] == 2
    assert body["note"] == "High withdrawal with incomplete KYC. Holding for review."

    case_response = client.get(f"/api/v1/cases/{case_id}")
    assert case_response.status_code == 200
    assert case_response.json()["status"] == "on_hold"


def test_escalate_decision_updates_case_status_to_escalated(client: TestClient) -> None:
    risk_case = create_case(client)
    case_id = risk_case["id"]

    response = client.post(
        f"/api/v1/cases/{case_id}/decision",
        json={"action": "escalate", "expected_version": risk_case["version"]},
    )

    assert response.status_code == 200
    assert response.json()["new_status"] == "escalated"

    case_response = client.get(f"/api/v1/cases/{case_id}")
    assert case_response.status_code == 200
    assert case_response.json()["status"] == "escalated"


def test_unsupported_decision_action_returns_422(client: TestClient) -> None:
    risk_case = create_case(client)

    response = client.post(
        f"/api/v1/cases/{risk_case['id']}/decision",
        json={"action": "defer", "expected_version": risk_case["version"]},
    )

    assert response.status_code == 422


def test_client_cannot_supply_audit_actor(client: TestClient) -> None:
    risk_case = create_case(client)

    response = client.post(
        f"/api/v1/cases/{risk_case['id']}/decision",
        json={
            "action": "hold",
            "expected_version": risk_case["version"],
            "analyst": "forged_identity",
        },
    )

    assert response.status_code == 422


def test_missing_case_decision_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/cases/999/decision",
        json={"action": "hold", "expected_version": 1},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Risk case not found"}


def test_decision_creates_audit_log(client: TestClient) -> None:
    risk_case = create_case(client)
    case_id = risk_case["id"]

    decision_response = client.post(
        f"/api/v1/cases/{case_id}/decision",
        json={
            "action": "request_kyc",
            "expected_version": risk_case["version"],
            "note": "Need documents.",
        },
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
        "actor": "portfolio_operator",
        "version": 2,
        "note": "Need documents.",
    }


def test_repeated_action_is_rejected_as_invalid_transition(client: TestClient) -> None:
    risk_case = create_case(client)
    first_response = client.post(
        f"/api/v1/cases/{risk_case['id']}/decision",
        json={"action": "hold", "expected_version": risk_case["version"]},
    )
    assert first_response.status_code == 200

    repeated_response = client.post(
        f"/api/v1/cases/{risk_case['id']}/decision",
        json={"action": "hold", "expected_version": first_response.json()["version"]},
    )

    assert repeated_response.status_code == 409
    assert repeated_response.json()["detail"] == (
        "Action 'hold' is not allowed while case is 'on_hold'"
    )


def test_stale_decision_is_rejected(client: TestClient) -> None:
    risk_case = create_case(client)
    first_response = client.post(
        f"/api/v1/cases/{risk_case['id']}/decision",
        json={"action": "hold", "expected_version": risk_case["version"]},
    )
    assert first_response.status_code == 200

    stale_response = client.post(
        f"/api/v1/cases/{risk_case['id']}/decision",
        json={"action": "escalate", "expected_version": risk_case["version"]},
    )

    assert stale_response.status_code == 409
    assert stale_response.json()["detail"] == (
        "Case changed since it was loaded; refresh and try again"
    )


def test_terminal_case_rejects_further_decisions(client: TestClient) -> None:
    risk_case = create_case(client)
    resolved_response = client.post(
        f"/api/v1/cases/{risk_case['id']}/decision",
        json={"action": "approve", "expected_version": risk_case["version"]},
    )
    assert resolved_response.status_code == 200

    response = client.post(
        f"/api/v1/cases/{risk_case['id']}/decision",
        json={"action": "escalate", "expected_version": resolved_response.json()["version"]},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Action 'escalate' is not allowed while case is 'resolved'"
