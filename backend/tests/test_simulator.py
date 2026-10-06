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


def test_simulator_normal_player_creates_events_without_cases(client: TestClient) -> None:
    response = client.post(
        "/api/v1/simulator/run",
        json={"scenario": "normal_player", "player_id": "plr_demo_normal"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scenario"] == "normal_player"
    assert body["player_id"] == "plr_demo_normal"
    assert body["events_created"] == 5
    assert body["cases_created"] == 0
    assert len(body["event_ids"]) == 5
    assert body["case_ids"] == []


def test_simulator_high_value_withdrawal_incomplete_kyc_creates_case(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/simulator/run",
        json={
            "scenario": "high_value_withdrawal_incomplete_kyc",
            "player_id": "plr_demo_001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["events_created"] == 3
    assert body["cases_created"] == 1
    assert len(body["case_ids"]) == 1


def test_simulator_high_risk_country_withdrawal_creates_high_risk_case(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/simulator/run",
        json={
            "scenario": "high_risk_country_withdrawal",
            "player_id": "plr_demo_high_country",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["events_created"] == 2
    assert body["cases_created"] >= 1

    cases = [client.get(f"/api/v1/cases/{case_id}").json() for case_id in body["case_ids"]]
    assert any(case["risk_level"] == "HIGH" for case in cases)


def test_simulator_unsupported_scenario_returns_400(client: TestClient) -> None:
    response = client.post(
        "/api/v1/simulator/run",
        json={"scenario": "not_a_scenario"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported simulator scenario: not_a_scenario"}
