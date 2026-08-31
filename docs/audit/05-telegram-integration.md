# Telegram Integration Review

Audit date: 2026-08-31

## Architecture found

The production bot uses `python-telegram-bot` 21.7 with long polling. It does not use webhooks. Polling starts with all update types, a 30-second timeout, and `drop_pending_updates=True` (`bot.py:682-686`).

Long polling is appropriate for the current scale and one-replica deployment. Webhooks would add public ingress, TLS/routing, and authentication operations without a demonstrated benefit. The problem is not polling; it is the absence of explicit single-instance and delivery semantics.

The sibling `itobot-token-setup` repository is not a Telegram update integration. It calls Telegram's `getMe` endpoint to validate a credential and stores the credential in a file that the production bot does not read.

## Update routing

| Update type | Current behavior |
| --- | --- |
| `/start` | Register user and return keyboard |
| `/help` | Return help text |
| `/status` | Query global/user state and return status |
| Text buttons | Exact string matching routes to subscribe, unsubscribe, next-check, stats, status, help |
| Callback query | No handler |
| Non-text update | Allowed by polling but no application handler |
| Unknown text | Silently ignored |

Evidence: `bot.py:80-360`, `602-611`, `682-685`.

No application-level error handler is registered. Handler exceptions therefore rely on framework logging/default behavior and are not tied to an update ID in this code.

## Concurrency and responsiveness

`python-telegram-bot` is used asynchronously, but handlers call synchronous SQLAlchemy methods and the background task calls synchronous `requests`. The FIRST call's 15-second connect/read timeout setting or an unbounded database connection/query wait can block the event loop and delay update handling.

The code does not explicitly enable concurrent update processing, which keeps subscription state transitions simple. The main risk is blocking, not simultaneous handler races. `DB.add_or_get_user` is still not safe against multiple processes or future concurrent updates because query-then-insert does not handle a unique-key race (`database.py:185-208`).

## Duplicate update and idempotency analysis

The bot does not persist `Update.update_id` or an idempotency key.

| Operation | Duplicate processing effect |
| --- | --- |
| `/start` | Mostly idempotent; sends duplicate welcome response; concurrent insert can fail |
| Subscribe | State transition is idempotent; duplicate response changes to “already subscribed” |
| Unsubscribe | State transition is idempotent; first call deletes pending rows |
| Status/help/stats | Read-only but duplicate replies are possible |
| Background discovery | Notification unique constraint prevents duplicate user/grant rows, but grant natural key is wrong |
| Outbound notification | At-least-once with a send/mark gap; duplicates are possible |

`drop_pending_updates=True` favors avoiding old command replay by discarding every pending update at process start. That also means commands sent during downtime can be silently lost. This trade-off is not documented or tested.

## Outbound notification safety

### What works

- A database uniqueness constraint prevents two rows for the same `user_id`/`grant_id` (`database.py:101-107`).
- Failed sends leave `sent_at` null and are retried on a later scrape cycle (`bot.py:526-552`).
- Sends are sequential, limiting instantaneous concurrency.

### Failure gaps

1. `send_message` succeeds.
2. The process crashes, the DB is unavailable, or only part of a five-item batch is marked.
3. Remaining rows are still pending.
4. Restart sends them again.

Telegram `sendMessage` has no application-supplied idempotency key, so exactly-once delivery is not available. The correct target is explicit **at-least-once** delivery, with duplicates documented and minimized.

## Retry and rate-limit behavior

- Any send exception is caught generically and logged by `print`.
- There is no distinction between transient network error, `RetryAfter`, invalid Markdown, forbidden/blocked user, or invalid chat.
- There is no attempt count, next-attempt time, exponential backoff, jitter, dead-letter state, or maximum retry.
- Permanent failures retry every scrape interval forever.
- All subscribed users are processed with no explicit Telegram rate limiter or pacing beyond sequential awaits.

Desired minimal behavior:

- respect Telegram-provided retry-after values;
- bounded exponential backoff with jitter for transient network/5xx errors;
- mark blocked/deactivated chats inactive after a classified permanent Telegram error;
- retain and expose the last failure/attempt count;
- quarantine deterministic formatting failures instead of retrying forever;
- do not retry validation or permission failures as if they were network failures.

## Formatting and malformed data

Scraped titles and links are interpolated into legacy Markdown without escaping (`bot.py:491-532`). Parentheses, brackets, underscores, asterisks, and other control characters can make Telegram reject a message. Use a dedicated renderer with escaping (or escaped HTML mode) and unit-test boundary cases and Telegram message-length limits.

Batching is fixed at five grants, which limits typical message length but is not a proof against Telegram's length limit because title and URL lengths are independently large.

## Identity and authorization

- Chat identity uses `effective_chat.id`; username is metadata only (`bot.py:83-86`). This is correct because usernames are mutable and optional.
- The bot has no admin commands and is described as public subscription software. No allowlist is required for the current feature set.
- Aggregate status is available to any user. It exposes user count and operating statistics but no other user's direct identity.
- User/chat IDs are printed in logs and retained in PostgreSQL without a deletion/retention workflow.

If privileged commands are introduced later, authorization must be explicit and based on immutable Telegram user IDs, not usernames or chat-provided text.

## Startup, restart, and shutdown

Positive behavior:

- SIGTERM/SIGINT set an asyncio event.
- Polling is stopped, scraper task is cancelled, and the Telegram application is stopped (`bot.py:650-745`).
- Scraper HTTP has a 15-second connect/read timeout setting, though no strict wall-clock deadline.

Gaps:

- Pending user updates are dropped on every start.
- Synchronous DB work has no explicit timeout/cancellation.
- The health server thread is not shut down.
- Fatal exceptions are printed and swallowed, producing a normal process exit path.
- The application is initialized inside an `async with app` context and then explicitly initialized again, making lifecycle ownership unnecessarily ambiguous (`bot.py:671-676`).

## Dedicated recommendations

1. Keep polling and explicitly enforce/document one replica.
2. Add tests around duplicate update behavior, `drop_pending_updates`, restart, and graceful shutdown.
3. Extract a Telegram adapter and renderer from application use cases.
4. Define at-least-once outbound delivery and make retries classified, bounded, observable, and poison-message safe.
5. Move blocking scraper/DB work off the event loop or adopt async-compatible adapters only if measurements justify it.
6. Register an application error handler that includes a correlation/update ID without leaking message content or tokens.
