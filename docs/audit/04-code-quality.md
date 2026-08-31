# Code Quality Audit

Audit date: 2026-08-31

## Severity model

- **BLOCKER**: prevents a stated system capability or makes a planned structural change unsafe.
- **HIGH**: credible correctness, data loss, security, or production-operation risk.
- **MEDIUM**: meaningful maintainability/reliability issue with a bounded current impact.
- **LOW**: localized debt or scale-dependent risk.
- **INFORMATIONAL**: evidence or positive practice that needs no immediate change.

## Findings

| ID | Severity | Finding | Concrete evidence | Impact |
| --- | --- | --- | --- | --- |
| CQ-01 | BLOCKER | The token setup product does not configure the bot | `itobot-token-setup/token_manager.py:12-22` writes local JSON; `teamitobot-grant-tracker/config.py:18` reads environment only; no cross-reference exists | The second repository's primary advertised outcome is false for the combined system |
| CQ-02 | HIGH | Grant identity is implemented inconsistently | `bot.py:406-424` compares title + dates; `database.py:333-380` matches title/text only; probe returned the same ID for two seasons | A recurring grant can overwrite history and fail to notify users |
| CQ-03 | HIGH | Discovery and notification-intent creation are not atomic | `bot.py:438-452` calls multiple independently committing DB methods | Crash/DB failure after grant commit permanently skips notifications for some users |
| CQ-04 | HIGH | Main production behavior has no tests | No `test_*`, pytest config, or CI exists in the main repository; audit collected zero tests | Refactoring or dependency changes can silently break the core system |
| CQ-05 | HIGH | Schema evolution is unmanaged | `database.py:68` says a migration is incomplete; startup only calls `create_all` at `database.py:147-150` | Existing production schemas can drift; deploy/rollback compatibility is unknown |
| CQ-06 | HIGH | Fatal and recoverable errors are broadly swallowed | `bot.py:568-572`, `699-702`, `762-764`; `scraper.py:193-195` | Process can exit successfully after fatal failure; causes and tracebacks are lost |
| CQ-07 | MEDIUM | One malformed grant card can fail the complete scrape | `scraper.py:140-146` references `apply_link` without initialization when details lookup fails; reproduced by probe | All grants are skipped for that cycle |
| CQ-08 | MEDIUM | Core modules and orchestration are oversized | `bot.py` is 764 physical lines; `database.py` is 825; `scrape_and_notify_loop` spans `bot.py:367-572` | Concerns are hard to test and change independently |
| CQ-09 | MEDIUM | Synchronous external I/O runs on the asyncio event loop | `Scraper.scrape` uses `requests.get`; all `DB` methods are synchronous; called directly by async handlers/loop | Telegram commands can stall during HTTP or database latency |
| CQ-10 | MEDIUM | External strings are inserted into Telegram Markdown unescaped | `bot.py:498-532` interpolates scraped title and URL using Markdown | Valid grant content can cause parse errors and poison retries |
| CQ-11 | MEDIUM | Timezone semantics are inconsistent | ORM uses `DateTime` without timezone; aware Istanbul values are written; `bot.py:278-297` treats one naive field as Istanbul and another as UTC | Displayed scrape time can be shifted; database behavior varies by driver |
| CQ-12 | MEDIUM | Health endpoint is unconditional and detached from lifecycle | `bot.py:41-58` always returns 200; server runs in daemon thread and is never stopped | Monitoring reports healthy while polling, DB, or scraper is broken |
| CQ-13 | MEDIUM | Configuration is only partially validated | `config.py:31-34` converts numeric values at import but does not validate ranges; `LOG_LEVEL` and `ENVIRONMENT` are unused | Zero/negative intervals can create a scrape storm; bad health port failure is swallowed |
| CQ-14 | MEDIUM | Setup app combines routing, security, rate limiting, API client, and config in one module | `itobot-token-setup/app.py` is 583 physical lines | Still testable, but changes have a broad blast radius |
| CQ-15 | LOW | Setup test module contains shadowed duplicate test code | `test_app.py:734` and `test_app.py:1929` define the same test name; Ruff F811 | Earlier test definition is never collected, reducing clarity |
| CQ-16 | LOW | Unused APIs and fields add misleading surface | `database.py:get_db`, `get_user`, delete helpers, `increment_user_scrape`, and `get_active_users` have no callers; config fields are unused | Readers cannot distinguish supported behavior from abandoned work |
| CQ-17 | LOW | Stats row is singleton only by convention | `database.py:710-723` queries `.first()` and creates with no unique key | Concurrent startup can create multiple rows and inconsistent counters |
| CQ-18 | LOW | Magic operational values are embedded in orchestration | Batch size 5 (`bot.py:481-489`), two-second wake (`560`), ten-second error sleep (`572`) | Tuning and testing require code edits |
| CQ-19 | INFORMATIONAL | Current module dependency graph has no circular imports | `config` is depended upon by DB/scraper; `bot` is the composition root | A staged extraction is feasible without rewrite |
| CQ-20 | INFORMATIONAL | Setup utility has unusually strong tests for its size | 83 tests passed; 90% measured coverage | Preserve these behaviors if the tool moves or is retired |

## Static-analysis context

Ruff reported 20 findings in the main repository and 5 in the setup repository. Most were import/style/type-modernization items; the material findings were broad exception handling and the duplicated test definition. Bandit reported one medium-confidence bind-all-interfaces warning for the main health server and no medium/high production-code findings in the setup utility. The setup token-key string was a false-positive low-severity password heuristic.

Static tools did not discover the most important issues: cross-repository disconnection, identity mismatch, transaction gaps, and delivery semantics required flow reconstruction and direct probes.

## Maintainability assessment

The code is understandable because the system is small, naming is generally direct, inheritance is minimal, and there are few abstractions. Maintainability risk comes from concentration of responsibilities and absent core tests, not from excessive patterns. The modernization should extract use cases and I/O seams while resisting a large framework or class hierarchy.

