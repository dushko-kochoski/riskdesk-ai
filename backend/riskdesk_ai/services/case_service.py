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
ACTIVE_CASE_STATUSES = {"open", "on_hold", "escalated", "pending_kyc"}
ALL_DECISION_ACTIONS = set(DECISION_STATUS_MAPPING)
ALLOWED_ACTIONS_BY_STATUS = {
    "open": ALL_DECISION_ACTIONS,
    "on_hold": ALL_DECISION_ACTIONS - {"hold"},
    "escalated": ALL_DECISION_ACTIONS - {"escalate"},
    "pending_kyc": ALL_DECISION_ACTIONS - {"request_kyc"},
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
        *,
        actor: str,
    ) -> schemas.CaseDecisionResponse:
        risk_case = self.get_case(case_id)
        action = request.action.value
        if risk_case.version != request.expected_version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Case changed since it was loaded; refresh and try again",
            )

        previous_status = risk_case.status
        allowed_actions = ALLOWED_ACTIONS_BY_STATUS.get(previous_status, set())
        if previous_status not in ACTIVE_CASE_STATUSES or action not in allowed_actions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Action '{action}' is not allowed while case is '{previous_status}'",
            )

        new_status = DECISION_STATUS_MAPPING[action]
        updated_case = self.repository.update_status_if_version_matches(
            case_id=case_id,
            expected_version=request.expected_version,
            status=new_status,
        )
        if updated_case is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Case changed since it was loaded; refresh and try again",
            )

        audit_log = self.audit_service.record(
            action="case_decision_recorded",
            entity_type="case",
            entity_id=case_id,
            details=json.dumps(
                {
                    "case_id": case_id,
                    "action": action,
                    "previous_status": previous_status,
                    "new_status": new_status,
                    "actor": actor,
                    "version": updated_case.version,
                    "note": request.note,
                },
                sort_keys=True,
            ),
        )
        self.db.commit()

        return schemas.CaseDecisionResponse(
            case_id=case_id,
            action=action,
            previous_status=previous_status,
            new_status=new_status,
            actor=actor,
            version=updated_case.version,
            note=request.note,
            audit_log_id=audit_log.id,
        )
