# Incremental Migration Roadmap

Audit date: 2026-08-31

Every stage must leave the bot deployable and preserve user-visible Telegram behavior unless a separately approved change is named. No migration is implemented by this audit.

## Stage 0 — Baseline Protection

**Goal:** make current behavior observable and safe to change.

**Affected files/modules:** current `bot.py`, `scraper.py`, `database.py`, `config.py`; both setup test modules; new `tests/`, CI/tool configuration, sanitized FIRST fixture.

**Work:**

- add parser tests from a dated, sanitized live FIRST fixture;
- add characterization tests for commands, messages, discovery, fan-out, pending delivery, and shutdown;
- add PostgreSQL integration test environment;
- record current at-least-once and `drop_pending_updates` behavior;
- keep and run all 83 setup tests; remove the shadowed duplicate test;
- configure structured baseline logging without changing application decisions;
- create a CI workflow for compile/lint/tests/advisory/secret scans;
- pin supported Python runtime and reproducible dependency resolution.

**Risk:** low; tests may expose undocumented production behavior and require product decisions.

**Prerequisites:** access to a sanitized schema/sample, test Telegram token or fake adapter, confirmation of current Render environment.

**Tests required:** new tests themselves plus unchanged setup suite; deployment import/start smoke.

**Rollback:** remove CI/test-only additions or revert logging configuration; no schema/state change.

**Expected architecture:** same runtime architecture, now with a trustworthy behavior baseline.

## Stage 1 — Critical Defects

**Goal:** correct data loss/security/reliability defects before structural movement.

**Affected files/modules:** `scraper.py`, `database.py`, `bot.py`, `config.py`, `requirements.txt`; new migrations; setup configuration contract/docs.

**Work in safe order:**

1. Initialize `apply_link` per card and isolate card parsing failures.
2. Escape Telegram output and test length/batching.
3. Make fatal startup errors exit non-zero; validate interval/port/timeouts.
4. Introduce migration tooling and baseline the actual production schema.
5. Reconcile legacy grant data, then align natural-key query and DB uniqueness with title/start/end after product confirmation.
6. Persist grant plus notification intents in one transaction.
7. Classify Telegram transient/rate-limit/permanent failures; add bounded retry state as an approved migration.
8. Upgrade advisory-bearing dependencies under tests.
9. Adopt one secret contract; mark setup tool local-only and stop claiming its file configures production.

**Risk:** medium/high because identity and delivery state touch production data.

**Prerequisites:** Stage 0, database backup, actual schema inventory, migration rehearsal, agreed grant normalization and delivery semantics.

**Tests required:** P0 identity/transaction/parser/renderer/retry tests, production-like PostgreSQL migration tests, rollback/read-compatibility tests, live-page smoke outside blocking CI.

**Rollback:** feature flags or backward-compatible code path for new retry fields; expand-first schema migrations; restore DB backup only under rehearsed incident procedure. Never blindly downgrade destructive data changes.

**Expected architecture:** current modules remain, but correctness invariants and operational contracts are reliable.

## Stage 2 — Boundary Cleanup

**Goal:** separate application decisions from Telegram, SQLAlchemy, FIRST HTML, and bootstrap code.

**Affected files/modules:** split `bot.py`, `database.py`, `scraper.py`, and `config.py` incrementally into the target `src/itobot_grants` modules.

**Work:**

- introduce typed `GrantCandidate`, `GrantIdentity`, delivery outcome, and result enums;
- extract pure FIRST parser, retaining current HTTP adapter;
- extract `check_grants` and `deliver_notifications` use cases behind minimal ports;
- extract Telegram renderer and thin handlers;
- replace static `DB` calls with an injected transaction-oriented unit of work;
- move process construction, signals, health, and schedule into bootstrap/infrastructure;
- remove import-time settings validation in favor of explicit bootstrap construction.

**Risk:** medium; imports/lifecycle/message formatting can regress.

**Prerequisites:** Stage 0 tests and Stage 1 correctness fixes.

**Tests required:** existing characterization tests must pass at each extraction; add pure application unit tests and adapter contract tests.

**Rollback:** make each extraction a small commit; retain delegating compatibility functions until all callers move; revert one slice without reverting data migrations.

**Expected architecture:** lightweight ports-and-adapters modular monolith, still one repository/process/database.

## Stage 3 — Repository Restructure

**Goal:** execute ADR-001 without changing production runtime behavior.

**Affected repositories/modules:** both repositories, consolidated dependency/test/docs configuration, optional `tools/token_setup`.

**Work:**

- tag both pre-consolidation commits;
- confirm setup UI usage and choose retain-temporarily or retire path;
- if retained, move it with history where practical under local-only tools and define a real secret handoff;
- combine tests and dependency configuration while keeping tool dependencies out of the bot runtime artifact when possible;
- update canonical README/repository links;
- deploy the same one bot artifact from the consolidated repo;
- archive the old setup repository read-only after verification.

**Risk:** medium operational/repository risk; low runtime risk if behavior is unchanged.

**Prerequisites:** ADR accepted, Stages 0-2, owner agreement, access to repository settings/deployment configuration.

**Tests required:** all bot/setup tests in one pipeline; artifact-content assertion excludes tool server from production; configuration contract test; deployment smoke.

**Rollback:** keep the old setup repo/tag and old deployment source available until cutover acceptance; revert canonical repo/deployment pointer.

**Expected architecture:** one canonical repository, one deployable bot, optional non-deployed local tool.

## Stage 4 — Test Expansion

**Goal:** cover remaining risk and reduce over-mocked tests.

**Affected files/modules:** `tests/unit`, `tests/integration`, `tests/contract`, fixtures, setup browser tests if tool remains.

**Work:**

- concurrency/claim tests for pending notifications;
- Telegram duplicate update and restart scenarios;
- PostgreSQL timezone/constraint/index behavior;
- configuration matrix and lifecycle tests;
- browser E2E for retained setup tool;
- contract tests for FIRST parser fixtures and Telegram payload rendering;
- mutation/property tests only for parsers/identity if they add demonstrated value.

**Risk:** low; test runtime/flakiness can grow.

**Prerequisites:** stable Stage 2 boundaries.

**Tests required:** CI itself must demonstrate deterministic execution and isolate live-network smoke from merge-blocking tests.

**Rollback:** remove flaky/nonessential cases; never weaken P0 gates to improve speed.

**Expected architecture:** critical behavior protected at the cheapest appropriate test level.

## Stage 5 — Operational Hardening

**Goal:** make production failure visible, bounded, and recoverable.

**Affected files/modules:** logging, health, scheduler, config, deployment manifest, CI/CD, migration/release docs.

**Work:**

- liveness/readiness and scrape-freshness checks;
- structured redacted logs with cycle/update/notification correlation;
- minimal counters/alerts for stale scrape and pending age;
- explicit DB/connect/send timeouts and pool health;
- shutdown deadlines and resource closure;
- one-replica deployment assertion/documentation;
- immutable release/version metadata, migration phase, rollback runbook, backup/restore rehearsal;
- provider secret documentation and rotation runbook.

**Risk:** medium; incorrect readiness can cause restart loops.

**Prerequisites:** stable lifecycle boundaries and provider configuration access.

**Tests required:** readiness transition, stale scrape, DB outage, Telegram outage, SIGTERM, non-zero fatal exit, deploy/rollback smoke.

**Rollback:** keep liveness independent; relax readiness threshold/config without disabling diagnosis; revert deployment manifest to last tagged release.

**Expected architecture:** same simple runtime with production-grade diagnosis and recovery.

## Stage 6 — Cleanup

**Goal:** remove obsolete compatibility surface and documentation debt.

**Affected files/modules:** legacy `Grant.text`, unused DB methods/fields, duplicate/old docs, optional token tool, obsolete dependencies.

**Work:**

- remove dead DB APIs only after call/telemetry confirmation;
- complete and later contract legacy-column migrations;
- remove `pytz` after UTC/`zoneinfo` tests if chosen;
- split overly large test files by behavior;
- remove stale README tree/files and extra code fence;
- retire setup tool and Flask dependency if no longer used;
- document architecture decisions and supported operations.

**Risk:** low/medium; cleanup can remove hidden operator behavior.

**Prerequisites:** at least one stable release on target architecture, usage confirmation, migration compatibility window elapsed.

**Tests required:** full suite, migration contract cleanup test, deployment smoke.

**Rollback:** retain prior tagged release and expand/contract migration discipline; restore optional tool from archived tag if a user dependency is discovered.

**Expected architecture:** one small, documented modular application with no misleading legacy surfaces.

## Stage gates

Do not begin repository movement merely because the ADR is accepted. The gates are:

```text
Baseline tests
  -> critical correctness/data fixes
  -> application/adapter boundaries
  -> repository consolidation
  -> broader tests and operations
  -> cleanup
```

The application must be deployable after every arrow.

