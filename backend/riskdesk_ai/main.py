from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from riskdesk_ai.api.routes import router
from riskdesk_ai.schemas import HealthRead, RootRead


def create_app() -> FastAPI:
    fastapi_app = FastAPI(title="RiskDesk AI", version="0.1.0")
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @fastapi_app.get("/", response_model=RootRead)
    def root() -> dict[str, str]:
        return {"service": "riskdesk-ai", "status": "ok", "docs": "/docs"}

    @fastapi_app.get("/healthz", response_model=HealthRead)
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "riskdesk-ai"}

    fastapi_app.include_router(router)
    return fastapi_app


app = create_app()
