import pytest
from fastapi.testclient import TestClient

from riskdesk_ai.main import app


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/v1/auth/me"),
        ("POST", "/api/v1/events"),
        ("GET", "/api/v1/events"),
        ("GET", "/api/v1/dashboard/summary"),
        ("GET", "/api/v1/cases"),
        ("GET", "/api/v1/cases/1"),
        ("POST", "/api/v1/cases/1/decision"),
        ("GET", "/api/v1/audit-logs"),
        ("POST", "/api/v1/demo/reset"),
        ("POST", "/api/v1/demo/seed"),
        ("POST", "/api/v1/simulator/run"),
    ],
)
def test_sensitive_routes_reject_unauthenticated_requests(method: str, path: str) -> None:
    with TestClient(app) as client:
        response = client.request(method, path)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid operator credentials"}


def test_valid_credentials_resolve_server_side_actor(auth_headers: dict[str, str]) -> None:
    with TestClient(app, headers=auth_headers) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json() == {"actor": "portfolio_operator", "demo_mode": True}


def test_authentication_fails_closed_when_server_credentials_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RISKDESK_OPERATOR_USERNAME")
    monkeypatch.delenv("RISKDESK_OPERATOR_PASSWORD")

    with TestClient(app) as client:
        response = client.get("/api/v1/cases")

    assert response.status_code == 503
    assert response.json() == {"detail": "Operator authentication is not configured"}


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/demo/reset",
        "/api/v1/demo/seed",
        "/api/v1/simulator/run",
    ],
)
def test_demo_mutations_are_not_available_outside_demo_mode(
    path: str,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RISKDESK_DEMO_MODE", "false")

    with TestClient(app, headers=auth_headers) as client:
        response = client.post(path, json={})

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}
