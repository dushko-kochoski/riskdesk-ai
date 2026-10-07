import pytest

from riskdesk_ai.seed_preview import seed_preview


def test_preview_seed_requires_explicit_preview_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RISKDESK_PREVIEW_SEED_ENABLED", "true")
    monkeypatch.setenv("RISKDESK_DEPLOYMENT_ENV", "production")

    with pytest.raises(RuntimeError, match="DEPLOYMENT_ENV"):
        seed_preview("postgresql+psycopg://example.invalid/preview")


def test_preview_seed_requires_explicit_enable_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RISKDESK_DEPLOYMENT_ENV", "preview")
    monkeypatch.setenv("RISKDESK_PREVIEW_SEED_ENABLED", "false")

    with pytest.raises(RuntimeError, match="PREVIEW_SEED_ENABLED"):
        seed_preview("postgresql+psycopg://example.invalid/preview")


def test_preview_seed_refuses_non_postgresql_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RISKDESK_DEPLOYMENT_ENV", "preview")
    monkeypatch.setenv("RISKDESK_PREVIEW_SEED_ENABLED", "true")

    with pytest.raises(RuntimeError, match="PostgreSQL"):
        seed_preview("sqlite:///preview.db")
