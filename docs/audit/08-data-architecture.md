# Data Architecture

Audit date: 2026-08-31

## Persistent and temporary state

| Store | Owner | State | Durability |
| --- | --- | --- | --- |
| PostgreSQL | `teamitobot-grant-tracker` | Users, grants, notification intents/status, aggregate stats | Production durable state |
| `itobot-token-setup/data/config.json` | `itobot-token-setup` | Telegram bot token | Local durable plaintext file, Git-ignored |
| Flask session cookie | Browser/setup app | CSRF token | Ephemeral; invalidated when random process key changes |
| In-memory rate-limit dictionary | Setup process | Request timestamps by IP | Lost on restart; process-local |
| `last_scrape_time` global | Main process | Next-run timing | Lost/reset on restart |

The repositories do not share a database or file.

## PostgreSQL schema found

### `users`

| Column | Notes |
| --- | --- |
| `id` | Integer primary key |
| `chat_id` | BigInteger, unique, non-null, indexed |
| `username` | Nullable, mutable metadata |
| `is_active` | Boolean, default true |
| `is_subscribed` | Boolean, default false |
| `total_scrapes` | Non-null counter; increment method is unused |
| `created_at` | `DateTime` without explicit timezone flag; default supplies Istanbul-aware datetime |

### `grants`

| Column | Notes |
| --- | --- |
| `id` | Integer primary key |
| `text` | Nullable legacy title column; comment says migration is incomplete |
| `title` | Nullable current title |
| `start_date`, `end_date` | Nullable dates |
| `url` | Nullable URL |
| `detected_at` | Indexed `DateTime`, timezone semantics unspecified |

No uniqueness constraint encodes grant identity.

### `notifications`

| Column | Notes |
| --- | --- |
| `id` | Integer primary key |
| `user_id` | Non-null FK to users |
| `grant_id` | Non-null FK to grants |
| `sent_at` | Null means pending |
| unique `(user_id, grant_id)` | Prevents duplicate intent row for one DB grant ID |

ORM relationships cascade notification deletion from a user or grant. Database-level `ON DELETE CASCADE` is not specified, so behavior depends on ORM-managed deletion.

### `stats`

One row is assumed but not enforced. It stores scrape/notification/user counters, process start time, and last successful scrape time.

## Identity defect

The README and discovery comparison define grant identity as `(title, start_date, end_date)`. Persistence uses `(title OR legacy text)`.

Audit probe with an isolated SQLite database:

```text
first insert ID: 1
same title/different dates ID: 1
row count: 1
stored dates/URL: overwritten by second call
```

Consequences:

- recurring annual grants overwrite prior records;
- prior notifications still point to the updated row;
- the user/grant uniqueness constraint blocks notification creation for the “new” season;
- historical reporting becomes inaccurate.

The target natural key and migration require product confirmation about whitespace/case normalization and legacy rows before any schema change.

## Transaction boundaries

Every `DB` method creates and closes its own session. This produces small transactions but prevents application-level atomicity.

| Business operation | Current transactions | Risk |
| --- | --- | --- |
| Register user | Query + insert in one method | Multi-process unique race not handled |
| Subscribe | One transaction | Adequate |
| Unsubscribe | Delete pending + flag update in one transaction | Adequate |
| Discover grant for N users | 1 grant commit + N notification commits | Partial fan-out can become permanent |
| Send five grants | External send + up to 10 independent DB commits (mark + counter) | Duplicates, partial counters |
| Stats update | Read-modify-write | Lost updates with multiple processes |

Use one SQLAlchemy unit of work for grant plus subscriber notification intents. Keep external Telegram I/O outside the DB transaction.

## Migration state

Startup calls `Base.metadata.create_all`. This only creates missing tables and cannot safely alter existing columns, constraints, indexes, or data. The legacy `Grant.text` comment proves schema evolution has already occurred without a migration artifact.

Before future schema work:

1. capture the actual production schema and row counts;
2. introduce a migration tool such as Alembic because SQLAlchemy is already used;
3. add a baseline migration matching production, not merely current model declarations;
4. write forward/rollback compatibility notes;
5. rehearse against a sanitized database copy.

## Index and query review

- `users.chat_id` has both uniqueness and index support.
- `notifications(user_id, grant_id)` unique index supports duplicate checks.
- `grants.detected_at` is indexed but current code does not query it.
- Pending notification lookup filters `sent_at`, `users.is_active`, and `users.is_subscribed`; it has no targeted pending index.
- `get_all_grants` loads all historical grants each cycle.

At present, expected row counts are probably small. Do not add indexes speculatively. First record query duration and row counts. The grant natural-key constraint is a correctness requirement, not a performance optimization.

## Concurrency and scaling

The data design assumes one process. Multiple replicas can:

- create multiple stats rows;
- lose read-modify-write counter increments;
- race user insertion;
- independently scrape and fan out notifications;
- deliver the same pending notification before either commits `sent_at`.

The simplest current control is an explicit one-replica deployment. If independent scaling becomes real, use a PostgreSQL advisory lock/row-claim pattern before considering another datastore or broker.

## Time handling

SQLAlchemy columns use `DateTime` without `timezone=True`, while defaults pass timezone-aware Istanbul values. `bot.py` interprets a naive `started_at` as Istanbul but a naive `last_scrape_at` as UTC. Standardize on UTC-aware storage and convert only at the Telegram presentation boundary. This requires a migration/rehearsal, not an ad hoc model edit.

## Setup token file

Positive properties:

- fixed path, no path traversal;
- 4 KiB read limit;
- type/empty validation;
- `fsync` plus same-directory `os.replace` gives strong single-filesystem atomicity;
- invalid JSON is not deserialized unsafely.

Gaps:

- plaintext token;
- no restrictive file-mode/ACL setup;
- no file locking for concurrent writers;
- read errors/corruption are silently treated as absence;
- most importantly, no consumer in the main repository.

Production secrets should remain deployment-provider environment secrets. The file utility can be retained temporarily only as local operator tooling with an explicit export/deploy step, or retired.

