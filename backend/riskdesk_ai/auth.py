import os
import secrets
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

basic_auth = HTTPBasic(auto_error=False)


@dataclass(frozen=True)
class OperatorPrincipal:
    username: str


def demo_mode_enabled() -> bool:
    return os.getenv("RISKDESK_DEMO_MODE", "false").lower() == "true"


def require_operator(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(basic_auth)],
) -> OperatorPrincipal:
    configured_username = os.getenv("RISKDESK_OPERATOR_USERNAME")
    configured_password = os.getenv("RISKDESK_OPERATOR_PASSWORD")
    if not configured_username or not configured_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Operator authentication is not configured",
        )

    username_matches = credentials is not None and secrets.compare_digest(
        credentials.username.encode(),
        configured_username.encode(),
    )
    password_matches = credentials is not None and secrets.compare_digest(
        credentials.password.encode(),
        configured_password.encode(),
    )
    if not username_matches or not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid operator credentials",
            headers={"WWW-Authenticate": 'Basic realm="RiskDesk AI"'},
        )

    return OperatorPrincipal(username=configured_username)


def require_demo_mode() -> None:
    if not demo_mode_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


CurrentOperator = Annotated[OperatorPrincipal, Depends(require_operator)]
DemoMode = Annotated[None, Depends(require_demo_mode)]
