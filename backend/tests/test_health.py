from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine, inspect

import riskdesk_ai.database as database_module
import riskdesk_ai.main as main_module
from riskdesk_ai.database import Base
from riskdesk_ai.main import app


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


def test_lifespan_initializes_database(monkeypatch) -> None:
    calls = []

    def fake_init_db() -> None:
        calls.append("init_db")

    monkeypatch.setattr(main_module, "init_db", fake_init_db)
    test_app = main_module.create_app()

    with TestClient(test_app):
        pass

    assert calls == ["init_db"]


def test_lifespan_creates_database_tables(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    monkeypatch.setattr(database_module, "engine", engine)
    test_app = main_module.create_app()

    with TestClient(test_app):
        pass

    assert set(Base.metadata.tables).issubset(inspect(engine).get_table_names())
