from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from riskdesk_ai import models, schemas


class EventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, event_data: schemas.EventCreate) -> models.Event:
        event = models.Event(**event_data.model_dump())
        self.db.add(event)
        self.db.flush()
        self.db.refresh(event)
        return event

    def list(self) -> list[models.Event]:
        statement = select(models.Event).order_by(
            models.Event.created_at.desc(),
            models.Event.id.desc(),
        )
        return list(self.db.scalars(statement).all())

    def count(self) -> int:
        statement = select(func.count()).select_from(models.Event)
        return self.db.scalar(statement) or 0

    def delete_all(self) -> int:
        count = self.count()
        self.db.execute(delete(models.Event))
        return count


class CaseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        event_id: int,
        player_id: str,
        risk_score: int,
        risk_level: str,
        recommended_action: str,
        triggered_rules: list[str],
    ) -> models.RiskCase:
        risk_case = models.RiskCase(
            event_id=event_id,
            player_id=player_id,
            risk_score=risk_score,
            risk_level=risk_level,
            recommended_action=recommended_action,
            triggered_rules=triggered_rules,
        )
        self.db.add(risk_case)
        self.db.flush()
        self.db.refresh(risk_case)
        return risk_case

    def list(self, filters: schemas.CaseFilters | None = None) -> list[models.RiskCase]:
        statement = select(models.RiskCase)
        if filters is not None:
            if filters.status:
                statement = statement.where(models.RiskCase.status == filters.status)
            if filters.risk_level:
                statement = statement.where(models.RiskCase.risk_level == filters.risk_level)
            if filters.player_id:
                statement = statement.where(models.RiskCase.player_id == filters.player_id)
            if filters.recommended_action:
                statement = statement.where(
                    models.RiskCase.recommended_action == filters.recommended_action,
                )

        statement = statement.order_by(
            models.RiskCase.created_at.desc(),
            models.RiskCase.id.desc(),
        )
        return list(self.db.scalars(statement).all())

    def get(self, case_id: int) -> models.RiskCase | None:
        return self.db.get(models.RiskCase, case_id)

    def update_status(self, risk_case: models.RiskCase, status: str) -> models.RiskCase:
        risk_case.status = status
        self.db.flush()
        self.db.refresh(risk_case)
        return risk_case

    def count(self) -> int:
        statement = select(func.count()).select_from(models.RiskCase)
        return self.db.scalar(statement) or 0

    def count_by_risk_level(self) -> dict[str, int]:
        statement = select(models.RiskCase.risk_level, func.count()).group_by(
            models.RiskCase.risk_level,
        )
        return {risk_level: count for risk_level, count in self.db.execute(statement).all()}

    def count_by_status(self) -> dict[str, int]:
        statement = select(models.RiskCase.status, func.count()).group_by(models.RiskCase.status)
        return {case_status: count for case_status, count in self.db.execute(statement).all()}

    def prevented_exposure_estimate(self, statuses: tuple[str, ...]) -> float:
        statement = (
            select(func.coalesce(func.sum(models.Event.amount), 0))
            .select_from(models.RiskCase)
            .join(models.Event, models.RiskCase.event_id == models.Event.id)
            .where(models.RiskCase.status.in_(statuses))
        )
        return float(self.db.scalar(statement) or 0)

    def triggered_rule_count(self) -> int:
        return sum(len(risk_case.triggered_rules) for risk_case in self.list())

    def delete_all(self) -> int:
        count = self.count()
        self.db.execute(delete(models.RiskCase))
        return count


class AuditLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: int | None,
        details: str = "",
    ) -> models.AuditLog:
        audit_log = models.AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
        self.db.add(audit_log)
        self.db.flush()
        self.db.refresh(audit_log)
        return audit_log

    def list(self) -> list[models.AuditLog]:
        statement = select(models.AuditLog).order_by(
            models.AuditLog.created_at.desc(),
            models.AuditLog.id.desc(),
        )
        return list(self.db.scalars(statement).all())

    def recent(self, limit: int) -> list[models.AuditLog]:
        statement = (
            select(models.AuditLog)
            .order_by(models.AuditLog.created_at.desc(), models.AuditLog.id.desc())
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def count(self) -> int:
        statement = select(func.count()).select_from(models.AuditLog)
        return self.db.scalar(statement) or 0

    def delete_all(self) -> int:
        count = self.count()
        self.db.execute(delete(models.AuditLog))
        return count
