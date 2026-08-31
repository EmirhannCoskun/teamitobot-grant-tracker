# Current-to-Target Module Map

Architecture freeze date: 2026-08-31

This map tells implementation engineers where current behavior belongs. It does not instruct a bulk move. Rows that split one current file must be extracted one behavior slice at a time.

## `teamitobot-grant-tracker`

| Current file/symbol | Current responsibility | Target classification | Target location/consequence |
| --- | --- | --- | --- |
| `bot.py:80-360` Telegram command/text handlers | Update parsing, DB calls, Turkish responses | Inbound Adapter | `adapters/telegram/handlers.py`; call application use cases only |
| `bot.py:88-112`, `217-335`, `491-533` message construction | Reply keyboards, status/help, grant Markdown | Inbound/Outbound Adapter | `adapters/telegram/renderer.py`; escape and length-test output |
| `bot.py:367-458` scrape/discovery orchestration | Schedule check, provider call, new-grant calculation, fan-out | Application | `application/collect_grants.py` after identity/unit-of-work ports exist |
| `bot.py:458-552` pending send loop | Grouping, batching, Telegram send, sent marks | Application + Outbound Adapter | `application/dispatch_notifications.py` and `adapters/telegram/notifier.py` |
| `bot.py:30-31` `last_scrape_time` | Process schedule state | Bootstrap | `infrastructure/scheduling.py`; clock injected for tests |
| `bot.py:38-73` health server | HTTP liveness only | Bootstrap | `infrastructure/health.py`; lifecycle-managed liveness/readiness |
| `bot.py:579-764` `main`/signals/lifecycle | Composition and process lifecycle | Bootstrap | `bootstrap/main.py`; single composition root |
| `database.py:34-127` ORM models | Users, grants, notifications, stats | Outbound Adapter | `adapters/persistence/models.py`; evolve schema compatibly |
| `database.py:133-164` engine/session/init | Global persistence bootstrap | Bootstrap + Outbound Adapter | Engine/session in `adapters/persistence/session.py`; migrations replace production `create_all` |
| `database.py:178-315` user DB methods | Queries plus subscription state transitions | Application + Outbound Adapter | subscription use cases in `application/subscriptions.py`; SQL in repository/unit of work |
| `database.py:321-385` grant upsert | Incorrect title-based identity and persistence | Domain + Application + Outbound Adapter | identity rules in `domain/identity.py`; use case/unit of work persists occurrence |
| `database.py:387-473` grant read/delete helpers | Reads and unused deletion APIs | Outbound Adapter / Deprecated | retain only called reads during transition; deletion helpers candidate for removal |
| `database.py:479-703` notification methods | Counts, pending creation/read/sent state | Application + Outbound Adapter | outbox repository in `adapters/persistence/outbox.py`; delivery rules in application/domain values |
| `database.py:709-825` stats methods | Singleton-by-convention counters | Outbound Adapter / Candidate for Simplification | atomic `system_stats` repository; remove copied/unused counters later |
| `database.py:get_db`, `get_user`, `get_user_notification_count`, `increment_user_scrape`, `get_active_users`, delete helpers | No current callers | Deprecated / Candidate for Removal | verify no external consumers, then remove in cleanup PR |
| `scraper.py:16-195` `Scraper` | HTTP fetch, HTML parse, active/FRC filtering | Outbound Adapter | split `adapters/first_web/client.py` and `parser.py`; return typed candidates |
| `config.py` | `.env`, environment reads, import-time globals/validation | Bootstrap | `infrastructure/config.py`; immutable settings constructed explicitly |
| `Procfile` | Production command | Bootstrap/Delivery | keep compatible until package entry point is released; then update in focused PR |
| `requirements.txt` | Runtime dependency manifest | Bootstrap/DevEx | migrate deliberately to `pyproject.toml`/resolved dependency workflow; no unrelated framework churn |
| `.gitignore` | Local/secret exclusions | Tool/DevEx | expand `.env.*` coverage and allow redacted `.env.example` |
| `README.md` | User/operator documentation | Tool/Documentation | update after commands/config/repository cutover stabilize |

## `itobot-token-setup`

| Current file/symbol | Current responsibility | Target classification | Target location/consequence |
| --- | --- | --- | --- |
| `app.py:54-110` CSRF | Web-only session CSRF | Deprecated / Candidate for Removal | remove with Flask UI; not needed by a CLI |
| `app.py:117-146` security headers | Web response hardening | Deprecated / Candidate for Removal | remove with Flask UI |
| `app.py:153-190` rate limiter | Web request limiting | Deprecated / Candidate for Removal | remove with Flask UI |
| `app.py:199-292` format and `getMe` validation | Useful token validation | Tool | optional non-persisting `tools/token_setup` CLI or bootstrap validation helper; no token logging/storage |
| `app.py:299-570` Flask routes | Save/change/delete token UI | Deprecated / Candidate for Removal | replace with environment/provider-secret documentation |
| `app.py:577-583` Flask development server | Loopback UI host | Deprecated / Candidate for Removal | no target runtime |
| `token_manager.py` | Atomic plaintext JSON token store | Deprecated / Candidate for Removal | no target production/local secret source; archive after transition |
| `templates/*.html` | Setup/success web UI | Deprecated / Candidate for Removal | remove after replacement documentation/CLI acceptance |
| `static/css/*.css`, `static/js/*.js` | Setup/success presentation | Deprecated / Candidate for Removal | remove with web UI |
| `test_app.py` validation/non-disclosure cases | Strong behavior tests mixed with web tests | Tool Tests | port only token format/API classification/non-disclosure cases; retire CSRF/route/UI cases |
| `test_token_manager.py` | File store behavior | Deprecated Tests | retain until file workflow is retired; then archive with repository |
| `requirements.txt` | Flask/requests/pytest | Tool/DevEx | keep only dependencies used by retained CLI/tests; Flask becomes removable |
| `README.md` | Describes unused file workflow | Deprecated / Documentation | replace with canonical configuration/secret instructions |
| `.gitignore` | Correctly ignores `data/` and `.env.*` | Tool/DevEx | preserve useful patterns in canonical repository |

## Frozen target module map

```text
src/itobot_grants/
├── domain/
│   ├── grants.py                 # GrantOccurrence values/invariants
│   ├── identity.py               # alias normalization and resolver policy
│   └── delivery.py               # states/outcomes/retry policy
├── application/
│   ├── ports.py                  # GrantSource, UnitOfWork/outbox, Notifier, Clock
│   ├── collect_grants.py
│   ├── dispatch_notifications.py
│   └── subscriptions.py
├── adapters/
│   ├── first_web/
│   │   ├── client.py
│   │   └── parser.py
│   ├── persistence/
│   │   ├── models.py
│   │   ├── session.py
│   │   ├── unit_of_work.py
│   │   └── outbox.py
│   └── telegram/
│       ├── handlers.py
│       ├── renderer.py
│       └── notifier.py
├── infrastructure/
│   ├── config.py
│   ├── health.py
│   ├── logging.py
│   └── scheduling.py
└── bootstrap/
    └── main.py

tools/token_setup/                   # optional non-persisting CLI only
migrations/                          # Alembic revisions
tests/{unit,integration,contract,fixtures}/
```

The directory tree is a destination map, not one work item. Compatibility imports/functions may temporarily bridge old and new locations.

