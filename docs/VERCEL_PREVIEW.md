# Vercel Preview Readiness

Date: 2026-10-06
Branch: `codex/vercel-preview`

## Prepared architecture

The repository is configured as one Vercel project with two Services:

- `frontend`: Vite static build at the public root.
- `backend`: FastAPI service reached only through the public `/api/*` rewrite.

The exact `/api` route and the `/api/*` rewrite are ordered before the frontend catch-all. Vercel Services preserves the original path, so `/api/v1/cases` reaches the existing FastAPI `/api/v1/cases` route and can never fall through to Vite navigation. The frontend uses relative `/api/*` requests by default; no backend hostname or credential is compiled into the browser bundle. Local Vite development proxies `/api` to `127.0.0.1:8000` with the same browser-visible paths.

Vercel's current `services` configuration replaced the older `experimentalServices` format for new projects. Services is beta and available on all plans. The repository pins deterministic installs with `npm ci` and the existing hash-locked Python requirements file.

## Current account access

No resource was created, linked, or changed.

- Vercel CLI 53.1.1 is installed, but its cached token is invalid. Project, team, integration, environment, and billing access could not be enumerated without a fresh `vercel login`.
- No `.vercel` project link exists in the repository.
- No Neon CLI, Neon environment variables, or local Neon project link were found. Neon account/project access is therefore not available from this workstation session.

## Exact account and resource setup required

1. Sign in to a Vercel account or team and confirm that this personal, non-commercial portfolio preview is eligible for Hobby. Update or use Vercel CLI 59.1.4 or newer because the installed CLI predates the current Services configuration.
2. Import the GitHub repository as one Vercel project, set its framework preset to **Services**, and keep the repository root as the project root.
3. Enable Vercel Authentication for preview deployments as an outer reviewer gate. The application's own HTTP Basic authentication remains enabled behind it.
4. Sign in to Neon and create one Free-plan project for preview in a region close to the selected Vercel function region. Create a preview database/branch and retain both its pooled application URL and direct migration URL.
5. Prefer separate database roles: a least-privilege application role for the pooled URL and a migration-owner role for the direct URL. If the initial Neon workflow supplies one role, keep the two endpoints and settings separate and split privileges before broader access.
6. Configure only the following Vercel **Preview** environment variables. Mark credentials and the database URL sensitive:

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

Do not configure `RISKDESK_MIGRATION_DATABASE_URL`, `RISKDESK_PREVIEW_SEED_ENABLED`, or database credentials as `VITE_*` variables. The migration URL is an operator-only secret and should not be available to the runtime deployment.

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

## Cost before provisioning

No paid resource is required for this portfolio-sized preview if both free tiers are eligible and remain within their limits:

- Vercel Hobby: $0 for personal, non-commercial use. Current included usage lists 4 active CPU-hours, 360 GB-hours provisioned memory, one million function invocations, 100 GB fast data transfer, 10 GB fast origin transfer, and one million CDN requests. Services is available in beta on all plans; the first one million service requests are included, although this design uses public routing rather than a service binding.
- Neon Free: $0. As of 2026-10-02, Neon lists up to 100 projects with 1 GB storage, 100 CU-hours per project per month, autoscaling up to 2 CU, 10 branches per project, and a six-hour restore window.
- Optional Vercel Pro: not required. Current developer seats are $20 per user per month before taxes; do not upgrade or accept a paid integration plan for this preview without separate approval.

Official references: [Vercel Services](https://vercel.com/docs/services), [Services routing](https://vercel.com/docs/services/routing), [Services pricing](https://vercel.com/docs/services/pricing), [Vercel Hobby](https://vercel.com/docs/plans/hobby), and [Neon Free plan](https://neon.com/blog/neon-free-plan-1-gb-per-project).

## Verified locally

- Python 3.12 SQLite suite: 63 passed.
- PostgreSQL 16 integration suite: 7 passed, including the guarded preview seeder.
- Ruff and Alembic model/schema drift check: passed.
- Frontend ESLint and TypeScript/Vite production build: passed.
- Production npm audit: zero findings.
- Vercel CLI 59.1.4 local discovery recognized `frontend [Vite]` and `backend [FastAPI]` plus the shared URL. Its Windows development runtime then hit a CLI-generated Python path escaping bug (`\backend` interpreted as a backspace), so a full `vercel dev -L` runtime check remains for Linux or a future fixed CLI.
- The normal Vite development flow verified authenticated dashboard traffic entirely through `http://127.0.0.1:5173/api/*`; health, authentication, summary, and case requests all returned `200`, with zero browser console errors or warnings.

## Remaining gates before deployment

- Restore Vercel login and verify team, plan, Services access, GitHub connection, project framework preset, and preview protection.
- Confirm Neon account access, region, project ownership, roles, pooled/direct URLs, backups, and usage limits.
- Replace the origin placeholder with the exact assigned stable preview or custom domain.
- Run the migration and controlled seed against the actual isolated preview database.
- Perform a protected preview smoke test through Vercel Authentication and application authentication.
- No production database, production environment, or custom domain is part of this preview task.
