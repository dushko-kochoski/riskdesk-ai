import pytest

from riskdesk_ai.main import LOCAL_DEVELOPMENT_ORIGINS, allowed_origins


def test_cors_defaults_to_explicit_local_origins() -> None:
    assert allowed_origins() == list(LOCAL_DEVELOPMENT_ORIGINS)


def test_cors_accepts_explicit_configured_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "RISKDESK_ALLOWED_ORIGINS",
        "https://preview.example.com/, https://riskdesk.example.com",
    )

    assert allowed_origins() == [
        "https://preview.example.com",
        "https://riskdesk.example.com",
    ]


def test_cors_rejects_wildcard_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RISKDESK_ALLOWED_ORIGINS", "*")

    with pytest.raises(RuntimeError, match="explicit origins"):
        allowed_origins()


@pytest.mark.parametrize("configured_origins", [None, ""])
def test_cors_requires_explicit_vercel_origin(
    monkeypatch: pytest.MonkeyPatch,
    configured_origins: str | None,
) -> None:
    monkeypatch.setenv("VERCEL_ENV", "preview")
    if configured_origins is None:
        monkeypatch.delenv("RISKDESK_ALLOWED_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("RISKDESK_ALLOWED_ORIGINS", configured_origins)

    with pytest.raises(RuntimeError, match="required on Vercel"):
        allowed_origins()
