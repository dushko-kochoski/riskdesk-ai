from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from riskdesk_ai import schemas
from riskdesk_ai.database import get_db
from riskdesk_ai.services.audit_service import AuditService
from riskdesk_ai.services.case_service import CaseService
from riskdesk_ai.services.dashboard_service import DashboardService
from riskdesk_ai.services.demo_service import DemoService
from riskdesk_ai.services.event_service import EventService
from riskdesk_ai.services.simulator_service import SimulatorService

router = APIRouter(prefix="/api/v1")
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/events", response_model=schemas.EventIngestResponse, status_code=201)
def create_event(event: schemas.EventCreate, db: DbSession) -> schemas.EventIngestResponse:
    return EventService(db).ingest_event(event)


@router.get("/events", response_model=list[schemas.EventRead])
def list_events(db: DbSession) -> list[schemas.EventRead]:
    return EventService(db).list_events()


@router.get("/dashboard/summary", response_model=schemas.DashboardSummaryResponse)
def dashboard_summary(db: DbSession) -> schemas.DashboardSummaryResponse:
    return DashboardService(db).summary()


@router.post("/demo/reset", response_model=schemas.DemoResetResponse)
def reset_demo(db: DbSession) -> schemas.DemoResetResponse:
    return DemoService(db).reset()


@router.post("/demo/seed", response_model=schemas.DemoSeedResponse)
def seed_demo(db: DbSession) -> schemas.DemoSeedResponse:
    return DemoService(db).seed()


@router.get("/cases", response_model=list[schemas.RiskCaseRead])
def list_cases(
    db: DbSession,
    status: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    player_id: str | None = Query(default=None),
    recommended_action: str | None = Query(default=None),
) -> list[schemas.RiskCaseRead]:
    filters = schemas.CaseFilters(
        status=status,
        risk_level=risk_level,
        player_id=player_id,
        recommended_action=recommended_action,
    )
    return CaseService(db).list_cases(filters)


@router.get("/cases/{case_id}", response_model=schemas.RiskCaseRead)
def get_case(case_id: int, db: DbSession) -> schemas.RiskCaseRead:
    return CaseService(db).get_case(case_id)


@router.post("/cases/{case_id}/decision", response_model=schemas.CaseDecisionResponse)
def decide_case(
    case_id: int,
    request: schemas.CaseDecisionRequest,
    db: DbSession,
) -> schemas.CaseDecisionResponse:
    return CaseService(db).record_decision(case_id, request)


@router.get("/audit-logs", response_model=list[schemas.AuditLogRead])
def list_audit_logs(db: DbSession) -> list[schemas.AuditLogRead]:
    return AuditService(db).list_logs()


@router.post("/simulator/run", response_model=schemas.SimulatorRunResponse)
def run_simulator(
    request: schemas.SimulatorRunRequest,
    db: DbSession,
) -> schemas.SimulatorRunResponse:
    return SimulatorService(db).run(request)
