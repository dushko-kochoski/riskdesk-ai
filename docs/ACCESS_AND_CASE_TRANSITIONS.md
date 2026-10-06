# Access Protection and Case Transitions

Date: 2026-10-06

## Delivered scope

This upgrade protects the portfolio demo without provisioning an identity provider or any paid service:

- Every `/api/v1` route requires HTTP Basic credentials configured only in the backend environment.
- The authenticated server-side username becomes the audit actor. Decision requests reject extra fields, including a client-supplied `analyst` identity.
- Authentication fails closed with `503` when server credentials are absent and returns `401` for missing or invalid credentials.
- Reset, seed, and simulator endpoints additionally require the exact opt-in `RISKDESK_DEMO_MODE=true`; otherwise they return `404`.
- The frontend holds credentials only in memory, signs in through `/api/v1/auth/me`, attaches authorization to API calls, and clears data on sign-out or reload.
- Case rows carry an integer `version`. Decisions use a conditional update on both case ID and expected version, so competing writes cannot both succeed.
- The case update and audit insert share one database transaction. An audit failure rolls back the case change.

The public `/`, `/healthz`, and generated API documentation remain reachable for health checks and development discovery. Production documentation exposure should be decided when the deployment entrypoint is configured.

## Server configuration

| Variable | Required | Purpose |
|---|---:|---|
| `RISKDESK_OPERATOR_USERNAME` | yes | Single verified operator and audit actor |
| `RISKDESK_OPERATOR_PASSWORD` | yes | Operator secret; store outside Git |
| `RISKDESK_DEMO_MODE` | no | Set to exactly `true` only for a local synthetic demo |

HTTP Basic sends a reusable credential on every request, so any remotely reachable environment must enforce HTTPS. It is deliberately scoped to a single-operator portfolio review and is not a substitute for multi-user SSO, role-based authorization, session controls, rate limiting, or credential rotation.

## Transition rules

The rules are derived from the seven existing case actions and their established destination statuses:

| Action | Destination |
|---|---|
| `approve` | `resolved` |
| `hold` | `on_hold` |
| `escalate` | `escalated` |
| `request_kyc` | `pending_kyc` |
| `reject` | `rejected` |
| `mark_false_positive` | `false_positive` |
| `close` | `closed` |

An `open` case accepts any action. An `on_hold`, `escalated`, or `pending_kyc` case accepts any action except the action that would leave it in the same state. `resolved`, `rejected`, `false_positive`, and `closed` are terminal and accept no further decisions. Invalid transitions return `409 Conflict`.

Every decision must include the version last read by the client as `expected_version`. A stale version or a concurrent winner returns `409 Conflict`; the frontend refreshes the queue so the operator can review the winning state before trying again.

## Database and transaction behavior

Alembic revision `0003_case_version` adds `risk_cases.version` as non-null with a server default of `1`. Existing SQLite or PostgreSQL rows are preserved and initialized at version `1`. Successful decisions increment the version exactly once.

PostgreSQL performs a short conditional `UPDATE ... WHERE id = ... AND version = ... RETURNING ...`, followed by the audit insert and a single commit. No network or user interaction occurs while the transaction is open. The integration suite verifies concurrent decisions, durable audit identity, rollback on audit failure, migrations, filters, and unauthorized access.

## Verified locally

- Python 3.12 SQLite unit suite: 54 passed.
- PostgreSQL 16 integration suite: 6 passed.
- Ruff: passed.
- Frontend ESLint: passed.
- TypeScript/Vite production build: passed.
- Browser flow: sign-in, synthetic demo seed, case review, authenticated decision, audit actor, and sign-out verified locally.

## Remaining limitations

- The browser flow must be served over HTTPS outside localhost.
- Production CORS origins are not yet configurable; only the local Vite origins are allowed.
- Credentials are intentionally memory-only, so a reload requires sign-in again.
- The frontend exposes the four original dashboard actions (`hold`, `escalate`, `approve`, `close`); the API retains all seven established actions.
- No account, managed database, secret, cloud resource, deployment, or production migration was created.
- Tailwind 4 remains a separate upgrade.
