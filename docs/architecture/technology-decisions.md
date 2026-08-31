# Technology Decisions

Architecture freeze date: 2026-08-31

Statuses:

- **KEEP**: retain the technology and role.
- **REPLACE**: deliberately substitute an existing mechanism.
- **REMOVE**: eliminate from the maintained target after migration.
- **ADD**: introduce because it closes a measured gap.
- **DEFER**: no current justification; reconsider only with evidence/ADR.

| Technology/capability | Status | Decision and justification |
| --- | --- | --- |
| Python runtime/language | KEEP | README already targets Python 3.12+ and both repos are Python. Enforce one supported minor in CI/deployment after confirming provider support; no language rewrite |
| `python-telegram-bot` | KEEP | Existing polling/handlers/sends work; no competing SDK or missing capability justifies replacement |
| Telegram long polling | KEEP | Correct for one replica and no public ingress. Webhooks are deferred |
| SQLAlchemy | KEEP | Existing ORM supports required unit of work, constraints, and PostgreSQL locking |
| PostgreSQL | KEEP | Production target and correct tool for transactions, uniqueness, partial indexes, leases, and `SKIP LOCKED` |
| `psycopg2-binary`/sync driver | KEEP initially | Avoid driver/async ORM churn during correctness migration; review packaging/version under dependency maintenance |
| `Base.metadata.create_all` in production | REPLACE | Alembic-managed explicit migrations; `create_all` may remain test-only where appropriate |
| Alembic | ADD | Idiomatic SQLAlchemy migration/version mechanism; required by existing schema drift and target changes |
| `requests` for FIRST | KEEP initially | Existing fixed-target client works. Run bounded/offloaded; upgrade advisory-bearing version under tests. Async replacement deferred pending measurement |
| BeautifulSoup | KEEP | Current official page is HTML and selectors work; pure parser tests/hardening are needed, not parser replacement |
| In-process asyncio scheduler | KEEP | Adequate cadence/scale; extract lifecycle and make failures observable |
| APScheduler/Celery/cron service | DEFER | No scheduling complexity or separate-worker requirement |
| `python-dotenv` | KEEP for local only | `.env` convenience stays bootstrap-only; production uses provider environment. Upgrade version under dependency work |
| Typed settings framework (Pydantic/etc.) | DEFER | Standard-library immutable dataclass/parser is sufficient for current setting count |
| Pytest | KEEP | Existing setup suite proves fit; use for unit/integration/migration/lifecycle tests |
| Ruff format/lint | ADD | One fast tool addresses current lint/import/format findings and supports a CI gate |
| Mypy/strict type analysis | ADD incrementally | Gate new domain/application modules first; do not block on typing all legacy framework code immediately |
| Bandit | DEFER as mandatory gate | Audit found mostly low-value false positives. Reconsider as a non-blocking scan; prioritize dependency/secret scans and code review |
| `pip-audit` | ADD | Audit found four known advisories in main pins; automated advisory visibility has measurable value |
| Secret scanning | ADD | Prevent future token/DB credential commits; current history scan found no live secrets |
| GitHub Actions | ADD | Neither repo has CI; required for unified test/migration/package/security gates |
| `pyproject.toml` + resolved dependency workflow | ADD/REPLACE | Consolidate runtime/dev tooling and declare supported Python; replace duplicated loose requirements gradually, without opportunistic upgrades |
| Production Dockerfile | DEFER | Render Procfile currently deploys. Add only if reproducibility/hosting requires a container |
| Docker Compose | ADD for local/test PostgreSQL | Gives developers a real isolated PostgreSQL matching CI; never part of production topology by default |
| GitHub Actions PostgreSQL service container | ADD | Required for real persistence/migration acceptance tests |
| Flask token setup web app | REMOVE | Output is unused, web/CSRF/rate-limit surface is disproportionate, and plaintext file is not canonical configuration |
| Token JSON file storage | REMOVE | Production/runtime secrets use environment/provider secret store |
| Non-persisting token validation CLI | ADD only as small tool | Preserves useful format/`getMe` validation without a web service or secret store; documentation remains primary |
| External queue/broker | DEFER/reject | PostgreSQL outbox is sufficient; no throughput/isolation/ownership evidence for RabbitMQ/Kafka |
| Redis | DEFER/reject | No cache, distributed lock, or queue need; PostgreSQL owns durable coordination |
| RabbitMQ/Kafka | DEFER/reject | Adds operations and failure modes without benefit at current volume |
| CQRS/Event Sourcing | DEFER/reject | Current CRUD/use cases and auditability do not require separate models/event history |
| Kubernetes | DEFER/reject | One managed process does not need an orchestrator platform |
| Standard-library structured logging | ADD | Replace unstructured prints with redacted event fields and provider log collection |
| Liveness/readiness endpoints | ADD/REPLACE | Replace unconditional health 200 with truthful lifecycle/task/freshness checks |
| External metrics/APM/OpenTelemetry | DEFER | Structured logs, DB queue age, and provider monitoring are sufficient initially |
| Sentry/hosted error tracker | DEFER | Consider only if provider logs/alerts prove insufficient |

## Ecosystem change summary

### KEEP

Python, `python-telegram-bot`, long polling, SQLAlchemy, PostgreSQL, synchronous driver initially, requests, BeautifulSoup, asyncio scheduling, local-only dotenv, pytest, Render-compatible one-process deployment.

### ADD

Alembic, Ruff, incremental Mypy, `pip-audit`, secret scanning, GitHub Actions, real PostgreSQL test service/Compose, structured logging, truthful readiness, consolidated project/dependency metadata, optional non-persisting token validator.

### REPLACE

`create_all` production schema management, import-time configuration globals, unstructured prints, unconditional health, and duplicated dependency manifests.

### REMOVE

Flask token setup UI, local JSON token persistence, unused setup web assets/dependencies, and later proven dead compatibility APIs/fields.

### DEFER

Async ORM/client rewrite, webhooks, production Dockerfile, scheduler framework, external broker/Redis, services/workers, observability platforms, `GrantDefinition`, and any runtime/framework replacement.

