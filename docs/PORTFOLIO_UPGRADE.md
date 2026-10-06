# Portfolio Upgrade Audit

> Current status (2026-10-06): the authentication, server-derived audit identity, transition validation, and optimistic-concurrency items identified in this audit are implemented in [Access Protection and Case Transitions](ACCESS_AND_CASE_TRANSITIONS.md). The observations below describe the original audited baseline and remain as historical evidence.

Audit date: 2026-10-05
Branch: `codex/portfolio-case-filters`

## Scope and baseline

The repository contains a Vite React TypeScript dashboard and a FastAPI/SQLAlchemy API backed by local SQLite. No `AGENTS.md` file was present, so `README.md` was the only repository-specific instruction source. The working tree was clean before the upgrade and `main` matched `origin/main` at commit `16fff7a`.

Baseline checks all passed:

- Backend: 32 pytest tests passed.
- Backend: Ruff passed.
- Frontend: ESLint passed.
- Frontend: TypeScript and Vite production build passed.
- Build note: Browserslist reported that its `caniuse-lite` dataset is six months old; this is maintenance noise, not a build failure.

## Upgrade delivered

The analyst case queue now supports server-backed filters for player ID, risk level, and status. Applying a filter calls the existing `/api/v1/cases` query interface, keeps dashboard totals global, displays the number of matching cases, and provides tailored zero-result and clear-filter states. The controls reflow from a compact mobile stack to a desktop toolbar.

This was selected as the first upgrade because the API already had tested filter support but the main user interface did not expose it. It closes a visible workflow gap without expanding the product surface or introducing infrastructure.

## Browser verification

The verified story was run against a freshly seeded synthetic dataset: an analyst opens the dashboard, narrows the queue to high-risk cases, opens a matching case, records a decision, checks the refreshed status and summary, tests a zero-result filter, then clears the filters.

1. Dashboard load — healthy. The backend status changed to online and the dashboard rendered the existing dataset.
2. Queue triage — healthy. Selecting `High` issued `GET /api/v1/cases?risk_level=HIGH` and rendered one matching case.
3. Case review — healthy. Synthetic case 4 opened with its score, recommended action, triggered rules, event ID, and decision actions.
4. Decision update — healthy. Submitting `Hold` as `demo_analyst` updated the case to `On Hold`, reduced open cases from four to three, increased on-hold cases from zero to one, updated prevented exposure from €0 to €2,200, and added a new audit entry.
5. Empty state — healthy. A non-existent player filter rendered the filter-specific no-results message.
6. Reset state — healthy. Clear restored the full four-case queue.

No browser console warnings or errors were recorded during the verified flow. Verification used only simulator-generated identifiers and events in the local database; the decision changed local demo data only, and the database file is ignored by Git.

### Audit evidence

- [Original pre-upgrade responsive baseline](audit/01-baseline-dashboard-mobile.jpg)
- [Synthetic dashboard overview](screenshots/riskdesk-demo-dashboard.png)
- [Synthetic high-risk filtered queue](screenshots/riskdesk-demo-high-risk-queue.png)
- [Synthetic case review and decision](screenshots/riskdesk-demo-case-review-decision.png)
- [Synthetic decision audit trail](screenshots/riskdesk-demo-decision-audit-trail.png)
- [Synthetic mobile dashboard](screenshots/riskdesk-demo-mobile-dashboard.png)

The two superseded audit JPEGs were removed after the new PNGs were inspected. The original baseline JPEG remains because it documents the pre-upgrade layout rather than duplicating the final portfolio states. Temporary browser captures were stored outside the repository during conversion and removed afterward.

Screenshot-based accessibility evidence is limited. The new fields have programmatic labels, the form submits with Enter, and controls expose disabled state. A full keyboard, screen-reader, focus-trap, zoom, and color-contrast audit was not performed.

## Post-upgrade checks

- Backend: 34 pytest tests passed in 2.60 seconds. The filter suite includes individual status, risk, and player filters; a status-plus-risk combination; an exact status-plus-risk-plus-player combination; and a no-match response.
- Backend: Ruff passed.
- Frontend: ESLint passed.
- Frontend: production build passed in 1.91 seconds with 30 transformed modules; JavaScript output was 218.35 kB (66.69 kB gzip) and CSS was 16.97 kB (4.25 kB gzip).
- Browser: the end-to-end analyst flow above passed at 1440 by 1000 pixels and the responsive layout was inspected at 390 by 844 pixels.

## Highest-value next fixes

1. Add application authentication and authorization. Every read and mutation endpoint, including demo reset/seed and case decisions, is currently public to any caller that can reach the API.
2. Replace SQLite with persistent Postgres plus migrations. `Base.metadata.create_all()` is sufficient for the local demo but does not provide production schema evolution.
3. Make production origins configurable and deploy the frontend/API behind one protected origin or protect both projects. CORS currently permits only the two local Vite origins.
4. Add frontend component and end-to-end tests. The backend is well covered, but the React dashboard has no automated test suite.
5. Improve the case drawer as a true accessible dialog: focus entry, focus trap, focus restoration, background inertness, and an explicit dialog name.
6. Replace the hard-coded analyst name and decision note with authenticated identity and analyst-entered rationale; validate allowed state transitions on the server.
7. Add pagination, sorting, and server-side bounds to case and audit-log lists before data volume grows.

No explicit TODO or FIXME markers were found. The unfinished work is architectural and product-level rather than marked in source.

## Vercel suitability

Status: suitable after targeted deployment work; not deploy-ready in the current state.

### What fits

- The Vite frontend is directly supported by Vercel as a static build.
- FastAPI can run as one Vercel Python Function, and the current supported Python versions include 3.12 through 3.14.
- The dependency set is small and comfortably below the 500 MB uncompressed Python function limit.

References: [Vite on Vercel](https://vercel.com/docs/frameworks/frontend/vite), [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi), and [Python runtime](https://vercel.com/docs/functions/runtimes/python).

### Blocking persistence issue

The default database URL is `sqlite:///./riskdesk_ai.db`. Vercel Functions have a read-only filesystem with temporary `/tmp` scratch space, and Vercel explicitly does not support SQLite as persistent serverless storage. Multiple function instances would not share one database and local writes would not survive reliably.

Before a Vercel deployment, move to a managed Postgres database and provide `RISKDESK_DATABASE_URL` through environment variables. A no-paid-service path is a free-tier Postgres provider from the Vercel Marketplace, such as Neon, which currently advertises a free plan. Add a PostgreSQL driver, pooled/serverless connection configuration, migrations, and a production smoke test before deployment.

References: [SQLite support on Vercel](https://vercel.com/kb/guide/is-sqlite-supported-in-vercel), [Vercel runtime filesystem](https://vercel.com/docs/functions/runtimes), and [Neon Marketplace integration](https://vercel.com/marketplace/neon).

### Access protection

The application has no built-in login or API authorization. For a private portfolio demonstration, enable Vercel Authentication for all deployments. Vercel announced on 2026-09-09 that Vercel Authentication can protect preview and production deployments on every plan at no additional cost. This is appropriate for reviewer access but does not replace application-level roles, analyst identity, or endpoint authorization.

If frontend and backend are separate projects, both must be protected and cross-origin authentication must be tested. A single-origin deployment is preferable, but Vercel Services for mixed frontend/backend repositories was still documented as private beta in March 2026, so it should not be treated as the default production path without confirming account access. A conventional alternative is a static frontend project plus a separately protected FastAPI project, with explicit production CORS origins and `VITE_API_BASE_URL`.

References: [free production deployment protection announcement](https://vercel.com/changelog/protect-production-deployments-for-free-on-every-plan), [Vercel Authentication](https://vercel.com/docs/deployment-protection/methods-to-protect-deployments/vercel-authentication), and [Vercel Services](https://vercel.com/docs/services).

### Deployment prerequisites still missing

- Vercel project configuration and framework roots.
- A recognized FastAPI entrypoint or explicit `tool.vercel.entrypoint` for `backend.riskdesk_ai.main:app`.
- Persistent Postgres and migrations.
- Production environment variables.
- Configurable CORS or same-origin routing.
- Protection enabled for every reachable frontend and API URL.
- Automated CI that runs the existing backend and frontend checks before preview promotion.

No paid service, Vercel project, deployment, push, merge, or remote change was created during this upgrade.
