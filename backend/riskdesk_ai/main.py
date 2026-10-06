import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from riskdesk_ai.api.routes import router
from riskdesk_ai.schemas import HealthRead, RootRead

LOCAL_DEVELOPMENT_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def allowed_origins() -> list[str]:
    configured_origins = os.getenv("RISKDESK_ALLOWED_ORIGINS")
    if configured_origins is None:
        if os.getenv("VERCEL_ENV") in {"preview", "production"}:
            raise RuntimeError("RISKDESK_ALLOWED_ORIGINS is required on Vercel")
        return list(LOCAL_DEVELOPMENT_ORIGINS)

    origins = [origin.strip().rstrip("/") for origin in configured_origins.split(",")]
    origins = [origin for origin in origins if origin]
    if not origins and os.getenv("VERCEL_ENV") in {"preview", "production"}:
        raise RuntimeError("RISKDESK_ALLOWED_ORIGINS is required on Vercel")
    if "*" in origins:
        raise RuntimeError("RISKDESK_ALLOWED_ORIGINS must contain explicit origins, not '*'")
    return origins


def create_app() -> FastAPI:
    fastapi_app = FastAPI(
        title="RiskDesk AI",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @fastapi_app.get("/api", response_model=RootRead)
    def root() -> dict[str, str]:
        return {"service": "riskdesk-ai", "status": "ok", "docs": "/api/docs"}

    @fastapi_app.get("/api/healthz", response_model=HealthRead)
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "riskdesk-ai"}

    fastapi_app.include_router(router)
    return fastapi_app


app = create_app()
