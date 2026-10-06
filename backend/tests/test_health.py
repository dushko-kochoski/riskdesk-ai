from fastapi.testclient import TestClient

from riskdesk_ai.main import app, create_app


def test_root_endpoint_works() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"service": "riskdesk-ai", "status": "ok", "docs": "/docs"}


def test_health_endpoint_works() -> None:
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "riskdesk-ai"}


def test_application_startup_does_not_create_database_schema(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "startup-must-not-create.db"
    monkeypatch.setenv("RISKDESK_DATABASE_URL", f"sqlite:///{database_path}")

    with TestClient(create_app()):
        pass

    assert not database_path.exists()
