# PostgreSQL Deployment Foundation

Date: 2026-10-05
Branch: `codex/postgres-deployment-foundation`

## Delivered scope

This change establishes a deployable database foundation without provisioning or changing any cloud resource:

- Python 3.12 is the supported backend and CI runtime.
- The hashed lockfile is generated for Python 3.12 and includes Alembic and Psycopg 3.
- SQLAlchemy supports PostgreSQL with connection health checks and a bounded application pool.
- Alembic owns schema creation and evolution. Application startup no longer creates tables.
- Application and migration connections use separate settings.
- SQLite remains available for isolated unit tests and zero-service local development.
- PostgreSQL 16 integration tests run real migrations, combined case filters, decisions, audit persistence, and failure rollback.
- The case queue gains indexes for `recommended_action` and the common status/risk/date access pattern.

The change does not provision PostgreSQL, deploy the application, migrate a production database, add authentication, or perform the separate Tailwind upgrade.

## Connection settings

Use environment variables or the deployment platform's encrypted secret store. Do not put connection strings in Git or a frontend `VITE_*` variable.

| Setting | Purpose |
|---|---|
| `RISKDESK_DATABASE_URL` | Pooled application connection used by FastAPI |
| `RISKDESK_MIGRATION_DATABASE_URL` | Direct database connection used only by Alembic |
| `RISKDESK_DB_POOL_SIZE` | Application pool size; defaults to `5` |
| `RISKDESK_DB_MAX_OVERFLOW` | Temporary application connections above the pool; defaults to `5` |
| `RISKDESK_DB_POOL_RECYCLE_SECONDS` | Connection recycle interval; defaults to `300` |

For a managed serverless PostgreSQL provider, use its pooled URL for application traffic and direct URL for migrations. Alembic uses a non-persistent connection pool so migration sessions cannot consume the application's pool allowance.

Example placeholders:

```powershell
$env:RISKDESK_DATABASE_URL="postgresql+psycopg://APP_USER:REDACTED@POOLED_HOST/riskdesk"
$env:RISKDESK_MIGRATION_DATABASE_URL="postgresql+psycopg://MIGRATION_USER:REDACTED@DIRECT_HOST/riskdesk"
```

## Fresh database setup

Install the committed lock, set only the migration connection for the target environment, then upgrade explicitly:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
$env:RISKDESK_MIGRATION_DATABASE_URL="postgresql+psycopg://..."
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

Only start application instances after the migration succeeds. Migration execution must be a single release step, not part of a web-function startup path.

## Existing SQLite installations

The application still defaults to `sqlite:///./riskdesk_ai.db`, and this change never edits or deletes that file automatically. Back up the file and stop every writer before adopting migrations.

An existing database created by the previous `Base.metadata.create_all()` schema already corresponds to revision `0001_initial_schema`. After confirming that it has the `events`, `risk_cases`, and `audit_logs` tables, stamp that baseline and apply the additive index migration:

```powershell
cd backend
Copy-Item riskdesk_ai.db riskdesk_ai.before-alembic.db
$env:RISKDESK_MIGRATION_DATABASE_URL="sqlite:///./riskdesk_ai.db"
.\.venv\Scripts\python.exe -m alembic stamp 0001_initial_schema
.\.venv\Scripts\python.exe -m alembic upgrade head
```

`stamp` records the matching baseline without recreating tables or changing rows. Revision `0002_case_queue_indexes` adds indexes. Revision `0003_case_version` adds a non-null `version` column with a default of `1`; existing cases are retained and initialized to version `1`. The automated SQLite adoption test verifies that existing event and case rows survive this sequence.

Do not stamp an installation whose schema was manually changed or is missing a baseline table. Take a copy and reconcile its schema first.

Moving existing SQLite rows into PostgreSQL is a separate data-transfer operation, not a schema migration. The safe production procedure is:

1. Retain an immutable SQLite backup.
2. Create the empty PostgreSQL schema with `alembic upgrade head`.
3. Export and import tables in dependency order: `events`, `risk_cases`, then `audit_logs`.
4. Advance PostgreSQL identity sequences beyond the imported maximum IDs.
5. Compare row counts, foreign-key coverage, case statuses, and audit-log details.
6. Run the full PostgreSQL integration and smoke suites before switching `RISKDESK_DATABASE_URL`.

An automated SQLite-to-PostgreSQL data-copy utility is intentionally not included yet. Existing files remain usable and untouched; a production cutover must not proceed until a project-specific transfer rehearsal and reconciliation are complete.

## Local PostgreSQL verification

The integration suite requires an isolated PostgreSQL database whose name contains `test`. CI supplies an ephemeral PostgreSQL 16 service with synthetic credentials. A local example is:

```powershell
docker run --name riskdesk-postgres-test `
  -e POSTGRES_DB=riskdesk_test `
  -e POSTGRES_USER=riskdesk `
  -e POSTGRES_PASSWORD=riskdesk_test_only `
  -p 55432:5432 `
  -d postgres:16-alpine

$env:RISKDESK_TEST_DATABASE_URL="postgresql+psycopg://riskdesk:riskdesk_test_only@localhost:55432/riskdesk_test"
$env:RISKDESK_TEST_MIGRATION_DATABASE_URL=$env:RISKDESK_TEST_DATABASE_URL
python -m pytest -m integration
```

The suite deliberately downgrades and rebuilds the named test database. Its guard rejects non-PostgreSQL URLs and database names without `test`.

## Remaining deployment limitations

- No managed PostgreSQL account, project, credentials, backups, or region have been selected.
- No production data transfer has been rehearsed.
- The current HTTP Basic protection is suitable only for the single-operator portfolio demo over HTTPS; multi-user identity, roles, session expiry, rate limiting, and credential rotation remain future work.
- Production secrets still need to be created in the selected host's encrypted secret store.
- Production CORS and a recognized Vercel backend entrypoint remain to be configured.
- Connection limits must be tuned against the selected provider's actual plan before deployment.
- Deployed end-to-end tests remain outstanding.
- Tailwind 4 remains a separate migration.

## Verified results

Local verification used Python 3.12.13 and an isolated PostgreSQL 16 Docker container:

- Clean `--require-hashes` installation from `backend/requirements.lock`: passed, 36 packages.
- Ruff: passed.
- SQLite unit suite: 34 passed, including the existing-database adoption path.
- PostgreSQL integration suite: 4 passed.
- Alembic model/schema drift check: no new upgrade operations detected.
- Frontend production dependency audit: zero findings.
- Frontend ESLint: passed.
- Frontend TypeScript/Vite production build: passed, 30 modules transformed.

FastAPI/Starlette emits one upstream deprecation warning because its test client still imports the legacy `httpx` package path. It does not affect test outcomes. No warning was suppressed or check weakened.
