# Reliability and Failure Modes

Audit date: 2026-08-31

## Reliability model found

The system is a single process with one database, one periodic scraper, long polling, and at-least-once outbound attempts. This topology is appropriate for the product's likely scale. Reliability risk comes from transaction gaps, broad exception handling, blocking I/O, and weak diagnostics—not from lack of distributed infrastructure.

## Failure-mode analysis

| Failure mode | Current behavior | Data/integrity risk | Retry safety | Desired behavior | Operator visibility |
| --- | --- | --- | --- | --- | --- |
| FIRST timeout | 15-second connect/read timeout setting; scraper returns `None`; next scheduled cycle tries again | No DB mutation; freshness delayed | Safe | Add a wall-clock deadline if needed; record latency/result/reason; use the normal schedule during an outage | Structured warning and last-success age |
| FIRST HTTP/network error | Caught as request error; entire cycle fails | No DB mutation | Safe | Same as timeout; distinguish status/network | Status, latency, failure count |
| Malformed page/card | Date parse skips card; unexpected exception aborts whole scrape | Valid grants can be missed | Safe to retry, but deterministic poison repeats | Isolate per-card parsing; reject bad card with evidence; fail cycle if source contract broadly changes | Parsed/rejected counts and selector-contract alarm |
| Telegram unavailable/network error | Batch remains pending; retried every scrape interval | Duplicate possible if remote accepted before local exception/commit | At-least-once only | Classify transient error; retry with bounded backoff/jitter | Notification ID, attempt, class, next retry |
| Telegram rate limit | Generic exception; ignores retry-after; continues sends | Retry storm and continued failures | Usually safe but inefficient | Respect retry-after and pace sends | Rate-limit count and wait |
| User blocked bot/invalid chat | Generic exception; user stays active; retries forever | Poison pending row and log noise | Not useful | Mark chat inactive after classified permanent error; keep audit reason | User deactivation count, not raw chat ID |
| Invalid Markdown/message | Generic exception; pending rows retry forever | Other items in the batch can remain undelivered | Deterministic retry unsafe/useless | Escape output; quarantine after bounded attempts | Render/send failure with notification IDs |
| DB unavailable at startup | `init_db` raises; outermost handler prints; process exits normally | No startup mutation; no service | Retry may be platform-managed | Fail fast non-zero; provider restarts; startup log identifies DB readiness | Readiness false and fatal traceback |
| DB unavailable during discovery | Broad loop catch; some previous DB calls may already be committed | Partial grant/notification creation; permanent missed recipients | Some methods safe, transaction sequence is not | Persist grant + intended recipients in one transaction | Cycle/transaction ID and rollback result |
| DB unavailable after Telegram send | Send may succeed, mark fails | Duplicate on retry | At-least-once only | Explicitly accept/document duplicate possibility; update attempt state when DB returns | Sent-but-uncommitted warning |
| Crash after grant commit | Remaining per-user pending rows are never created because grant is now known | Permanent notification loss | Current restart does not reconcile | Atomic grant/intents transaction or deterministic reconciliation | Reconciliation counters |
| Crash after send before mark | Pending row is resent | Duplicate user message | Cannot guarantee exactly once | At-least-once contract; minimize window; make message/report traceable | Duplicate-risk event |
| Duplicate Telegram update | No update-ID storage; command may run again | State commands mostly idempotent; duplicate replies | Mostly safe | Test and document idempotency; persist only if future commands have non-idempotent effects | Update ID in error logs |
| Restart with pending inbound updates | `drop_pending_updates=True` discards backlog | User commands during downtime are lost | Not retried | Choose intentionally; likely set false once handlers are proven idempotent | Startup count/policy log |
| Invalid configuration | Missing required values fail at import; invalid integers raise; bad ranges pass | Process may exit 0; zero interval can scrape continuously | N/A | Validate typed settings/ranges, redact values, exit non-zero | One startup configuration summary |
| Connection interruption during shutdown | Scraper has connect/read inactivity limits but no total deadline; DB is unbounded; health thread is not stopped | Partial sequence risks above | Depends on operation | Set shutdown deadline; stop accepting work; cancel only at safe boundaries | Shutdown phase/duration |
| Multiple application replicas | Each replica polls/scrapes/sends and mutates stats | Duplicate work, polling conflict, lost counter updates | Not safe | Enforce one replica; add leader lock only if scale requirement appears | Instance ID and startup guard |
| Corrupted setup token file | `get_token` silently returns `None`; UI shows setup | Existing file/state is hidden as “not configured” | Operator can overwrite | Distinguish absent, corrupt, unreadable; preserve file for diagnosis without exposing token | Redacted local error |

## Transaction and idempotency assessment

### Discovery

The database uniqueness constraint only covers notification rows. Grant uniqueness is neither modeled nor constrained. `add_grant` and every `create_pending_notification` commit independently. This violates the natural application transaction: **record one discovery and all notification intents for the subscriber snapshot**.

The minimal fix is one database transaction for this unit of work, plus a database uniqueness constraint that matches the natural grant key. It does not require a message broker.

### Delivery

Database state and Telegram cannot participate in one transaction. The application should explicitly implement at-least-once delivery:

- durable pending intent;
- bounded attempt metadata;
- classified permanent/transient outcomes;
- send, then mark sent;
- clear documentation that a rare duplicate can occur after an ambiguous send/crash.

Exactly-once claims would be false without a Telegram idempotency facility.

## Timeouts and cancellation

- FIRST GET: one 15-second value applies to connect/read inactivity, not a strict total deadline; useful but incomplete.
- Setup Telegram validation: explicit `(5, 10)` connect/read timeouts; good baseline.
- Telegram polling: explicit 30-second long-poll timeout.
- SQLAlchemy: no explicit connect/statement timeout or `pool_pre_ping`.
- Outbound `send_message`: relies on library defaults; no app-level deadline or classified timeout handling.
- Synchronous scraper and DB calls cannot be cancelled cleanly while on the event loop.

## Retry policy appropriate to scale

No retry library or broker is needed. A small persisted attempt model and simple policy is enough:

| Operation | Attempts | Backoff | Notes |
| --- | --- | --- | --- |
| Periodic FIRST scrape | Natural next scheduled run | Existing interval; optionally jitter | Do not tight-loop on failure |
| Telegram transient send | Bounded (for example 5) | Exponential + jitter; honor retry-after | Persist attempt/next time |
| Telegram permanent send | 0 automatic retries after classification | None | Deactivate/quarantine |
| Database startup | Provider restart or small bounded startup retry | Capped | Exit non-zero after deadline |
| Token validation | User-initiated retry | None in request | Return 502/503 for Telegram outage, 400 only for invalid token |

## Graceful shutdown target

1. Mark readiness false.
2. Stop polling for new updates.
3. Stop scheduling a new scrape cycle.
4. Allow current DB transaction/send to reach a documented safe boundary within a deadline.
5. Close Telegram client, DB engine/pool, and health server.
6. Exit non-zero for fatal startup/runtime failure; zero only for intentional shutdown.
