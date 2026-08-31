# Repository Inventory

Audit date: 2026-08-31

## Scope and name mapping

The audit brief used conceptual names that do not exist in this workspace. This report uses the actual repository names:

| Brief name | Actual repository | Role found in code |
| --- | --- | --- |
| `hibe-bot` | `teamitobot-grant-tracker` | Production grant scraper, Telegram bot, PostgreSQL persistence, health endpoint |
| `telegram-integration` | `itobot-token-setup` | Local Flask UI that validates and stores a Telegram bot token |

Both repositories were clean on `main` at discovery. Neither has tags, submodules, GitHub Actions, Docker configuration, or generated source checked in.

## Executive inventory

| Concern | `teamitobot-grant-tracker` | `itobot-token-setup` |
| --- | --- | --- |
| Language/runtime | Python; README claims 3.12+; runtime not pinned | Python; minimum version not declared |
| Frameworks | `python-telegram-bot`, SQLAlchemy | Flask |
| Entry point | `python bot.py`; Procfile: `web: python bot.py` | `python app.py`; Flask development server on loopback |
| Dependency manager | `pip` requirements file | `pip` requirements file |
| Persistent state | PostgreSQL via `DATABASE_URL` | Plain JSON at `data/config.json` |
| External systems | FIRST website, Telegram Bot API, PostgreSQL | Browser, Telegram Bot API |
| Background work | Async polling plus a manual periodic scrape loop | None |
| HTTP server | Minimal health server in a daemon thread | Flask local UI |
| Tests | None | 83 pytest tests; 90% measured statement coverage over `app.py` and `token_manager.py` |
| CI/CD | None | None |
| Deployment | Render is described; only a Procfile is present | No production deployment artifact; loopback-only development server |
| Logging | Unstructured `print` calls | No application logging |
| Releases | 33 commits, no tags | 2 commits, no tags |

## Repository trees

### `teamitobot-grant-tracker`

```text
teamitobot-grant-tracker/
├── .gitignore
├── Procfile
├── README.md
├── bot.py
├── config.py
├── database.py
├── requirements.txt
└── scraper.py
```

### `itobot-token-setup`

```text
itobot-token-setup/
├── .gitignore
├── README.md
├── app.py
├── requirements.txt
├── token_manager.py
├── test_app.py
├── test_token_manager.py
├── templates/
│   ├── setup.html
│   └── success.html
└── static/
    ├── css/
    │   ├── base.css
    │   ├── setup.css
    │   └── success.css
    └── js/
        ├── setup.js
        └── success.js
```

Generated and ignored directories such as `__pycache__`, `.pytest_cache`, virtual environments, and `data/` are excluded.

## `teamitobot-grant-tracker` details

### Entry points and runtime structure

- `bot.py:579-764`, `main`: initializes tables, builds the Telegram application, registers handlers, starts a health thread, starts an async scrape task, and begins Telegram long polling.
- `bot.py:38-73`, `HealthHandler` / `start_health_server`: binds `0.0.0.0:$PORT` and returns `200 OK` for GET, HEAD, and POST.
- `bot.py:367-572`, `scrape_and_notify_loop`: manual scheduler, grant discovery orchestration, pending-notification creation, delivery, and retry-by-next-cycle behavior.
- `Procfile:1`: deploys the process as a Render-style web service.

### Modules and responsibilities

| File | Physical lines | Responsibility |
| --- | ---: | --- |
| `bot.py` | 764 | Telegram UI, health HTTP server, scheduler, application orchestration, message formatting, startup/shutdown |
| `database.py` | 825 | ORM models, engine/session globals, schema creation, all queries and commands |
| `scraper.py` | 195 | FIRST page HTTP request and HTML parsing |
| `config.py` | 73 | Import-time environment loading and validation |

### Direct dependencies

- `requests==2.31.0`: FIRST page HTTP client.
- `beautifulsoup4==4.12.2`: HTML parsing.
- `python-telegram-bot==21.7`: polling, handlers, and sends.
- `sqlalchemy==2.0.52`: ORM and schema creation.
- `python-dotenv==1.0.0`: local `.env` loading.
- `pytz==2023.3.post1`: Istanbul timezone handling.
- `psycopg2-binary==2.9.12`: PostgreSQL driver.

There is no lock file, hash verification, separation of runtime/dev dependencies, packaging metadata, or automated dependency update configuration.

### Configuration and environment variables

| Variable | Required | Default | Used |
| --- | --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Yes | None | Telegram application token |
| `DATABASE_URL` | Yes | None | SQLAlchemy engine URL |
| `ENVIRONMENT` | No | `development` | Loaded but otherwise unused |
| `CHECK_INTERVAL` | No | `900` seconds | Scrape cadence |
| `LOG_LEVEL` | No | `INFO` | Loaded but otherwise unused |
| `PORT` | No | `8080` | Health server port |

`GRANT_URL` and the 15-second request timeout are hard-coded in `config.py:40-45`. Configuration is validated at import time, but numeric ranges and URL/driver compatibility are not validated.

### External integrations and state

- FIRST grant page: fixed HTTPS URL, synchronous GET, BeautifulSoup selectors.
- Telegram: long polling and outbound `send_message` calls.
- PostgreSQL: four tables created with `Base.metadata.create_all`; no migration tool.
- Health monitoring: a process-local endpoint that does not inspect Telegram, database, or scraper health.

### Scheduling and concurrency

One process contains:

- the main asyncio event loop;
- Telegram polling/update dispatch;
- an asyncio task that wakes every two seconds and scrapes every `CHECK_INTERVAL`;
- a daemon thread running the synchronous health server.

The scraper and every SQLAlchemy call are synchronous and execute on the asyncio event-loop thread.

## `itobot-token-setup` details

### Entry points and runtime structure

- `app.py:23-36`: module-global Flask application, random-or-environment session secret, 4 KiB request limit.
- `app.py:299-570`: setup, success, change, save, and delete routes.
- `app.py:577-583`: Flask development server bound to `127.0.0.1:5000` with debug disabled.
- `token_manager.py:62-127`: atomically writes the token JSON via a same-directory temporary file and `os.replace`.

### Direct dependencies

- `Flask==3.1.3`: local web UI and signed session cookie.
- `requests==2.34.2`: Telegram `getMe` validation call.
- `pytest==9.1.1`: tests; currently mixed into runtime dependencies.

### Configuration

| Variable | Required | Default | Used |
| --- | --- | --- | --- |
| `FLASK_SECRET_KEY` | No | Random 32-byte hex value per process | Signs Flask sessions/CSRF state |

Host, port, token file path, request limits, Telegram URL, timeouts, and rate limits are source constants.

### External integrations and state

- Browser to loopback Flask server.
- Telegram `GET /bot<token>/getMe` with connect/read timeouts of 5/10 seconds.
- Token persisted as plaintext JSON under this repository's `data/` directory.
- In-memory per-IP rate-limit dictionary.

### Tests

The audit executed the suite on Python 3.13:

```text
83 passed
app.py: 93%
token_manager.py: 83%
total: 90%
```

Tests cover routes, CSRF, rate limiting, token format/validation failures, response secrecy, atomic storage behavior, and token replacement/deletion. There is no browser end-to-end test and all Telegram calls are mocked.

## CI/CD, deployment, scripts, and generated code

- Neither repository has `.github/workflows`, a Dockerfile, Compose, deployment-as-code, build scripts, release scripts, a changelog, tags, or rollback tooling.
- The main repository's sole deployment artifact is `Procfile`.
- The setup repository intentionally uses Flask's development server and has no production server dependency.
- No generated code is committed.
- No shared package, submodule, package dependency, API schema, compatibility manifest, or cross-repository build step exists.

## Shared and duplicated code

There is no shared code. Both projects use Python and `requests`, but for different requests. Token validation and storage from the setup repository are not imported or invoked by the main application. There are no duplicated domain models or DTOs because the setup repository contains no grant-domain model at all.

## Boundary-defining finding

`itobot-token-setup/token_manager.py:12-22` writes `itobot-token-setup/data/config.json`. `teamitobot-grant-tracker/config.py:18` reads only `TELEGRAM_BOT_TOKEN`. No code in either repository references the sibling path or the other's module/API. Therefore the advertised setup workflow and the bot runtime are disconnected, not independently deployable collaborating components.

