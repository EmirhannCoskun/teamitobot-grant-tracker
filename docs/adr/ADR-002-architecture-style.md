# ADR-002: Architecture Style

- Status: Accepted
- Date: 2026-08-31

## Context

The production system is four Python modules, one PostgreSQL database, one Telegram bot, one FIRST scraper, and one deployable process. `bot.py:367-572` currently combines scheduling, provider I/O, identity, persistence, message rendering, Telegram delivery, and retry behavior. `database.py` combines ORM models and every operation. The main repository has no tests. The system needs test seams and transaction boundaries, but no evidence supports distributed services or a large enterprise architecture.

## Decision

Adopt a lightweight modular monolith with Ports & Adapters:

- Domain: occurrence identity and delivery/retry values/invariants.
- Application: collection, subscription/status, and outbox-delivery use cases.
- Inbound adapters: Telegram handlers and the in-process schedule trigger.
- Outbound adapters: FIRST HTTP/parser, SQLAlchemy/PostgreSQL, Telegram notification sender.
- Bootstrap/composition root: settings, logging, health, lifecycle, dependency construction.

Define only meaningful external I/O ports. Keep one repository, one production artifact, and one process.

## Alternatives Considered

1. Keep the current flat modules and add tests around them.
2. Simple three-layer presentation/service/data architecture.
3. Full Clean Architecture/DDD with entities, repositories, domain services, events, and use-case classes for every operation.
4. Multiple services/workers for Telegram, scraping, and notifications.

## Why Selected

Three real integration boundaries—Telegram, FIRST markup/HTTP, and PostgreSQL—already cause untestable coupling and failure ambiguity. A small port around each permits pure application tests and transaction-oriented persistence without framework replacement. A modular monolith preserves simple deployment and in-process calls.

The style is selected for concrete seams, not for folder aesthetics. Modules may remain functions/dataclasses where classes add no value.

## Consequences

- `bot.py`, `database.py`, and `scraper.py` will be split incrementally after characterization tests.
- Dependency construction moves to one explicit bootstrap module.
- Domain/application code becomes importable without environment variables or infrastructure packages.
- Changes across modules still ship atomically as one application.
- Implementation engineers must prevent ports from becoming generic pass-through wrappers.

## Risks

- Over-extraction could create more files/interfaces than behavior warrants.
- Moving lifecycle code can regress polling/shutdown.
- A “big bang” folder move would defeat the incremental plan.

Mitigation: one behavior slice per PR, characterization tests first, compatibility delegates during movement.

## Migration Implications

Extract in this order: pure provider parser/identity values, transaction-oriented application use cases, Telegram renderer/handlers, persistence adapter, then bootstrap. Do not move repositories until protected application boundaries exist.

## Rejected Over-Engineering

- microservices;
- Clean Architecture template with one class/interface per operation;
- domain event bus;
- CQRS/Event Sourcing;
- generic repository for every table;
- dependency injection framework;
- separate API/service solely to satisfy layer diagrams.

