from sqlalchemy.orm import Session

from riskdesk_ai import models
from riskdesk_ai.repositories import AuditLogRepository


class AuditService:
    def __init__(self, db: Session) -> None:
        self.repository = AuditLogRepository(db)

    def record(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: int | None,
        details: str = "",
    ) -> models.AuditLog:
        return self.repository.create(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )

    def list_logs(self) -> list[models.AuditLog]:
        return self.repository.list()
