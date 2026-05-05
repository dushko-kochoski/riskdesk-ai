from sqlalchemy.orm import Session

from riskdesk_ai import schemas
from riskdesk_ai.repositories import AuditLogRepository, CaseRepository, EventRepository

RISK_LEVELS = ("LOW", "MEDIUM", "HIGH")
CASE_STATUSES = (
    "open",
    "on_hold",
    "escalated",
    "pending_kyc",
    "rejected",
    "false_positive",
    "closed",
    "resolved",
)
PREVENTED_EXPOSURE_STATUSES = ("on_hold", "escalated", "rejected")
RECENT_AUDIT_LOG_LIMIT = 5


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.event_repository = EventRepository(db)
        self.case_repository = CaseRepository(db)
        self.audit_log_repository = AuditLogRepository(db)

    def summary(self) -> schemas.DashboardSummaryResponse:
        cases_by_risk_level = self._with_defaults(
            defaults=RISK_LEVELS,
            values=self.case_repository.count_by_risk_level(),
        )
        cases_by_status = self._with_defaults(
            defaults=CASE_STATUSES,
            values=self.case_repository.count_by_status(),
        )

        return schemas.DashboardSummaryResponse(
            total_events=self.event_repository.count(),
            total_cases=self.case_repository.count(),
            open_cases=cases_by_status["open"],
            high_risk_cases=cases_by_risk_level["HIGH"],
            on_hold_cases=cases_by_status["on_hold"],
            escalated_cases=cases_by_status["escalated"],
            cases_by_risk_level=cases_by_risk_level,
            cases_by_status=cases_by_status,
            prevented_exposure_estimate=self.case_repository.prevented_exposure_estimate(
                PREVENTED_EXPOSURE_STATUSES,
            ),
            recent_audit_logs=self.audit_log_repository.recent(RECENT_AUDIT_LOG_LIMIT),
        )

    def _with_defaults(
        self,
        *,
        defaults: tuple[str, ...],
        values: dict[str, int],
    ) -> dict[str, int]:
        normalized = {key: 0 for key in defaults}
        normalized.update(values)
        return normalized
