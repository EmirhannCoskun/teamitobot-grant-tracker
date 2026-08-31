# Testing Strategy

Audit date: 2026-08-31

## Existing tests and validation results

| Repository | Unit | Integration | E2E | Contract | Smoke | Audit execution |
| --- | --- | --- | --- | --- | --- | --- |
| `teamitobot-grant-tracker` | None | None | None | None | None | Python compilation passed; pytest collected zero tests; isolated defect probes executed |
| `itobot-token-setup` | Strong route/storage unit tests with mocks | Local filesystem integration through temp paths | None | Mocked Telegram response shapes | None | 83 passed on Python 3.13; 90% measured coverage |

Setup coverage detail:

```text
app.py             93%
token_manager.py   83%
total              90%
```

One duplicate test name is redefined at `test_app.py:734` and `:1929`; Python collects only the latter definition. The suite still ran 83 distinct collected tests.

## Critical workflow coverage

| Workflow | Current coverage | Risk |
| --- | --- | --- |
| FIRST happy-path parsing | None | High |
| Missing/malformed FIRST fields | None | High; a missing details node aborts cycle |
| Active-date and FRC filtering | None | High |
| Grant natural-key persistence | None | High; direct probe exposed mismatch |
| Atomic grant + notification fan-out | None | High |
| Duplicate notification intent | No automated test in main | High |
| Telegram update routing | None | Medium |
| Telegram message escaping/limits | None | High |
| Telegram retry/permanent failure | None | High |
| Restart after send before mark | None | High |
| Configuration/startup | None | Medium |
| Graceful shutdown | None | Medium |
| Token form validation/CSRF/rate limit | Extensive | Low |
| Token file atomic save/delete/corruption | Good, with some uncovered error branches | Low |
| Setup-to-bot configuration contract | None; no contract exists | Blocker |

## Risk-based test matrix

| Priority | Test level | Scenario | Assertions |
| --- | --- | --- | --- |
| P0 | Unit | Parse a sanitized current FIRST page fixture | FRC-only, active-only, exact title/dates/URL |
| P0 | Unit | Details panel missing; dates malformed; selector drift | One bad card is isolated; cycle result explicitly indicates health |
| P0 | Persistence integration | Same title, different date window | Two identities/rows after approved migration; no overwrite |
| P0 | Persistence integration | Concurrent/repeated grant discovery | One grant identity and one user/grant intent |
| P0 | Transaction integration | Failure halfway through fan-out | Grant and all intended rows commit together or none do |
| P0 | Application unit | Send succeeds then mark fails | Duplicate-risk state is explicit; retry contract is at-least-once |
| P0 | Telegram adapter unit | Titles/URLs with Markdown control characters and max lengths | Valid Telegram payload and deterministic batching |
| P0 | Startup smoke | Missing/invalid token, URL, interval, port, DB unavailable | Redacted error and non-zero exit/readiness false |
| P1 | Handler unit | Duplicate `/start`, subscribe, unsubscribe | State idempotency and expected responses |
| P1 | Application unit | Telegram timeout, rate limit, forbidden, bad request | Correct classification/backoff/deactivation/quarantine |
| P1 | Application unit | FIRST empty valid result versus scrape failure | Empty success increments scrape; failure does not |
| P1 | Integration | PostgreSQL timezone round trip | UTC storage and Istanbul presentation are consistent |
| P1 | Lifecycle | SIGTERM during idle, scrape HTTP, DB transaction, send | Safe bounded shutdown and exit code |
| P1 | Contract | Setup/exported secret interface, while utility exists | Output is actually consumable by main or explicitly deployable |
| P2 | Browser E2E | Save/change/delete token locally | UI behavior, CSP, no token exposure |
| P2 | Deployment smoke | Start built release against disposable PostgreSQL and mocked Telegram/FIRST | Health/readiness, migration version, polling bootstrap |

## Baseline protection before refactoring

1. Freeze representative Telegram responses as behavior assertions, not exact internal call structures.
2. Save a sanitized FIRST HTML fixture with its retrieval date and an explicit update process. Do not make ordinary CI depend on the live site.
3. Add pure parser tests before moving `scraper.py`.
4. Add application tests around discovery/fan-out/delivery semantics before changing transactions.
5. Add PostgreSQL integration tests for constraints and timezone behavior; SQLite alone cannot prove PostgreSQL semantics.
6. Keep setup's 83 tests running during consolidation; split the 2,248-line module by behavior and remove the shadowed duplicate.

## Test architecture

Use small ports/fakes, not broad mocking of internal implementation:

- `GrantSource` fake returns candidates or classified failures.
- `GrantRepository` test implementation captures transaction behavior.
- `Notifier` fake records sends and returns transient/permanent outcomes.
- `Clock` fake makes active dates, cadence, and retry time deterministic.
- Telegram adapter tests construct framework updates only at the adapter boundary.

Application tests should assert stable outcomes such as “notification intent created once” and “blocked user deactivated,” not the exact number/order of private method calls.

## CI quality gates

Initial gates:

- compile/import smoke;
- Ruff lint;
- unit tests;
- PostgreSQL integration tests;
- setup tests while retained;
- dependency advisory audit;
- secret scan;
- deployment startup smoke on pull requests that affect runtime/config/migrations.

Do not impose a global coverage percentage as a substitute for critical-path cases. Track coverage to find gaps, with P0 behavior tests as the merge gate.

