# Team Implementation Plan

Architecture freeze date: 2026-08-31

This plan contains 32 focused work packages. Each package should normally be one pull request. No developer names are assigned; owner capability identifies the skill profile the software captain should select.

## Planning rules

- Protected `main`; short-lived branch per package; mandatory review and green required checks.
- Blocking contracts are merged before parallel dependants start.
- Only one active Alembic-head/schema-contract PR at a time unless maintainers explicitly coordinate a merge revision.
- Production remains deployable after every merged package.
- Public Telegram behavior remains unchanged unless the package acceptance criteria explicitly approve a correction.
- Schema/data packages require a backup/rehearsal plan before production execution.

## Canonical work tracking contract

The Software Captain approved this immutable tracking relationship on
2026-08-31 under the [Architecture Freeze](../architecture/architecture-freeze.md).
`GRANT-XX` is the canonical GitHub-facing task identifier; the source package
ID remains the canonical technical work-package identifier in this plan and the
dependency graph. GitHub issue numbers are transport metadata and are not part
of the identity contract, even when they happen to match a GRANT number.

An identifier must not be reused or remapped. A mapping correction requires
Software Captain approval and a coordinated update to this table, the related
GitHub issue, and the dependency references.

| GitHub task ID | Source work-package ID |
| --- | --- |
| GRANT-01 | FZ-001 |
| GRANT-02 | DV-001 |
| GRANT-03 | DV-002 |
| GRANT-04 | BL-001 |
| GRANT-05 | BL-002 |
| GRANT-06 | BL-003 |
| GRANT-07 | BL-004 |
| GRANT-08 | PK-001 |
| GRANT-09 | MG-001 |
| GRANT-10 | ID-001 |
| GRANT-11 | CF-001 |
| GRANT-12 | TG-001 |
| GRANT-13 | PV-001 |
| GRANT-14 | ID-002 |
| GRANT-15 | ID-003 |
| GRANT-16 | OB-001 |
| GRANT-17 | OB-002 |
| GRANT-18 | OB-003 |
| GRANT-19 | OB-004 |
| GRANT-20 | OB-005 |
| GRANT-21 | AP-001 |
| GRANT-22 | AP-002 |
| GRANT-23 | TG-002 |
| GRANT-24 | EX-001 |
| GRANT-25 | OP-001 |
| GRANT-26 | CI-001 |
| GRANT-27 | TS-001 |
| GRANT-28 | DV-003 |
| GRANT-29 | RS-001 |
| GRANT-30 | ST-001 |
| GRANT-31 | ST-002 |
| GRANT-32 | CL-001 |

## Package summary

| Group | Packages | Parallelization intent |
| --- | --- | --- |
| G0 — Freeze | FZ-001 | Blocking architecture contract |
| G1 — Tooling gate | DV-001 | Establish fast PR gate first |
| G2 — Baseline | DV-002, BL-001..004, PK-001 | Parallel after DV-001; BL-003 follows DV-002 |
| G3 — Contracts/foundations | MG-001, ID-001, CF-001, TG-001 | Parallel by area; MG waits for PostgreSQL baseline tests |
| G4 — Provider/schema | PV-001, ID-002, ID-003, OB-001 | ID-002 then OB-001 serialized on migration head; provider work parallel |
| G5 — Outbox/application | OB-002..004, AP-001..002, TG-002 | Parallel where dependencies/files do not overlap |
| G6 — Assembly/reliability | OB-005, EX-001, OP-001 | Integration gate |
| G7 — Delivery/tooling | CI-001, TS-001, DV-003 | Parallel after contracts/tests exist |
| G8 — Consolidation/rehearsal | RS-001, ST-001 | Can prepare in parallel; staging waits for both |
| G9 — Validation | ST-002 | Blocking release validation |
| G10 — Contract cleanup | CL-001 | After stable observation window |

## Work packages

### FZ-001 — Approve and enforce architecture freeze

- **Goal:** approve the freeze/ADRs and establish deviation/change-control rules.
- **Dependencies:** none.
- **Affected architecture area:** all contracts.
- **Likely files/modules:** `docs/architecture/architecture-freeze.md`, ADR-002..009, planning docs.
- **Acceptance criteria:** software captain records approval; unresolved deviations have follow-up ADRs; package IDs become canonical tracking labels.
- **Required tests:** documentation link/section/Mermaid validation only.
- **Risk:** Low.
- **Estimated complexity:** S.
- **Parallelization group:** G0; blocking contract work.
- **Recommended owner capability:** Architecture/Domain.

### DV-001 — Establish supported runtime and fast CI gate

- **Goal:** pin the supported Python minor and add the first GitHub Actions job for install, compile, Ruff, and fast pytest.
- **Dependencies:** FZ-001.
- **Affected architecture area:** delivery/DevEx.
- **Likely files/modules:** `.github/workflows/ci.yml`, tool config, runtime declaration, minimal test config.
- **Acceptance criteria:** clean checkout runs one documented command locally and CI blocks compile/lint/unit failures; no production dependency upgrade bundled.
- **Required tests:** CI self-run; import/compile smoke; one intentional failure demonstrated in branch history or workflow test.
- **Risk:** Low.
- **Estimated complexity:** M.
- **Parallelization group:** G1; blocks all implementation PR gates.
- **Recommended owner capability:** QA/DevEx.

### DV-002 — Add isolated PostgreSQL test harness

- **Goal:** provide real PostgreSQL locally and in CI with deterministic database isolation.
- **Dependencies:** DV-001.
- **Affected architecture area:** testing/persistence.
- **Likely files/modules:** test fixtures, CI service container, optional test-only Compose file, test documentation.
- **Acceptance criteria:** tests create/clean isolated schemas/databases; no production DB can be selected accidentally; production major version is recorded and CI aligned.
- **Required tests:** connectivity, isolation between tests, teardown after failure, secret-redaction check.
- **Risk:** Medium.
- **Estimated complexity:** M.
- **Parallelization group:** G2; parallel with non-DB baseline packages.
- **Recommended owner capability:** QA/DevEx.

### BL-001 — Characterize FIRST collection and parsing

- **Goal:** lock current valid behavior and known malformed-card behavior before extraction.
- **Dependencies:** DV-001.
- **Affected architecture area:** provider adapter/testing.
- **Likely files/modules:** `scraper.py`, `tests/fixtures/first/`, parser tests.
- **Acceptance criteria:** dated sanitized fixture covers active/inactive, FRC/non-FRC, relative URL, duplicate, missing details, malformed dates, empty valid page, network failure distinction.
- **Required tests:** pure/mocked HTTP parser regression tests; live page only as optional scheduled smoke.
- **Risk:** Low.
- **Estimated complexity:** M.
- **Parallelization group:** G2.
- **Recommended owner capability:** QA/DevEx.

### BL-002 — Characterize Telegram behavior and rendering

- **Goal:** preserve commands, button routing, Turkish responses, batching, polling policy, and current retry/duplicate behavior.
- **Dependencies:** DV-001.
- **Affected architecture area:** Telegram inbound/outbound adapters.
- **Likely files/modules:** `bot.py`, Telegram update/bot fakes, response snapshots/assertions.
- **Acceptance criteria:** `/start`, subscribe/unsubscribe, status/stats/help, unknown text, duplicate commands, Markdown edge strings, send failure, and `drop_pending_updates` behavior are explicit.
- **Required tests:** framework-boundary unit tests with no live bot token.
- **Risk:** Medium.
- **Estimated complexity:** M.
- **Parallelization group:** G2.
- **Recommended owner capability:** Integration/Telegram.

### BL-003 — Characterize legacy persistence and fan-out

- **Goal:** capture actual user/grant/notification/stats behavior and reproduce known identity/transaction defects on PostgreSQL.
- **Dependencies:** DV-002.
- **Affected architecture area:** persistence/testing.
- **Likely files/modules:** `database.py`, PostgreSQL fixtures, legacy schema/data fixture.
- **Acceptance criteria:** tests cover unique chat/user-grant constraints, title overwrite probe, subscription cancellation, pending queries, sent marking, stats, and partial fan-out failure.
- **Required tests:** real PostgreSQL integration only for acceptance; no SQLite substitution.
- **Risk:** Medium.
- **Estimated complexity:** L.
- **Parallelization group:** G2; prerequisite for migration baseline.
- **Recommended owner capability:** Backend/Persistence.

### BL-004 — Characterize configuration and lifecycle

- **Goal:** freeze startup, invalid configuration, health, signal, exit-code, and shutdown behavior before bootstrap changes.
- **Dependencies:** DV-001.
- **Affected architecture area:** bootstrap/configuration.
- **Likely files/modules:** `config.py`, `bot.py:38-73`, `bot.py:579-764`, subprocess test helpers.
- **Acceptance criteria:** current deficiencies are captured; target assertions are marked expected-failure or introduced only with approved fixes; secrets never appear in output.
- **Required tests:** subprocess/import tests, invalid interval/port, missing secrets, DB failure, SIGTERM/KeyboardInterrupt, health response.
- **Risk:** Medium.
- **Estimated complexity:** M.
- **Parallelization group:** G2.
- **Recommended owner capability:** QA/DevEx.

### PK-001 — Introduce consolidated project metadata and dependency groups

- **Goal:** declare supported Python, runtime/test/dev groups, and reproducible install/build metadata without opportunistic framework upgrades.
- **Dependencies:** DV-001.
- **Affected architecture area:** packaging/DevEx.
- **Likely files/modules:** `pyproject.toml`, lock/resolution artifact, compatibility `requirements.txt`, build/import entry metadata.
- **Acceptance criteria:** runtime install excludes pytest/tool-only dependencies; existing Procfile command still works or has a compatibility entry; builds are reproducible.
- **Required tests:** clean runtime install, dev install, package build/install/import smoke.
- **Risk:** Medium.
- **Estimated complexity:** M.
- **Parallelization group:** G2; coordinate with DV-001 workflow files.
- **Recommended owner capability:** QA/DevEx.

### MG-001 — Inventory production schema and add Alembic baseline

- **Goal:** establish a reviewed schema version matching deployed reality before target migrations.
- **Dependencies:** BL-003, DV-002.
- **Affected architecture area:** persistence/migrations.
- **Likely files/modules:** Alembic config/environment, baseline revision, sanitized schema dump/fixture, deployment docs.
- **Acceptance criteria:** baseline matches production inventory; existing DB can be stamped only after verified match; empty DB upgrade recreates baseline; startup no longer relies on future `create_all` changes.
- **Required tests:** empty upgrade, current legacy fixture upgrade/stamp, ORM-schema comparison, downgrade policy documentation.
- **Risk:** High.
- **Estimated complexity:** L.
- **Parallelization group:** G3; blocking schema contract.
- **Recommended owner capability:** Backend/Persistence.

### ID-001 — Implement versioned occurrence identity domain rules

- **Goal:** add pure candidate normalization, alias generation, date overlap, and resolution decision logic.
- **Dependencies:** BL-001, FZ-001.
- **Affected architecture area:** domain identity.
- **Likely files/modules:** new `domain/grants.py`, `domain/identity.py`, unit tests/fixtures.
- **Acceptance criteria:** title-only/positional ID rejected; exact replay idempotent; non-overlap recurrence distinct; unique continuity update supported; ambiguity never returns silent merge.
- **Required tests:** table-driven unit tests for Unicode/whitespace/program/date/URL normalization, alias versioning, current BAE shared-URL case, annual recurrence, ambiguous matches.
- **Risk:** High.
- **Estimated complexity:** M.
- **Parallelization group:** G3; blocking domain contract.
- **Recommended owner capability:** Architecture/Domain.

### CF-001 — Add typed canonical configuration contract

- **Goal:** construct immutable validated settings in bootstrap while preserving current callers through a compatibility layer.
- **Dependencies:** BL-004.
- **Affected architecture area:** configuration/bootstrap.
- **Likely files/modules:** `config.py`, new infrastructure config module, `.env.example`, `.gitignore`, startup tests.
- **Acceptance criteria:** one precedence/source contract; positive/range validation; direct settings construction in tests; redacted errors; local dotenv only; no domain/application environment reads.
- **Required tests:** field/type/range matrix, missing secret, redaction, `.env` precedence, import without live secrets for inner modules.
- **Risk:** Medium.
- **Estimated complexity:** M.
- **Parallelization group:** G3.
- **Recommended owner capability:** Architecture/Domain.

### TG-001 — Extract and harden Telegram renderer

- **Goal:** centralize escaped, length-safe Telegram messages without changing approved wording/commands.
- **Dependencies:** BL-002.
- **Affected architecture area:** Telegram outbound adapter.
- **Likely files/modules:** `bot.py` formatting sections, new `adapters/telegram/renderer.py`.
- **Acceptance criteria:** titles/URLs/control characters cannot produce invalid payload; batch respects Telegram limit; renderer takes structured payload/value types only.
- **Required tests:** current message regression, Markdown/HTML escaping cases, maximum title/URL/batch, empty optional URL/date.
- **Risk:** Medium.
- **Estimated complexity:** M.
- **Parallelization group:** G3.
- **Recommended owner capability:** Integration/Telegram.

### PV-001 — Extract and harden FIRST provider adapter

- **Goal:** split synchronous fetch from pure parser, isolate malformed cards, and return typed `GrantCandidate` results.
- **Dependencies:** BL-001, ID-001.
- **Affected architecture area:** provider outbound adapter.
- **Likely files/modules:** `scraper.py`, new `adapters/first_web/client.py`, `parser.py`.
- **Acceptance criteria:** one bad card does not abort valid cards; success-empty differs from failure; timeouts/errors classified; parser has no config/global/network dependency.
- **Required tests:** BL-001 suite plus typed contract/error/latency-field tests.
- **Risk:** Medium.
- **Estimated complexity:** M.
- **Parallelization group:** G4; parallel with serialized schema work.
- **Recommended owner capability:** Backend/Persistence.

### ID-002 — Add occurrence identity schema and lossless backfill

- **Goal:** expand current grant storage with source/source-key/version/aliases and backfill every legacy row one-to-one.
- **Dependencies:** MG-001, ID-001.
- **Affected architecture area:** persistence/migrations/identity.
- **Likely files/modules:** one Alembic revision, ORM models, migration verification fixtures.
- **Acceptance criteria:** IDs/counts preserved; no automated merges; missing fields get unique legacy aliases; unique provider alias constraint added only after validation; representative checksums pass.
- **Required tests:** empty/legacy upgrade, duplicate-title rows preserved, missing title/date cases, uniqueness/FK checks, rollback/read compatibility.
- **Risk:** High.
- **Estimated complexity:** L.
- **Parallelization group:** G4; serialized migration-head work.
- **Recommended owner capability:** Backend/Persistence.

### ID-003 — Implement occurrence repository and alias upsert

- **Goal:** persist ID-001 decisions safely against ID-002 schema.
- **Dependencies:** ID-001, ID-002.
- **Affected architecture area:** persistence adapter/domain integration.
- **Likely files/modules:** persistence models/repository/unit-of-work, compatibility DB facade.
- **Acceptance criteria:** concurrent exact candidates converge; alias conflict rolls back and becomes a classified conflict; metadata update preserves occurrence ID; no title-only query remains in active path.
- **Required tests:** real PostgreSQL exact replay, recurrence, concurrent inserts, alias conflict, metadata update, legacy lookup.
- **Risk:** High.
- **Estimated complexity:** L.
- **Parallelization group:** G4 after ID-002; can overlap OB-001 review only if migration files are serialized.
- **Recommended owner capability:** Backend/Persistence.

### OB-001 — Add outbox schema and legacy notification backfill

- **Goal:** expand existing notification rows with payload, state, attempts, due/lease/error fields and approved indexes.
- **Dependencies:** ID-002, MG-001.
- **Affected architecture area:** persistence/migrations/outbox.
- **Likely files/modules:** one Alembic revision, ORM outbox model, legacy fixture assertions.
- **Acceptance criteria:** IDs/counts preserved; sent/null state maps correctly; unsubscribed pending rows cancel; unique user/occurrence/channel enforced; partial due/lease indexes verified.
- **Required tests:** empty/legacy migration, all state backfills, payload generation, constraint/index inspection, compatibility with current sent-at reads.
- **Risk:** High.
- **Estimated complexity:** L.
- **Parallelization group:** G4; starts only after ID-002 merge on the Alembic head.
- **Recommended owner capability:** Backend/Persistence.

### OB-002 — Implement outbox claim, lease, finalize, and recovery repository

- **Goal:** provide concurrency-safe due claiming and state transitions without Telegram code.
- **Dependencies:** OB-001.
- **Affected architecture area:** persistence adapter/outbox.
- **Likely files/modules:** `adapters/persistence/outbox.py`, unit of work, domain delivery values.
- **Acceptance criteria:** bounded `SKIP LOCKED` claim; state-consistent finalize/retry/terminal/cancel; stale lease recovery; no network call under DB transaction.
- **Required tests:** real PostgreSQL two-session claims, lease expiry, concurrent finalization, invalid transitions, unsubscribe cancellation.
- **Risk:** High.
- **Estimated complexity:** L.
- **Parallelization group:** G5.
- **Recommended owner capability:** Backend/Persistence.

### OB-003 — Implement atomic occurrence and recipient-intent transaction

- **Goal:** replace separate grant/per-user commits with one application unit of work.
- **Dependencies:** ID-003, OB-001, BL-003.
- **Affected architecture area:** application/persistence.
- **Likely files/modules:** application collection persistence service, persistence unit of work, compatibility `DB` calls.
- **Acceptance criteria:** occurrence/aliases/intents all commit or roll back; duplicates use `ON CONFLICT DO NOTHING`; recipient snapshot preserves current subscribe semantics; statistics update policy explicit.
- **Required tests:** injected failure at every step, concurrent collection, zero/many subscribers, duplicate run, unsubscribe race policy.
- **Risk:** High.
- **Estimated complexity:** L.
- **Parallelization group:** G5; parallel with OB-002 if persistence files are partitioned/reviewed carefully.
- **Recommended owner capability:** Backend/Persistence.

### OB-004 — Implement Telegram outbox dispatcher and retry classification

- **Goal:** deliver claimed structured intents with frozen state/retry semantics.
- **Dependencies:** OB-002, TG-001, BL-002.
- **Affected architecture area:** application/Telegram outbound adapter.
- **Likely files/modules:** `application/dispatch_notifications.py`, Telegram notifier, error classifier.
- **Acceptance criteria:** send outside DB transaction; 429 honors retry-after; transient bounded to configured attempts; global auth pauses readiness; blocked/payload failures terminal; no token/body leakage.
- **Required tests:** fake Telegram outcomes for every class, attempt/backoff/jitter clock, batch fairness, accepted receipt, ambiguous finalize failure.
- **Risk:** High.
- **Estimated complexity:** L.
- **Parallelization group:** G5.
- **Recommended owner capability:** Integration/Telegram.

### OB-005 — Verify outbox crash, concurrency, and outage recovery

- **Goal:** prove the integrated delivery model under the failure modes that motivated it.
- **Dependencies:** OB-002, OB-003, OB-004.
- **Affected architecture area:** reliability/testing.
- **Likely files/modules:** PostgreSQL integration tests, dispatcher harness, deterministic clock/fake Telegram.
- **Acceptance criteria:** no lost intent on collection crash; two dispatchers do not claim same row; stale lease recovers; send/finalize ambiguity may duplicate but remains durable/visible; terminal rows stop.
- **Required tests:** process/transaction fault injection and concurrent PostgreSQL sessions.
- **Risk:** High.
- **Estimated complexity:** L.
- **Parallelization group:** G6; blocking reliability gate.
- **Recommended owner capability:** QA/DevEx.

### AP-001 — Extract collect-grants application use case

- **Goal:** move collection decisions out of `bot.py` behind grant-source and unit-of-work ports.
- **Dependencies:** PV-001, ID-003, OB-003.
- **Affected architecture area:** application/domain.
- **Likely files/modules:** `bot.py:367-458`, new `application/collect_grants.py`, ports.
- **Acceptance criteria:** use case has no Telegram/requests/BeautifulSoup/SQLAlchemy/environment imports; valid-empty/failure/partial outcomes explicit; current cadence/active-FRC behavior preserved.
- **Required tests:** fake source/UoW/clock cases for new, repeated, recurring, ambiguous, empty, failure, rollback.
- **Risk:** Medium.
- **Estimated complexity:** M.
- **Parallelization group:** G5/G6 after persistence contract.
- **Recommended owner capability:** Architecture/Domain.

### AP-002 — Extract subscriber and status application use cases

- **Goal:** move registration/subscription/status decisions out of handlers/static DB methods.
- **Dependencies:** BL-002, BL-003, OB-001.
- **Affected architecture area:** application/Telegram inbound boundary.
- **Likely files/modules:** `bot.py:80-336`, user DB methods, new `application/subscriptions.py`.
- **Acceptance criteria:** state results are presentation-neutral; duplicate commands idempotent; unsubscribe cancels due outbox rows transactionally; status data matches current behavior.
- **Required tests:** pure use-case tests plus PostgreSQL subscribe/unsubscribe/cancellation integration.
- **Risk:** Medium.
- **Estimated complexity:** M.
- **Parallelization group:** G5; parallel with OB/PV work after schema contract.
- **Recommended owner capability:** Architecture/Domain.

### TG-002 — Extract thin Telegram inbound handlers

- **Goal:** make Telegram handlers map updates to AP-002/use-case inputs and TG-001 renderer outputs only.
- **Dependencies:** AP-002, TG-001.
- **Affected architecture area:** Telegram inbound adapter.
- **Likely files/modules:** `bot.py:80-360`, `adapters/telegram/handlers.py`.
- **Acceptance criteria:** no SQL/config/scraper imports; effective immutable IDs used; error handler includes update correlation; public commands/buttons unchanged.
- **Required tests:** BL-002 regression, malformed/non-message update, duplicate update, application failure mapping.
- **Risk:** Medium.
- **Estimated complexity:** M.
- **Parallelization group:** G5.
- **Recommended owner capability:** Integration/Telegram.

### EX-001 — Assemble one-process composition root and lifecycle

- **Goal:** compose polling, schedule, collection, dispatcher, health, settings, and DB with clear startup/shutdown ownership.
- **Dependencies:** CF-001, AP-001, TG-002, OB-004.
- **Affected architecture area:** bootstrap/execution.
- **Likely files/modules:** `bot.py:579-764`, new bootstrap/scheduling modules, Procfile compatibility.
- **Acceptance criteria:** one initialization path; one replica documented/asserted; blocking work does not stall Telegram loop; readiness only after components start; non-zero fatal exit; bounded shutdown closes resources.
- **Required tests:** lifecycle/subprocess, task failure, DB/Telegram unavailable, SIGTERM during idle/claim/provider call, readiness transitions.
- **Risk:** High.
- **Estimated complexity:** L.
- **Parallelization group:** G6; assembly gate.
- **Recommended owner capability:** Architecture/Domain.

### OP-001 — Add structured logging and truthful health/readiness

- **Goal:** make collection/outbox/Telegram failures diagnosable without leaking secrets or raw chat IDs.
- **Dependencies:** EX-001, OB-005.
- **Affected architecture area:** operations/observability.
- **Likely files/modules:** logging/health infrastructure, application event fields, deployment health config.
- **Acceptance criteria:** stable events/correlation IDs; last-success and oldest-pending signals; liveness/readiness distinction; shutdown unready; no token/DB URL/message body/raw chat ID.
- **Required tests:** log redaction/schema, stale scrape, dead dispatcher/polling, DB readiness, unsupported health methods, shutdown transition.
- **Risk:** Medium.
- **Estimated complexity:** M.
- **Parallelization group:** G6/G7.
- **Recommended owner capability:** QA/DevEx.

### CI-001 — Complete CI migration, package, PostgreSQL, and security gates

- **Goal:** turn all frozen acceptance suites into required protected-main checks.
- **Dependencies:** DV-001, DV-002, MG-001, OB-001, PK-001.
- **Affected architecture area:** delivery/CI.
- **Likely files/modules:** GitHub Actions workflows, test markers, build/advisory/secret scan config.
- **Acceptance criteria:** fast and PostgreSQL jobs; Alembic empty/legacy upgrades and drift check; package install/import; pip-audit and secret scan; documented required check names; no production Docker build unless approved.
- **Required tests:** workflow runs on PR/push, cached and uncached install, intentional migration drift failure in validation branch.
- **Risk:** Medium.
- **Estimated complexity:** M.
- **Parallelization group:** G7.
- **Recommended owner capability:** QA/DevEx.

### TS-001 — Replace token setup with canonical docs and optional validator CLI

- **Goal:** preserve useful token validation/non-disclosure without Flask or plaintext file storage.
- **Dependencies:** CF-001, FZ-001.
- **Affected architecture area:** tool/configuration/repository boundary.
- **Likely files/modules:** canonical README/operator docs, optional `tools/token_setup` CLI, selected setup tests.
- **Acceptance criteria:** docs configure the actual environment/provider secret; optional CLI does not persist/log/echo token; `getMe` outage differs from invalid token; Flask tool marked deprecated with cutover notice.
- **Required tests:** format/API outcome/non-disclosure tests ported from setup; subprocess/stdout/stderr redaction; no file created.
- **Risk:** Medium.
- **Estimated complexity:** M.
- **Parallelization group:** G7; parallel with CI/ops.
- **Recommended owner capability:** Integration/Telegram.

### DV-003 — Upgrade advisory-bearing dependencies under regression gates

- **Goal:** remove known main-manifest advisories without mixing architecture/framework changes.
- **Dependencies:** BL-001, BL-002, BL-003, CI-001.
- **Affected architecture area:** dependency security.
- **Likely files/modules:** dependency manifest/lock only, compatibility fixes if strictly required.
- **Acceptance criteria:** pip-audit clears targeted advisories or documents accepted non-exploitable exception; all suites pass; no unrelated major upgrade.
- **Required tests:** full CI, live provider smoke in staging, startup/import.
- **Risk:** Medium.
- **Estimated complexity:** M.
- **Parallelization group:** G7.
- **Recommended owner capability:** QA/DevEx.

### RS-001 — Consolidate repositories and prepare obsolete setup app for archive

- **Goal:** execute the canonical repository consolidation from ADR-001 after the production boundaries and replacement token workflow are ready, without archiving or deleting the old repository in this package.
- **Dependencies:** TS-001, PK-001, EX-001, CI-001.
- **Affected architecture area:** repository model/tooling.
- **Likely files/modules:** both Git histories/tags, canonical repo docs/tests, repository/deployment settings.
- **Acceptance criteria:** the canonical repository contains all required production behavior; relevant validation tests are retained; the production artifact excludes Flask/UI/file storage; the old setup repository is not a production runtime dependency; required functionality is moved or documented; deployment source changes are reversible; archive readiness is documented; actual archive/delete requires separate Software Captain approval.
- **Required tests:** unified full CI, artifact-content check, setup workflow acceptance, deployment smoke from canonical repo.
- **Risk:** High.
- **Estimated complexity:** M.
- **Parallelization group:** G8; coordination task, not parallel file movement or an archive/delete action.
- **Recommended owner capability:** QA/DevEx.

### ST-001 — Rehearse legacy-to-head migration and restore

- **Goal:** prove data preservation and operational timing on a sanitized production-like snapshot.
- **Dependencies:** ID-002, OB-001, OB-003, MG-001.
- **Affected architecture area:** persistence/release safety.
- **Likely files/modules:** migration runbook, validation queries/scripts, sanitized snapshot, backup/restore procedure.
- **Acceptance criteria:** row IDs/counts/checksums preserved; no grant merge; notification states accounted; constraints valid; lock/runtime measured; restore rehearsed; go/no-go thresholds documented.
- **Required tests:** automated migration assertions plus manual timed rehearsal evidence.
- **Risk:** High.
- **Estimated complexity:** L.
- **Parallelization group:** G8; can prepare while repository consolidation is reviewed.
- **Recommended owner capability:** Backend/Persistence.

### ST-002 — Perform staging end-to-end and rollback validation

- **Goal:** validate the consolidated artifact, migration, Telegram, provider, outbox recovery, health, and rollback before production assignment.
- **Dependencies:** RS-001, ST-001, OB-005, EX-001, OP-001, CI-001, DV-003.
- **Affected architecture area:** full system/release.
- **Likely files/modules:** staging environment/runbook/evidence only plus defects found as separate PRs.
- **Acceptance criteria:** migration succeeds; recurring grant and duplicate replay behave; test Telegram send/retry/blocked cases pass; crash recovery observed; SIGTERM/readiness correct; rollback/restore decision tested.
- **Required tests:** staging scenario checklist with timestamps/release/schema revision; no production user destinations.
- **Risk:** High.
- **Estimated complexity:** L.
- **Parallelization group:** G9; blocking production release gate.
- **Recommended owner capability:** QA/DevEx.

### CL-001 — Contract legacy schema and remove proven dead compatibility code

- **Goal:** remove `Grant.text`, old notification compatibility fields, unused DB APIs/stats fields, old entry delegates, and archived setup dependencies after a stable observation window.
- **Dependencies:** ST-002 and at least one verified production release/rollback window.
- **Affected architecture area:** persistence/code cleanup.
- **Likely files/modules:** contract Alembic revisions, legacy DB/config APIs, old module delegates/docs/dependencies.
- **Acceptance criteria:** telemetry/search confirms no callers; contract migration preserves target counts; rollback boundary/tag documented; final module map matches freeze.
- **Required tests:** full CI, legacy-to-precontract then contract upgrade, staging deployment smoke.
- **Risk:** Medium/High.
- **Estimated complexity:** M.
- **Parallelization group:** G10; intentionally deferred cleanup.
- **Recommended owner capability:** Backend/Persistence.

## Blocking contract work

The following must stabilize before dependants branch independently:

1. FZ-001 architecture/ADR approval.
2. DV-001 supported runtime and required fast checks.
3. MG-001 Alembic baseline/production schema truth.
4. ID-001 canonicalization, aliases, resolver result contract.
5. ID-002 occurrence/alias schema and lossless backfill.
6. OB-001 outbox schema, payload, states, indexes, retry fields.
7. Application port/result signatures introduced by AP-001/AP-002.
8. CF-001 settings names/types/secret source.
9. RS-001 canonical repository/deployment cutover plan.

Schema contracts ID-002 and OB-001 are serialized; do not create competing migration heads casually.

## Safe parallel implementation work

- After DV-001: scraper, Telegram, lifecycle characterization and PostgreSQL harness can proceed independently.
- After ID-001: provider adapter work can run while persistence migration work proceeds.
- After OB-001: claim repository, subscription use cases, and retry classifier/renderer work can run in separate modules.
- Configuration and token replacement can run parallel to identity/outbox implementation after their own baselines.
- CI hardening and migration rehearsal can progress parallel once revisions/tests exist.
- Repository cutover and staging execution remain coordinated gates, not casual parallel changes.

## Completion definition

The plan is implementation-complete only when ST-002 passes and the production captain approves release. CL-001 is a later contract-cleanup package and is not allowed to block rollback during the first target release.
