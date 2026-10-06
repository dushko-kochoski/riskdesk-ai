from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RootRead(BaseModel):
    service: str
    status: str
    docs: str


class HealthRead(BaseModel):
    status: str
    service: str


class AuthenticatedOperatorRead(BaseModel):
    actor: str
    demo_mode: bool


class EventCreate(BaseModel):
    event_type: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    amount: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=10)
    country: str = Field(min_length=2, max_length=2)
    ip_address: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    payment_method: str | None = None
    kyc_status: str = Field(min_length=1)
    timestamp: datetime


class EventRead(EventCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class RiskEvaluation(BaseModel):
    risk_score: int
    risk_level: str
    recommended_action: str
    triggered_rules: list[str]


class RiskCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    player_id: str
    risk_score: int
    risk_level: str
    recommended_action: str
    triggered_rules: list[str]
    status: str
    version: int
    created_at: datetime


class CaseFilters(BaseModel):
    status: str | None = None
    risk_level: str | None = None
    player_id: str | None = None
    recommended_action: str | None = None


class CaseDecisionAction(StrEnum):
    APPROVE = "approve"
    HOLD = "hold"
    ESCALATE = "escalate"
    REQUEST_KYC = "request_kyc"
    REJECT = "reject"
    MARK_FALSE_POSITIVE = "mark_false_positive"
    CLOSE = "close"


class CaseDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: CaseDecisionAction
    expected_version: int = Field(ge=1)
    note: str | None = None


class CaseDecisionResponse(BaseModel):
    case_id: int
    action: str
    previous_status: str
    new_status: str
    actor: str
    version: int
    note: str | None
    audit_log_id: int


class DashboardAuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    entity_type: str
    entity_id: int | None
    details: str
    created_at: datetime


class DashboardSummaryResponse(BaseModel):
    total_events: int
    total_cases: int
    open_cases: int
    high_risk_cases: int
    on_hold_cases: int
    escalated_cases: int
    cases_by_risk_level: dict[str, int]
    cases_by_status: dict[str, int]
    prevented_exposure_estimate: float
    recent_audit_logs: list[DashboardAuditLogRead]


class DemoResetDeleted(BaseModel):
    audit_logs: int
    triggered_rules: int
    cases: int
    events: int


class DemoResetResponse(BaseModel):
    status: str
    deleted: DemoResetDeleted


class DemoSeedResponse(BaseModel):
    status: str
    scenarios_run: int
    events_created: int
    cases_created: int
    case_ids: list[int]


class EventIngestResponse(BaseModel):
    event: EventRead
    risk: RiskEvaluation
    case: RiskCaseRead | None = None


class SimulatorRunRequest(BaseModel):
    scenario: str = Field(min_length=1)
    player_id: str | None = None


class SimulatorRunResponse(BaseModel):
    scenario: str
    player_id: str
    events_created: int
    cases_created: int
    event_ids: list[int]
    case_ids: list[int]


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    entity_type: str
    entity_id: int | None
    details: str
    created_at: datetime
