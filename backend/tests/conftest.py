import base64

import pytest

TEST_OPERATOR_USERNAME = "portfolio_operator"
TEST_OPERATOR_PASSWORD = "test-password-only"


@pytest.fixture(autouse=True)
def configure_test_access(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RISKDESK_OPERATOR_USERNAME", TEST_OPERATOR_USERNAME)
    monkeypatch.setenv("RISKDESK_OPERATOR_PASSWORD", TEST_OPERATOR_PASSWORD)
    monkeypatch.setenv("RISKDESK_DEMO_MODE", "true")


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    encoded = base64.b64encode(
        f"{TEST_OPERATOR_USERNAME}:{TEST_OPERATOR_PASSWORD}".encode(),
    ).decode()
    return {"Authorization": f"Basic {encoded}"}
