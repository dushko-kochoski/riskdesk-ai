from sqlalchemy.orm import Session

from riskdesk_ai import models, schemas
from riskdesk_ai.repositories import EventRepository
from riskdesk_ai.services.audit_service import AuditService
from riskdesk_ai.services.case_service import CaseService
from riskdesk_ai.services.risk_engine import evaluate_event_risk


class EventService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.event_repository = EventRepository(db)
        self.audit_service = AuditService(db)
        self.case_service = CaseService(db)

    def ingest_event(self, event_data: schemas.EventCreate) -> schemas.EventIngestResponse:
        event = self.event_repository.create(event_data)
        self.audit_service.record(
            action="event_received",
            entity_type="event",
            entity_id=event.id,
            details=f"Received event {event.event_type} for player {event.player_id}",
        )

        risk = evaluate_event_risk(event_data)
        self.audit_service.record(
            action="risk_evaluated",
            entity_type="event",
            entity_id=event.id,
            details=f"Risk level {risk.risk_level} with score {risk.risk_score}",
        )

        risk_case = self.case_service.create_if_needed(event=event, risk=risk)
        if risk_case is not None:
            self.audit_service.record(
                action="case_created",
                entity_type="case",
                entity_id=risk_case.id,
                details=f"Created case for event {event.id}",
            )

        self.db.commit()
        return schemas.EventIngestResponse(event=event, risk=risk, case=risk_case)

    def list_events(self) -> list[models.Event]:
        return self.event_repository.list()
