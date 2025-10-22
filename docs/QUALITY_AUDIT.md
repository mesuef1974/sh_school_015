# Quality and Performance Audit Guide

Objectives
- Improve platform performance end-to-end, safely remove unused code without breaking features.
- Reduce TTFB and TTI, lower resource consumption, and improve code quality and maintainability.
- Raise security, reliability, and test coverage.

Baseline KPIs (collect before any change)
- Backend: p95 latency and error rates for top APIs; CPU/RAM/DB utilization; slow queries (Top 10).
- DB: enable pg_stat_statements; measure queries by total time and mean time; use EXPLAIN (ANALYZE, BUFFERS) for heavy ones.
- Frontend: Lighthouse scores and Core Web Vitals; JS bundle sizes and number of requests.
- Delivery: lead time for changes, build time, flaky tests.

Quick start commands
- Run the full local quality checks:
  - Windows PowerShell: scripts/quality_checks.ps1
  - PowerShell Core: pwsh -File scripts/quality_checks.ps1
- Only install the tooling (no checks): pwsh -File scripts/quality_checks.ps1 -InstallOnly

Recommended improvements (initial tranche)
- DB
  - Enable and analyze pg_stat_statements; add missing indexes; address bloat via VACUUM/REINDEX.
  - Fix ORM N+1 by select_related/prefetch_related; use only/defer to reduce selected columns.
- Backend (Django)
  - Enable static checks: ruff, mypy, bandit; dependency audit via safety.
  - Cache responses/results (Redis recommended) where safe; add timeouts and retries for external I/O.
  - Add /livez (204, ultra-fast) and /readyz (checks DB/Redis) endpoints; use them in orchestration/dev scripts.
- Frontend (Vue + Vite)
  - Enforce ESLint and type checks (vue-tsc) in CI; enable route-level code splitting and lazy-loading.
  - Analyze bundle with visualizer and remove heavy/unused deps; optimize images/icons (SVG sprites, inline).
- Tests
  - Backend: pytest + pytest-django; factories and fast fixtures; target >= 80% coverage for models/services.
  - Frontend: vitest + testing-library/vue; E2E with Playwright/Cypress.

CI/CD and governance
- Add pre-commit: ruff, ruff-format, pycln, unimport, mypy, bandit, pytest, eslint, prettier.
- CI pipeline: build, tests, coverage, linters, security scans, conditionally deploy.
- Code review: small PRs; stricter review for sensitive paths.

Open questions to finalize the detailed plan
1) Which database is used in production and what are the largest tables? Do you have partial/functional indexes?
2) Which APIs/pages have the highest traffic and should be optimized first?
3) What is your production environment (VMs, Kubernetes, SaaS)? Do we have logging/monitoring/APM?
4) Do you have automated tests now? What is the coverage?
5) Any recurring performance incidents or errors (codes, peak times)?
6) Do you use Redis/Cache today? For what purposes?
7) Shall we start with Attendance flows first given their horizontal impact?