# Final Engineering Report

Audit date: 2026-08-31

## 1. Executive Summary

The grant bot is a small, understandable system with an appropriate basic technology stack: Python, Telegram long polling, BeautifulSoup, SQLAlchemy, and PostgreSQL. The live FIRST happy path worked during the audit, the setup utility has a strong 83-test suite, secrets are not committed, and notification rows have a useful user/grant uniqueness constraint.

Overall engineering health is **2/5**. The bot can operate, but core correctness and production recovery rely on untested, non-atomic sequences. The largest architectural issue is not excessive complexity; it is a false two-repository boundary. The token setup repository does not configure or communicate with the bot.

No production code, schema, public API, repository location, or deployment was changed by this audit.

## 2. Current Architecture

`teamitobot-grant-tracker` runs one process containing:

- Telegram long polling and command/text handlers;
- an in-process periodic FIRST scraper;
- synchronous SQLAlchemy/PostgreSQL access;
- pending-notification fan-out and Telegram sending;
- a daemon-thread HTTP health server.

`itobot-token-setup` is a separate loopback Flask application. It validates a Telegram token through `getMe` and atomically stores plaintext JSON locally. The production bot reads only an environment variable, so the two repositories have no runtime or configuration flow.

Detailed reconstruction: [02-runtime-and-data-flow.md](02-runtime-and-data-flow.md).

## 3. Top Risks

Maximum ten, ordered by impact and urgency:

1. **Disconnected setup boundary:** saved setup token is never consumed by the bot (`token_manager.py:12-22`; main `config.py:18`).
2. **Grant identity corruption/missed recurring grants:** application compares title + dates, while DB upserts by title only (`bot.py:406-424`; `database.py:333-380`).
3. **Permanent partial fan-out loss:** grant and per-user notification intents are separate commits (`bot.py:438-452`).
4. **No production-bot tests:** zero tests cover scraper, DB, handlers, delivery, restart, or shutdown.
5. **No schema migrations:** legacy schema evolution exists but startup only runs `create_all` (`database.py:68-75`, `147-150`).
6. **Unmodeled at-least-once delivery:** crash after Telegram send and before DB mark duplicates notifications (`bot.py:526-540`).
7. **Fatal failures are swallowed and health is false-green:** broad catches/normal exit plus unconditional 200 health (`bot.py:38-73`, `699-764`).
8. **Single-replica constraint is unenforced:** multiple processes would compete for polling/scraping/delivery and corrupt stats.
9. **Scraper/Markdown poison paths:** one missing details target aborts a cycle; unescaped upstream text can be rejected by Telegram (`scraper.py:140-146`; `bot.py:491-532`).
10. **Core event loop can block:** synchronous HTTP and database operations run inside async handlers/scheduler.

## 4. Repository Boundary Decision

**Should the system remain two repositories: NO.**

Choose **MERGE INTO SINGLE APPLICATION** as a repository/production-boundary decision:

- one canonical repository;
- one deployable modular bot process;
- Telegram as an adapter to application use cases;
- provider environment secret as the canonical token source;
- setup UI retained only temporarily as non-deployed loopback tooling if active users truly need it, otherwise retired.

Do not merge Flask routes into the bot runtime or expose credential mutation through the health endpoint. Full rationale and option trade-offs: [ADR-001](../adr/ADR-001-repository-boundary.md).

## 5. Recommended Architecture

A lightweight ports-and-adapters modular monolith:

```text
Domain value types/rules
        ↑
Application use cases and meaningful I/O ports
        ↑
Telegram / FIRST / SQLAlchemy adapters
        ↑
Bootstrap, scheduling, health, configuration
```

Key application transactions:

- persist one grant discovery and its recipient notification intents atomically in PostgreSQL;
- send outside the transaction with explicit at-least-once semantics and bounded classified retry;
- keep one process/replica until evidence requires more.

Full target: [target-architecture.md](../architecture/target-architecture.md).

## 6. Immediate Fixes

Before major refactoring:

1. Add behavior tests and a sanitized FIRST fixture.
2. Fix per-card scraper error isolation and initialize `apply_link`.
3. Introduce migration tooling based on the actual production schema.
4. Correct grant natural-key behavior through a rehearsed data migration.
5. Make discovery + notification-intent fan-out one DB transaction.
6. Escape Telegram output and test message limits.
7. Classify retries/permanent Telegram errors and make pending state observable.
8. Fail fatal startup/runtime errors non-zero; implement truthful readiness.
9. Upgrade advisory-bearing dependencies under tests.
10. Correct documentation: setup file does not configure production; enforce one replica.

## 7. Refactoring Roadmap

Ordered transformation:

1. Stage 0 — baseline tests, CI, logs, runtime pin.
2. Stage 1 — correctness/security/reliability defects and migrations.
3. Stage 2 — extract application, Telegram, FIRST, persistence, bootstrap boundaries.
4. Stage 3 — consolidate repositories after behavior is protected.
5. Stage 4 — expand risk-based integration/lifecycle tests.
6. Stage 5 — readiness, retry visibility, deployment/release/rollback hardening.
7. Stage 6 — dead code, legacy column, dependency, test, and documentation cleanup.

Every stage keeps the application deployable. Details: [migration-roadmap.md](../architecture/migration-roadmap.md).

## 8. What NOT To Change

- Do not replace Python, SQLAlchemy, PostgreSQL, BeautifulSoup, or `python-telegram-bot` merely for architectural fashion.
- Do not introduce microservices, a broker, Redis, Kafka, Kubernetes, CQRS, or distributed tracing.
- Do not switch polling to webhooks without a demonstrated availability/scale requirement.
- Do not claim or attempt exactly-once Telegram delivery; document at-least-once and minimize duplicates.
- Do not rewrite the well-tested token manager if the local tool is temporarily retained; preserve atomic write, CSRF, CSP, size limits, and non-disclosure tests.
- Do not add speculative indexes or async frameworks before measuring row counts and latency.
- Do not change public Telegram commands/messages or schema before baseline protection and approved migrations.

## 9. Enterprise Readiness

The term is interpreted as production engineering discipline appropriate to this system's scale, not adoption of enterprise infrastructure.

| Area | Score | Evidence |
| --- | ---: | --- |
| Architecture | 2/5 | Simple one-process topology is suitable, but boundaries are mixed and the second repository has no integration contract |
| Maintainability | 2/5 | Code is readable and non-circular, but `bot.py`/`database.py` are oversized and application decisions depend on infrastructure |
| Testing | 2/5 | Setup has 83 passing tests/90% coverage; production bot has zero tests |
| Security | 3/5 | No committed live secrets, fixed request targets, ORM, CSRF/CSP/limits; plaintext local token, PII logs, known dependency advisories, and unsafe public-exposure potential remain |
| Reliability | 2/5 | Pending rows, timeouts, and shutdown handling exist; transaction gaps, duplicate/loss windows, unbounded retries, and blocking I/O remain |
| Observability | 1/5 | Unstructured prints, no tracebacks/correlation/latency, and unconditional health response |
| CI/CD | 1/5 | No CI, migration/release/version/rollback automation, runtime pin, or deployment-as-code beyond a Procfile |
| Documentation | 2/5 | Detailed READMEs exist, but main tree is stale and the setup documentation describes an output the bot never reads |

## 10. Final Recommendation

Protect behavior first, correct the grant identity and transaction defects, then extract a few meaningful ports around the small application core. Consolidate to one canonical repository and one deployable bot only after those protections exist. Keep long polling, PostgreSQL, and the current frameworks. Treat the Flask setup screen as temporary local tooling—not a service—and retire it if no real operator workflow depends on it.

This is a modernization of boundaries and production discipline, not a rewrite.

## Document index

- [01 Repository Inventory](01-repository-inventory.md)
- [02 Runtime and Data Flow](02-runtime-and-data-flow.md)
- [03 Domain Boundaries](03-domain-boundaries.md)
- [04 Code Quality](04-code-quality.md)
- [05 Telegram Integration](05-telegram-integration.md)
- [06 Security](06-security.md)
- [07 Reliability](07-reliability.md)
- [08 Data Architecture](08-data-architecture.md)
- [09 Observability](09-observability.md)
- [10 Testing Strategy](10-testing-strategy.md)
- [11 Delivery and Operations](11-delivery-and-operations.md)
- [12 Dependencies](12-dependencies.md)
- [Technical Debt Register](technical-debt-register.md)
- [ADR-001](../adr/ADR-001-repository-boundary.md)
- [Target Architecture](../architecture/target-architecture.md)
- [Migration Roadmap](../architecture/migration-roadmap.md)

