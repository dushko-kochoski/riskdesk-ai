from collections.abc import Generator
from datetime import UTC, datetime

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


def event_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "event_type": "login",
        "player_id": "player-123",
        "amount": 0,
        "currency": "EUR",
        "country": "PL",
        "ip_address": "203.0.113.10",
        "device_id": "device-abc",
        "payment_method": None,
        "kyc_status": "verified",
        "timestamp": datetime(2026, 5, 5, 10, 0, tzinfo=UTC).isoformat(),
    }
    payload.update(overrides)
    return payload


def test_low_risk_event_does_not_create_case(client: TestClient) -> None:
    response = client.post("/api/v1/events", json=event_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["risk"]["risk_level"] == "LOW"
    assert body["case"] is None

    cases_response = client.get("/api/v1/cases")
    assert cases_response.status_code == 200
    assert cases_response.json() == []


def test_high_withdrawal_with_incomplete_kyc_creates_case(client: TestClient) -> None:
    response = client.post(
        "/api/v1/events",
        json=event_payload(
            event_type="withdrawal_requested",
            amount=3000,
            payment_method="card",
            kyc_status="pending",
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["risk"]["risk_score"] == 60
    assert body["risk"]["risk_level"] == "MEDIUM"
    assert body["risk"]["recommended_action"] == "manual_review"
    assert body["case"] is not None
    assert body["case"]["status"] == "open"
    assert set(body["risk"]["triggered_rules"]) == {
        "HIGH_VALUE_WITHDRAWAL",
        "KYC_INCOMPLETE",
        "PAYMENT_METHOD_PRESENT",
    }


def test_high_risk_country_creates_case(client: TestClient) -> None:
    response = client.post("/api/v1/events", json=event_payload(country="IR"))

    assert response.status_code == 201
    body = response.json()
    assert body["risk"]["risk_score"] == 30
    assert body["risk"]["risk_level"] == "MEDIUM"
    assert body["case"] is not None
    assert body["risk"]["triggered_rules"] == ["HIGH_RISK_COUNTRY"]


def test_audit_logs_are_created(client: TestClient) -> None:
    response = client.post(
        "/api/v1/events",
        json=event_payload(
            event_type="withdrawal_requested",
            amount=5000,
            country="RU",
            payment_method="bank_transfer",
            kyc_status="unverified",
        ),
    )
    assert response.status_code == 201

    audit_response = client.get("/api/v1/audit-logs")

    assert audit_response.status_code == 200
    actions = {log["action"] for log in audit_response.json()}
    assert {"event_received", "risk_evaluated", "case_created"}.issubset(actions)
