from sqlalchemy.orm import Session

from riskdesk_ai import schemas
from riskdesk_ai.repositories import AuditLogRepository, CaseRepository, EventRepository
from riskdesk_ai.services.simulator_service import SimulatorService

DEMO_SCENARIOS = (
    ("normal_player", "plr_normal_demo"),
    ("high_value_withdrawal_incomplete_kyc", "plr_withdrawal_demo"),
    ("bonus_abuse_attempt", "plr_bonus_demo"),
    ("high_risk_country_withdrawal", "plr_high_risk_demo"),
)


class DemoService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit_log_repository = AuditLogRepository(db)
        self.case_repository = CaseRepository(db)
        self.event_repository = EventRepository(db)
        self.simulator_service = SimulatorService(db)

    def reset(self) -> schemas.DemoResetResponse:
        deleted_audit_logs = self.audit_log_repository.delete_all()
        deleted_triggered_rules = self.case_repository.triggered_rule_count()
        deleted_cases = self.case_repository.delete_all()
        deleted_events = self.event_repository.delete_all()
        self.db.commit()

        return schemas.DemoResetResponse(
            status="reset_complete",
            deleted=schemas.DemoResetDeleted(
                audit_logs=deleted_audit_logs,
                triggered_rules=deleted_triggered_rules,
                cases=deleted_cases,
                events=deleted_events,
            ),
        )

    def seed(self) -> schemas.DemoSeedResponse:
        self.reset()

        scenario_results = [
            self.simulator_service.run(
                schemas.SimulatorRunRequest(scenario=scenario, player_id=player_id),
            )
            for scenario, player_id in DEMO_SCENARIOS
        ]
        case_ids = [
            case_id
            for result in scenario_results
            for case_id in result.case_ids
        ]

        return schemas.DemoSeedResponse(
            status="seed_complete",
            scenarios_run=len(scenario_results),
            events_created=sum(result.events_created for result in scenario_results),
            cases_created=sum(result.cases_created for result in scenario_results),
            case_ids=case_ids,
        )
