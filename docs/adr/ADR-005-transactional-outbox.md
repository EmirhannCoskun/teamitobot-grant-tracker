# ADR-005: PostgreSQL Transactional Outbox

- Status: Accepted
- Date: 2026-08-31

## Context

The current `notifications` table is a primitive outbox: a null `sent_at` means pending and `(user_id, grant_id)` is unique. However, grant creation and each notification insert commit separately (`bot.py:438-452`), so a crash can permanently skip recipients. Telegram send and per-row sent marks also have a crash gap (`bot.py:526-540`). All send failures are retried forever without classification, attempt count, backoff, lease, or terminal state.

## Decision

Evolve the PostgreSQL notification records into a transactional outbox.

Atomic write transaction:

- resolve/create occurrence and aliases;
- update occurrence metadata;
- snapshot active subscribed users;
- insert structured Telegram intents with `ON CONFLICT DO NOTHING`;
- commit once.

Unique intent constraint: `(user_id, grant_occurrence_id, channel)`.

The outbox stores a structured JSON payload snapshot, not rendered Markdown, so retries are deterministic while presentation stays in the Telegram adapter.

States: `pending`, `in_progress`, `retry_wait`, `sent`, `terminal_failure`, `cancelled`.

Claims use `FOR UPDATE SKIP LOCKED` in a short transaction, set a lease, then perform Telegram I/O after commit. Finalization is a second transaction. Stale leases return to retry and may duplicate after an ambiguous successful send; delivery is explicitly at-least-once.

Default retry policy:

- transient network/Telegram 5xx: exponential backoff with jitter, maximum 5 attempts;
- Telegram 429: honor `retry_after`, persist next attempt, no tight loop;
- bot-token authorization: stop dispatcher/readiness rather than fail every intent;
- blocked/missing chat: terminal and deactivate destination;
- invalid payload/Telegram 400: terminal and alert;
- terminal rows are retained and require an audited manual reset after correction.

Unsubscribe cancels `pending`/`retry_wait` rows. An already claimed send has a narrow race and may complete; no DB lock is held across Telegram I/O.

## Alternatives Considered

1. Keep null `sent_at` and retry every scrape cycle.
2. Send Telegram inside the database transaction.
3. Mark sent before Telegram call.
4. External RabbitMQ/Kafka/Redis queue.
5. Claim all rows without leases/row locking because one process is planned.
6. Claim exactly-once Telegram delivery.

## Why Selected

The system already has durable notification intents and needs only one PostgreSQL transaction/state machine to fix proven loss/retry gaps. PostgreSQL supplies required atomicity and safe claiming with no new service. A formal outbox makes failure behavior testable and visible while preserving one process.

## Consequences

- Notification schema gains state, payload, attempts, schedule, lease, redacted error, and timestamps.
- Dispatcher becomes an explicit application component.
- Rare duplicate Telegram messages remain possible and documented.
- Permanent failures stop retrying and remain inspectable.
- Pending queue age and terminal counts become useful readiness/operations signals.

## Risks

- Crash after Telegram acceptance and before finalize duplicates on lease recovery.
- Incorrect lease length can cause premature recovery or slow retries.
- Large payloads/queues can increase DB storage.
- Two migrations/dispatchers running during cutover can double-send.

Mitigation: single replica, versioned cutover, payload bounds, lease/crash integration tests, dispatcher ownership guard, retained terminal/history policy.

## Migration Implications

Backfill current notifications one-to-one: non-null `sent_at` -> `sent`; null and still eligible -> `pending`; null and unsubscribed/inactive -> `cancelled`. Populate structured payloads from the linked legacy grant. Add new columns nullable first, validate every row, then enforce state/payload constraints and due indexes. Do not delete the old `sent_at` compatibility column in the same release.

## Rejected Over-Engineering

- external broker/cache;
- separate outbox microservice;
- distributed transactions/two-phase commit;
- exactly-once marketing claims;
- per-message saga framework;
- independent dispatcher deployable before scale/ownership requires it.

