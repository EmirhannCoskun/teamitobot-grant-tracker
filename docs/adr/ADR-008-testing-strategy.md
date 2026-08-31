# ADR-008: Testing Strategy

- Status: Accepted
- Date: 2026-08-31

## Context

The main bot has zero automated tests. The setup utility has 83 passing pytest tests and 90% measured coverage, proving pytest fits the ecosystem. Critical defects span pure identity rules, provider parsing, PostgreSQL constraints/transactions, Telegram delivery semantics, configuration, and process lifecycle. SQLite cannot validate PostgreSQL row locks, partial indexes, timezone behavior, or migrations.

## Decision

Keep pytest and adopt a risk-based test pyramid:

- pure unit tests for identity, retry classification, rendering, and application decisions;
- adapter contract tests using dated sanitized FIRST fixtures and Telegram fakes;
- real isolated PostgreSQL integration tests for repositories, atomicity, concurrency, and outbox leases;
- Alembic migration tests from empty and from a sanitized legacy schema/data fixture;
- subprocess/lifecycle tests for startup config, readiness, signal handling, and fatal exits;
- staging-only live smoke with a test Telegram bot and read-only FIRST access.

Critical acceptance focuses on behavior, not a global coverage percentage. New domain/application modules are designed for ordinary fakes, not mocks of private implementation calls.

PostgreSQL tests run in a GitHub Actions service container and a documented local container/instance. The tested major version must match the managed production major once recorded.

## Alternatives Considered

1. Unit tests only with mocked SQLAlchemy.
2. SQLite for all persistence tests.
3. Live FIRST/Telegram calls in normal CI.
4. End-to-end tests only.
5. Coverage threshold as the primary quality gate.
6. Replace pytest.

## Why Selected

The failure modes occur at multiple boundaries. Cheap pure tests cover combinatorial rules; real PostgreSQL is necessary for the exact mechanisms selected; fixtures avoid flaky provider dependence; staging live smoke validates credentials/network without destabilizing PRs. This uses the existing successful framework.

## Consequences

- CI is slower than unit-only testing and needs PostgreSQL setup.
- A sanitized legacy snapshot becomes a maintained test asset.
- Migration and crash/concurrency tests are mandatory for schema/outbox PRs.
- Live provider smoke is non-blocking or scheduled/staging, not a PR dependency.
- Existing setup tests are preserved only until useful CLI/docs behavior replaces the Flask tool.

## Risks

- Integration tests can be flaky if isolation/cleanup is weak.
- Fixtures can drift from the provider.
- Over-mocking Telegram SDK internals can make tests brittle.
- Legacy snapshot may accidentally contain personal/secrets data.

Mitigation: per-test transactions/databases, deterministic clock, dated fixture refresh procedure, adapter-level contract fakes, automated sanitization review.

## Migration Implications

Add CI/test tooling first, then characterization suites before source movement. Build the PostgreSQL harness and legacy fixture before Alembic/identity/outbox migrations. Every work package defines required tests and cannot claim completion without them.

## Rejected Over-Engineering

- full browser farm for a tool scheduled for removal;
- contract-testing platform/service virtualization suite;
- mutation testing as an initial gate;
- production traffic replay;
- exhaustive framework-internal tests;
- a high coverage target disconnected from risk.

