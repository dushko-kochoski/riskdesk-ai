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


def seed_case_queue(client: TestClient) -> dict[str, int]:
    medium_response = client.post(
        "/api/v1/simulator/run",
        json={
            "scenario": "high_value_withdrawal_incomplete_kyc",
            "player_id": "plr_filter_medium",
        },
    )
    assert medium_response.status_code == 200
    medium_case_id = medium_response.json()["case_ids"][0]

    high_response = client.post(
        "/api/v1/simulator/run",
        json={
            "scenario": "high_risk_country_withdrawal",
            "player_id": "plr_filter_high",
        },
    )
    assert high_response.status_code == 200
    high_case_ids = high_response.json()["case_ids"]

    hold_response = client.post(
        f"/api/v1/cases/{medium_case_id}/decision",
        json={"action": "hold", "expected_version": 1},
    )
    assert hold_response.status_code == 200

    return {"medium": medium_case_id, "high": high_case_ids[-1]}


def test_no_filters_returns_all_cases(client: TestClient) -> None:
    seed_case_queue(client)

    response = client.get("/api/v1/cases")

    assert response.status_code == 200
    assert len(response.json()) == 3


def test_filter_cases_by_status(client: TestClient) -> None:
    seed_case_queue(client)

    response = client.get("/api/v1/cases", params={"status": "on_hold"})

    assert response.status_code == 200
    cases = response.json()
    assert len(cases) == 1
    assert cases[0]["status"] == "on_hold"


def test_filter_cases_by_risk_level(client: TestClient) -> None:
    seed_case_queue(client)

    response = client.get("/api/v1/cases", params={"risk_level": "HIGH"})

    assert response.status_code == 200
    cases = response.json()
    assert len(cases) == 1
    assert cases[0]["risk_level"] == "HIGH"


def test_filter_cases_by_player_id(client: TestClient) -> None:
    seed_case_queue(client)

    response = client.get("/api/v1/cases", params={"player_id": "plr_filter_medium"})

    assert response.status_code == 200
    cases = response.json()
    assert len(cases) == 1
    assert cases[0]["player_id"] == "plr_filter_medium"


def test_combined_filter_by_status_and_risk_level(client: TestClient) -> None:
    seed_case_queue(client)

    response = client.get(
        "/api/v1/cases",
        params={"status": "on_hold", "risk_level": "MEDIUM"},
    )

    assert response.status_code == 200
    cases = response.json()
    assert len(cases) == 1
    assert cases[0]["status"] == "on_hold"
    assert cases[0]["risk_level"] == "MEDIUM"


def test_combined_filters_only_return_the_exact_matching_player(client: TestClient) -> None:
    case_ids = seed_case_queue(client)

    response = client.get(
        "/api/v1/cases",
        params={
            "status": "on_hold",
            "risk_level": "MEDIUM",
            "player_id": "plr_filter_medium",
        },
    )

    assert response.status_code == 200
    assert [risk_case["id"] for risk_case in response.json()] == [case_ids["medium"]]


def test_filters_return_empty_list_when_no_cases_match(client: TestClient) -> None:
    seed_case_queue(client)

    response = client.get(
        "/api/v1/cases",
        params={
            "status": "open",
            "risk_level": "HIGH",
            "player_id": "plr_no_match",
        },
    )

    assert response.status_code == 200
    assert response.json() == []
