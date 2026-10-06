# Vercel Preview Readiness

Date: 2026-10-06
Branch: `codex/vercel-preview`

## Prepared architecture

The repository is configured as one Vercel project with two Services:

- `frontend`: Vite static build at the public root.
- `backend`: FastAPI service reached only through the public `/api/*` rewrite.

The exact `/api` route and the `/api/*` rewrite are ordered before the frontend catch-all. Vercel Services preserves the original path, so `/api/v1/cases` reaches the existing FastAPI `/api/v1/cases` route and can never fall through to Vite navigation. The frontend uses relative `/api/*` requests by default; no backend hostname or credential is compiled into the browser bundle. Local Vite development proxies `/api` to `127.0.0.1:8000` with the same browser-visible paths.

Vercel's current `services` configuration replaced the older `experimentalServices` format for new projects. Services is beta and available on all plans. The repository pins deterministic installs with `npm ci` and the existing hash-locked Python requirements file.

## Provisioned free preview resources

The isolated preview now uses only resources confirmed as free before creation:

- Vercel account `dushko-kochoski`, Hobby plan; project `riskdesk-ai` (`prj_AEc44JJDKvx9wiwww70tu64397MR`) in the personal scope. The framework preset is **Services**, builds run in `iad1`, and Vercel Authentication protects preview deployment URLs.
- Neon organization `org-fancy-fire-85380380`, Free plan; project `riskdesk-preview` (`odd-queen-78021796`) in `aws-us-east-1`, PostgreSQL 16. The isolated branch is `br-calm-mouse-b8kg176n` and database is `riskdesk_preview`.
- Neon migration owner `riskdesk_migration_owner` uses the direct connection only from a trusted operator shell. Runtime traffic uses the pooled connection as `riskdesk_app`, a non-superuser role without database/schema creation privileges and with only the required table DML and sequence access.
- The pooled runtime URL and operator credentials are sensitive Vercel Preview variables. The direct migration URL remains outside Vercel and Git. No credential is exposed through a `VITE_*` variable.
- Migrations `0001` through `0003` are applied. The guarded operator command loaded only the repository's fixed synthetic dataset: 14 events, four cases, and 32 initial audit records.

The first CLI deployment was assigned Vercel's production target automatically because it was the project's first deployment. It was protected immediately and then deleted, including its production aliases. Subsequent deployments explicitly use `--target preview`; the project has no remaining production deployment.

## Preview configuration

The following variables are scoped to Vercel **Preview**. Credentials and the database URL are marked sensitive:

   | Variable | Preview value |
   |---|---|
   | `RISKDESK_DATABASE_URL` | Neon pooled PostgreSQL URL for application traffic |
   | `RISKDESK_OPERATOR_USERNAME` | Server-side demo operator name |
   | `RISKDESK_OPERATOR_PASSWORD` | Generated high-entropy secret |
   | `RISKDESK_ALLOWED_ORIGINS` | Exact stable preview/custom origin; never `*` |
   | `RISKDESK_DEMO_MODE` | `false` |
   | `RISKDESK_DB_POOL_SIZE` | `1` |
   | `RISKDESK_DB_MAX_OVERFLOW` | `1` |
   | `RISKDESK_DB_POOL_RECYCLE_SECONDS` | `300` |

`RISKDESK_DEMO_MODE` is `false`. Do not configure `RISKDESK_MIGRATION_DATABASE_URL`, `RISKDESK_PREVIEW_SEED_ENABLED`, or database credentials as `VITE_*` variables. The migration URL is an operator-only secret and is not available to the runtime deployment.

## Migration command

Run migrations once from a trusted operator shell before allowing the new application revision to serve traffic. Use the Neon **direct** connection, not the pooled application URL:

```powershell
cd backend
$env:RISKDESK_MIGRATION_DATABASE_URL="postgresql+psycopg://MIGRATION_ROLE:REDACTED@DIRECT_HOST/riskdesk"
uv run --isolated --python 3.12 --with-requirements requirements.lock -- python -m alembic upgrade head
uv run --isolated --python 3.12 --with-requirements requirements.lock -- python -m alembic current
Remove-Item Env:RISKDESK_MIGRATION_DATABASE_URL
```

The application does not create or migrate schemas during startup.

## Controlled synthetic preview data

Public reset, seed, and simulator endpoints remain unavailable because preview sets `RISKDESK_DEMO_MODE=false`. To replace preview rows with the repository's fixed synthetic dataset, use the operator-only command after migration:

```powershell
cd backend
$env:RISKDESK_MIGRATION_DATABASE_URL="postgresql+psycopg://MIGRATION_ROLE:REDACTED@DIRECT_HOST/riskdesk"
$env:RISKDESK_DEPLOYMENT_ENV="preview"
$env:RISKDESK_PREVIEW_SEED_ENABLED="true"
uv run --isolated --python 3.12 --with-requirements requirements.lock -- python -m riskdesk_ai.seed_preview --replace
Remove-Item Env:RISKDESK_PREVIEW_SEED_ENABLED
Remove-Item Env:RISKDESK_DEPLOYMENT_ENV
Remove-Item Env:RISKDESK_MIGRATION_DATABASE_URL
```

The command is not an HTTP route. It refuses non-PostgreSQL databases, refuses non-preview environments, requires an explicit enable flag, and requires `--replace` because it deletes existing preview events, cases, and audits before loading synthetic data.

## Cost and limits

No payment method, paid integration, trial, or plan upgrade was requested or accepted. The current portfolio preview is using:

- Vercel Hobby: $0 for personal, non-commercial use. Current included usage lists 4 active CPU-hours, 360 GB-hours provisioned memory, one million function invocations, 100 GB fast data transfer, 10 GB fast origin transfer, and one million CDN requests. Services is available in beta on all plans; the first one million service requests are included, although this design uses public routing rather than a service binding.
- Neon Free: $0. As of 2026-10-02, Neon lists up to 100 projects with 1 GB storage, 100 CU-hours per project per month, autoscaling up to 2 CU, 10 branches per project, and a six-hour restore window.
- Optional Vercel Pro: not required. Current developer seats are $20 per user per month before taxes; do not upgrade or accept a paid integration plan for this preview without separate approval.

Official references: [Vercel Services](https://vercel.com/docs/services), [Services routing](https://vercel.com/docs/services/routing), [Services pricing](https://vercel.com/docs/services/pricing), [Vercel Hobby](https://vercel.com/docs/plans/hobby), and [Neon Free plan](https://neon.com/blog/neon-free-plan-1-gb-per-project).

## Verified locally and remotely

- Python 3.12 SQLite suite: 63 passed.
- PostgreSQL 16 integration suite: 7 passed, including the guarded preview seeder.
- Ruff and Alembic model/schema drift check: passed.
- Frontend ESLint and TypeScript/Vite production build: passed.
- Production npm audit: zero findings.
- Native Windows Vercel CLI 59.1.4 discovery recognized `frontend [Vite]` and `backend [FastAPI]`, but its generated Python launcher interpreted the `\backend` path segment as a backspace. Repeating the test from the no-space `C:\Projects\RiskDeskAI` checkout confirmed that the space was not the cause.
- Running that separate checkout through an ephemeral Linux/Python 3.12/Node 22 container avoided the Vercel Windows launcher defect. The shared Vercel origin returned Vite HTML at `/`, FastAPI JSON at `/api` and `/api/healthz`, the protected server response at `/api/v1/auth/me`, and a FastAPI JSON `404` at `/api/nonexistent`; the frontend catch-all did not intercept API routes.
- The normal Vite development flow verified authenticated dashboard traffic entirely through `http://127.0.0.1:5173/api/*`; health, authentication, summary, and case requests all returned `200`, with zero browser console errors or warnings.
- The Linux Vercel Preview build completed successfully with the FastAPI function in `iad1`; anonymous requests redirect to Vercel Authentication.
- Vercel's automation bypass was used only for testing behind the reviewer gate. Application authentication returned actor `portfolio_operator` and `demo_mode=false`; unauthenticated sensitive API access returned `401`.
- Remote case filtering passed for High risk, combined High/open, and no-match queries. The protected browser showed the one-case High-risk queue.
- A decision moved case 4 from Open to Escalated through the API, wrote audit record 33 with the server-derived actor, and a repeated stale version returned `409`. The protected browser then moved the same case from Escalated to On Hold and displayed the new audit trail entry.
- `/api/v1/demo/seed` returned `404` in preview. Reset and simulator routes use the same disabled demo-mode dependency and remain unavailable.

## Remaining limitations

- This is a single-operator portfolio preview using application HTTP Basic authentication behind Vercel Authentication; it is not multi-user identity, session management, or role-based access control.
- Neon Free provides limited compute, storage, history, and availability guarantees. The preview can cold-start and is not a production backup or disaster-recovery design.
- The direct migration credential remains a manual operator secret. Migrations and replacement seeding are intentionally not exposed as HTTP routes or run automatically during application startup.
- Generated preview deployment URLs change on redeploy. Same-origin browser requests work without CORS; a stable custom domain would require a separately approved DNS/configuration step.
- No production database, production deployment, custom domain, remote production migration, merge, or promotion is included in this preview task.
