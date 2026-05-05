from riskdesk_ai.schemas import EventCreate, RiskEvaluation

HIGH_RISK_COUNTRIES = {"RU", "IR", "KP", "SY"}
PAYMENT_OR_WITHDRAWAL_EVENTS = {"payment", "payment_received", "deposit", "withdrawal_requested"}


def evaluate_event_risk(event: EventCreate) -> RiskEvaluation:
    score = 0
    triggered_rules: list[str] = []
    event_type = event.event_type
    country = event.country.upper()

    if event_type == "withdrawal_requested" and event.amount >= 2000:
        score += 30
        triggered_rules.append("HIGH_VALUE_WITHDRAWAL")

    if event_type == "withdrawal_requested" and event.kyc_status != "verified":
        score += 25
        triggered_rules.append("KYC_INCOMPLETE")

    if event.payment_method and event_type in PAYMENT_OR_WITHDRAWAL_EVENTS:
        score += 5
        triggered_rules.append("PAYMENT_METHOD_PRESENT")

    if country in HIGH_RISK_COUNTRIES:
        score += 30
        triggered_rules.append("HIGH_RISK_COUNTRY")

    if event_type == "bonus_claimed":
        score += 15
        triggered_rules.append("BONUS_CLAIM_EVENT")

    score = min(score, 100)
    risk_level = _risk_level(score)
    return RiskEvaluation(
        risk_score=score,
        risk_level=risk_level,
        recommended_action=_recommended_action(risk_level),
        triggered_rules=triggered_rules,
    )


def _risk_level(score: int) -> str:
    if score >= 70:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


def _recommended_action(risk_level: str) -> str:
    actions = {
        "LOW": "approve",
        "MEDIUM": "manual_review",
        "HIGH": "hold_and_escalate",
    }
    return actions[risk_level]
