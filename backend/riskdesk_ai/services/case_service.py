import json

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from riskdesk_ai import models, schemas
from riskdesk_ai.repositories import CaseRepository
from riskdesk_ai.services.audit_service import AuditService

CASE_CREATING_LEVELS = {"MEDIUM", "HIGH"}
DECISION_STATUS_MAPPING = {
    "approve": "resolved",
    "hold": "on_hold",
    "escalate": "escalated",
    "request_kyc": "pending_kyc",
    "reject": "rejected",
    "mark_false_positive": "false_positive",
    "close": "closed",
}


class CaseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = CaseRepository(db)
        self.audit_service = AuditService(db)

    def create_if_needed(
        self,
        *,
        event: models.Event,
        risk: schemas.RiskEvaluation,
    ) -> models.RiskCase | None:
        if risk.risk_level not in CASE_CREATING_LEVELS:
            return None

        return self.repository.create(
            event_id=event.id,
            player_id=event.player_id,
            risk_score=risk.risk_score,
            risk_level=risk.risk_level,
            recommended_action=risk.recommended_action,
            triggered_rules=risk.triggered_rules,
        )

    def list_cases(self, filters: schemas.CaseFilters | None = None) -> list[models.RiskCase]:
        return self.repository.list(filters)

    def get_case(self, case_id: int) -> models.RiskCase:
        risk_case = self.repository.get(case_id)
        if risk_case is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Risk case not found",
            )
        return risk_case

    def record_decision(
        self,
        case_id: int,
        request: schemas.CaseDecisionRequest,
    ) -> schemas.CaseDecisionResponse:
        risk_case = self.get_case(case_id)
        new_status = DECISION_STATUS_MAPPING.get(request.action)
        if new_status is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported case decision action: {request.action}",
            )

        previous_status = risk_case.status
        self.repository.update_status(risk_case, new_status)
        audit_log = self.audit_service.record(
            action="case_decision_recorded",
            entity_type="case",
            entity_id=case_id,
            details=json.dumps(
                {
                    "case_id": case_id,
                    "action": request.action,
                    "previous_status": previous_status,
                    "new_status": new_status,
                    "analyst": request.analyst,
                    "note": request.note,
                },
                sort_keys=True,
            ),
        )
        self.db.commit()

        return schemas.CaseDecisionResponse(
            case_id=case_id,
            action=request.action,
            previous_status=previous_status,
            new_status=new_status,
            analyst=request.analyst,
            note=request.note,
            audit_log_id=audit_log.id,
        )
