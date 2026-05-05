from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from riskdesk_ai import schemas
from riskdesk_ai.services.event_service import EventService

DEFAULT_PLAYER_ID = "plr_sim_0001"
SUPPORTED_SCENARIOS = {
    "normal_player",
    "high_value_withdrawal_incomplete_kyc",
    "bonus_abuse_attempt",
    "high_risk_country_withdrawal",
}


class SimulatorService:
    def __init__(self, db: Session) -> None:
        self.event_service = EventService(db)

    def run(self, request: schemas.SimulatorRunRequest) -> schemas.SimulatorRunResponse:
        if request.scenario not in SUPPORTED_SCENARIOS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported simulator scenario: {request.scenario}",
            )

        player_id = request.player_id or DEFAULT_PLAYER_ID
        events = self._build_events(request.scenario, player_id)
        responses = [self.event_service.ingest_event(event) for event in events]
        event_ids = [response.event.id for response in responses]
        case_ids = [
            response.case.id
            for response in responses
            if response.case is not None
        ]

        return schemas.SimulatorRunResponse(
            scenario=request.scenario,
            player_id=player_id,
            events_created=len(event_ids),
            cases_created=len(case_ids),
            event_ids=event_ids,
            case_ids=case_ids,
        )

    def _build_events(self, scenario: str, player_id: str) -> list[schemas.EventCreate]:
        builders = {
            "normal_player": self._normal_player,
            "high_value_withdrawal_incomplete_kyc": self._high_value_withdrawal_incomplete_kyc,
            "bonus_abuse_attempt": self._bonus_abuse_attempt,
            "high_risk_country_withdrawal": self._high_risk_country_withdrawal,
        }
        return builders[scenario](player_id)

    def _event(
        self,
        *,
        event_type: str,
        player_id: str,
        offset_minutes: int,
        amount: float = 0,
        currency: str = "EUR",
        country: str = "MT",
        ip_address: str = "203.0.113.10",
        device_id: str = "dev_sim_001",
        payment_method: str | None = None,
        kyc_status: str = "unverified",
    ) -> schemas.EventCreate:
        return schemas.EventCreate(
            event_type=event_type,
            player_id=player_id,
            amount=amount,
            currency=currency,
            country=country,
            ip_address=ip_address,
            device_id=device_id,
            payment_method=payment_method,
            kyc_status=kyc_status,
            timestamp=datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
            + timedelta(minutes=offset_minutes),
        )

    def _normal_player(self, player_id: str) -> list[schemas.EventCreate]:
        return [
            self._event(event_type="signup", player_id=player_id, offset_minutes=0),
            self._event(event_type="login", player_id=player_id, offset_minutes=5),
            self._event(
                event_type="deposit_completed",
                player_id=player_id,
                offset_minutes=10,
                amount=100,
                payment_method="card",
            ),
            self._event(
                event_type="kyc_updated",
                player_id=player_id,
                offset_minutes=20,
                kyc_status="verified",
            ),
            self._event(
                event_type="withdrawal_requested",
                player_id=player_id,
                offset_minutes=60,
                amount=80,
                payment_method="card",
                kyc_status="verified",
            ),
        ]

    def _high_value_withdrawal_incomplete_kyc(
        self,
        player_id: str,
    ) -> list[schemas.EventCreate]:
        return [
            self._event(event_type="signup", player_id=player_id, offset_minutes=0),
            self._event(
                event_type="deposit_completed",
                player_id=player_id,
                offset_minutes=10,
                amount=500,
                payment_method="bank_transfer",
            ),
            self._event(
                event_type="withdrawal_requested",
                player_id=player_id,
                offset_minutes=30,
                amount=2500,
                payment_method="bank_transfer",
                kyc_status="incomplete",
            ),
        ]

    def _bonus_abuse_attempt(self, player_id: str) -> list[schemas.EventCreate]:
        return [
            self._event(event_type="signup", player_id=player_id, offset_minutes=0),
            self._event(
                event_type="deposit_completed",
                player_id=player_id,
                offset_minutes=8,
                amount=25,
                payment_method="card",
            ),
            self._event(event_type="bonus_claimed", player_id=player_id, offset_minutes=10),
            self._event(
                event_type="withdrawal_requested",
                player_id=player_id,
                offset_minutes=15,
                amount=100,
                payment_method="card",
            ),
        ]

    def _high_risk_country_withdrawal(self, player_id: str) -> list[schemas.EventCreate]:
        return [
            self._event(
                event_type="signup",
                player_id=player_id,
                offset_minutes=0,
                country="RU",
                ip_address="198.51.100.20",
            ),
            self._event(
                event_type="withdrawal_requested",
                player_id=player_id,
                offset_minutes=20,
                amount=2200,
                country="RU",
                ip_address="198.51.100.20",
                payment_method="crypto_wallet",
                kyc_status="incomplete",
            ),
        ]
