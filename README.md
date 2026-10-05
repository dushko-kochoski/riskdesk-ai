# RiskDesk AI

A local risk-event intake and analyst case-review service with a FastAPI backend and a Vite React dashboard.

## Current Portfolio Upgrade

The first audited upgrade adds server-backed case queue filters for player ID, risk level, and status. It includes responsive controls, explicit apply/clear behavior, and a useful empty state. See [Portfolio upgrade audit](docs/PORTFOLIO_UPGRADE.md) for verified results, screenshots, deployment suitability, and remaining limitations.

## Portfolio Screenshots

All names, identifiers, events, amounts, and decisions shown below are synthetic demo data.

![RiskDesk AI dashboard showing synthetic demo metrics, risk distribution, and recent activity](docs/screenshots/riskdesk-demo-dashboard.png)

*Demo data — dashboard overview with queue health and recent activity.*

![RiskDesk AI case queue filtered to one synthetic high-risk case](docs/screenshots/riskdesk-demo-high-risk-queue.png)

*Demo data — server-backed high-risk queue filter.*

![RiskDesk AI case-review drawer showing a synthetic high-risk case after a hold decision](docs/screenshots/riskdesk-demo-case-review-decision.png)

*Demo data — case review, triggered rules, and recorded decision state.*

## Backend

The backend is a FastAPI application backed by local SQLite storage. Routes are intentionally thin, business logic lives in services, and database access is isolated in repositories.

## Local Setup

Run these backend commands from the project root:

```powershell
cd "C:\RiskDesk AI\backend"
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m uvicorn riskdesk_ai.main:app --reload
```

## Frontend

The frontend is a Vite React TypeScript app in `frontend/`. It expects the backend at `http://127.0.0.1:8000` by default.

```powershell
cd "C:\RiskDesk AI\frontend"
npm install
npm run dev
```

Open the local Vite URL shown in the terminal. To point the frontend at a different backend URL, set `VITE_API_BASE_URL`.

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```

## Simulator

Run a synthetic casino-event scenario through the same ingestion path as the API:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/simulator/run" `
  -ContentType "application/json" `
  -Body '{"scenario":"high_value_withdrawal_incomplete_kyc","player_id":"plr_demo_001"}'
```

Example response:

```json
{
  "scenario": "high_value_withdrawal_incomplete_kyc",
  "player_id": "plr_demo_001",
  "events_created": 3,
  "cases_created": 1,
  "event_ids": [1, 2, 3],
  "case_ids": [1]
}
```

Supported scenarios:

```text
normal_player
high_value_withdrawal_incomplete_kyc
bonus_abuse_attempt
high_risk_country_withdrawal
```

## Case Decisions

Record an analyst decision on an existing risk case:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/cases/1/decision" `
  -ContentType "application/json" `
  -Body '{"action":"hold","analyst":"demo_analyst","note":"High withdrawal with incomplete KYC. Holding for review."}'
```

Example response:

```json
{
  "case_id": 1,
  "action": "hold",
  "previous_status": "open",
  "new_status": "on_hold",
  "analyst": "demo_analyst",
  "note": "High withdrawal with incomplete KYC. Holding for review.",
  "audit_log_id": 10
}
```

## Case Queue Filters

Filter the analyst case queue with optional query parameters:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/cases?status=open"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/cases?risk_level=HIGH"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/cases?player_id=plr_demo_001"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/cases?status=on_hold&risk_level=MEDIUM"
```

## Dashboard Summary

Fetch aggregate metrics for the analyst dashboard:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/dashboard/summary"
```

Example response:

```json
{
  "total_events": 3,
  "total_cases": 1,
  "open_cases": 1,
  "high_risk_cases": 0,
  "on_hold_cases": 0,
  "escalated_cases": 0,
  "cases_by_risk_level": {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 0
  },
  "cases_by_status": {
    "open": 1,
    "on_hold": 0,
    "escalated": 0,
    "pending_kyc": 0,
    "rejected": 0,
    "false_positive": 0,
    "closed": 0,
    "resolved": 0
  }
}
```

## Demo Controls

Reset local demo data:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/demo/reset"
```

Generate a clean demo dataset:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/demo/seed"
```
