# ADR-004: Persistence and Migrations

- Status: Accepted
- Date: 2026-08-31

## Context

The current application uses SQLAlchemy and PostgreSQL but calls `Base.metadata.create_all` at startup. `Grant.text` is explicitly retained for an incomplete migration (`database.py:68-75`), yet no migration history exists. Transactions are hidden inside static DB methods, preventing atomic discovery/fan-out. Production schema/version details are not codified.

## Decision

Keep PostgreSQL, SQLAlchemy, and the synchronous driver during the architecture migration. Add Alembic as the idiomatic SQLAlchemy migration mechanism.

Migration policy:

1. capture and compare the actual production schema;
2. create a baseline revision that matches deployed reality;
3. use expand -> backfill -> validate -> cutover -> contract;
4. preserve existing row IDs and data during occurrence/outbox evolution;
5. add constraints only after backfill validation;
6. run migrations as a dedicated deployment step, never as `create_all` side effects;
7. keep old columns/tables through at least one compatible release before contraction;
8. store timestamps as `TIMESTAMPTZ` in UTC in the target schema.

Application transactions use an injected SQLAlchemy unit of work. One transaction records an occurrence, aliases, subscriber intents, and success statistics. Telegram I/O is outside the transaction.

## Alternatives Considered

1. Continue `create_all` and manual SQL.
2. Replace SQLAlchemy with raw SQL or another ORM.
3. Replace PostgreSQL with SQLite.
4. Create fresh target tables and discard/collapse legacy rows.
5. Adopt an external migration platform independent of SQLAlchemy.

## Why Selected

PostgreSQL already owns production state and provides the transactions, uniqueness, partial indexes, and row-locking required by the outbox. SQLAlchemy is adequate and familiar in the codebase. Alembic integrates with the existing metadata and supports explicit reviewed revisions. No ecosystem replacement provides measurable benefit.

## Consequences

- Deployment gains a migration phase and schema version.
- Engineers must review generated migration code and write data backfills explicitly.
- Rollback becomes compatibility-based; destructive down migrations are not assumed safe.
- PostgreSQL integration tests become mandatory for persistence acceptance.
- `create_all` will be removed from production startup after the baseline/cutover is verified.

## Risks

- Baseline drift between ORM declarations and actual production schema.
- Long locks during backfill/constraint creation.
- Application rollback after new writes may not understand new state.
- Timezone conversion can shift historical values if assumptions are wrong.

Mitigation: sanitized production snapshot, row-count/checksum assertions, small migrations, lock-time review, backup/restore rehearsal, expand/contract compatibility.

## Migration Implications

The first implementation work is schema inventory and an Alembic baseline, not target-table creation. Evolve current `grants` and `notifications` compatibly before optional later renames to `grant_occurrences` and `notification_outbox`. Legacy rows missing dates get unique legacy identity; sent/pending notification state is backfilled from `sent_at` and subscription state without deletion.

## Rejected Over-Engineering

- database-per-module;
- a second datastore for outbox state;
- event sourcing;
- automatic production autogeneration/application on process boot;
- zero-downtime multi-region migration machinery without such a deployment requirement;
- ORM/framework replacement.

