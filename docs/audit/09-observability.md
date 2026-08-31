# Observability Review

Audit date: 2026-08-31

## Current state

### Logs

The main application uses emoji-prefixed `print` statements for startup, scraping, user actions, sends, errors, and shutdown. There is no logging configuration despite `LOG_LEVEL` being read. Exceptions are formatted as strings without tracebacks or stable event names.

The setup utility has no application logging. Expected validation failures return controlled messages, while file corruption/read failures are silent.

### Health

The main daemon thread returns `200 OK` for every GET, HEAD, and POST request (`bot.py:38-61`). It does not test:

- whether Telegram polling is running;
- whether the scrape task is alive;
- time since last successful scrape;
- database connectivity;
- whether the application is shutting down.

The setup utility has no health endpoint, which is acceptable for a local operator tool.

### Metrics and tracing

- PostgreSQL stores aggregate counters and timestamps.
- There are no exported metrics, histograms, traces, correlation IDs, instance IDs, update IDs in logs, or external latency measurements.
- UptimeRobot is mentioned in README but no monitor configuration is versioned.

## Diagnosability gaps

| Question an operator must answer | Can current system answer it? |
| --- | --- |
| Is the process running? | Yes, via unconditional health endpoint |
| Is Telegram polling actually running? | No |
| When was the last successful scrape? | User-facing stats can show it, but health cannot evaluate staleness |
| How long did FIRST/Telegram/DB calls take? | No |
| Which scrape cycle created a grant? | No correlation ID |
| Why is a notification pending? | No attempt/error state |
| Is a failure permanent or transient? | No; all send exceptions look alike |
| Did startup fail because of configuration or DB? | A printed message may exist, but fatal trace/context and non-zero exit are unreliable |
| How many cards were rejected during parsing? | No |
| Which code/version/instance is running? | No startup metadata or release tag |

## Minimum production observability

The project does not need a full telemetry platform. Standard-library logging plus the hosting provider's log collection is sufficient initially.

### Structured event logging

Adopt stable event names and key/value fields:

```text
event=scrape.completed cycle_id=... duration_ms=... fetched_cards=... accepted=... rejected=...
event=notification.failed notification_id=... attempt=... error_class=rate_limited retry_in_s=...
event=telegram.update_failed update_id=... handler=subscribe error_class=...
```

Minimum common fields:

- timestamp in UTC;
- level and event name;
- release/commit and instance ID;
- `cycle_id` for scrape/fan-out;
- `update_id` for inbound handler failures;
- `notification_id` for outbound attempts;
- duration and classified outcome for external calls.

Do not log tokens, database URLs, full outbound Telegram URLs, message bodies, usernames, or raw chat IDs. If user correlation is required, log a short keyed hash or internal user row ID.

### Health semantics

Expose two small checks:

- **liveness**: event loop/process is responsive;
- **readiness**: polling and scrape task are running, startup completed, shutdown not begun, and last successful scrape is not unreasonably stale. A lightweight DB ping may be cached/rate-limited.

Return 405 for unsupported health methods. Stop readiness before shutdown work begins.

### Metrics appropriate to scale

Start with structured log counters and existing DB state. If the platform supports inexpensive metrics, expose only:

- scrape cycles success/failure and duration;
- age of last successful scrape;
- grants accepted/rejected/new;
- pending notifications and oldest pending age;
- sends by outcome/error class;
- inbound handler failures;
- startup/shutdown count/duration.

Do not introduce distributed tracing, Prometheus, OpenTelemetry collectors, or a dashboard stack until log-based diagnosis proves insufficient.

## Startup diagnostics

Log once, with secrets redacted:

- release and Python version;
- selected environment;
- polling mode and single-replica requirement;
- configured check interval and external timeouts;
- database dialect/host class, never credentials;
- schema migration version;
- setup utility disabled/retired or local-only status.

Invalid mandatory configuration must fail fast with a non-zero exit code.

## Alerting baseline

Alert only on actionable states:

- process not live;
- readiness false beyond deployment grace period;
- last successful scrape older than two expected intervals plus tolerance;
- oldest pending notification above an agreed threshold;
- repeated fatal startup or Telegram authentication failures.

Individual transient send failures do not need pages; they need aggregation and a visible retry state.

