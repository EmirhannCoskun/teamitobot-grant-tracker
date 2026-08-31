# ADR-007: Execution Model

- Status: Accepted
- Date: 2026-08-31

## Context

The bot currently runs Telegram polling, a periodic scrape task, synchronous DB/provider calls, and a health HTTP thread in one process. This is operationally simple but blocking calls can stall the asyncio event loop. Multiple replicas would compete for Telegram polling, duplicate collection/delivery, and race stats. No measured volume or ownership boundary requires independent scaling.

## Decision

Keep one production process and one production replica containing:

- Telegram long polling/inbound handlers;
- in-process periodic grant collection;
- PostgreSQL outbox dispatcher;
- liveness/readiness HTTP;
- one SQLAlchemy engine/pool and shared bootstrap lifecycle.

Keep a simple asyncio-based schedule; do not add a scheduler framework. During transition, offload bounded synchronous provider/DB application work so it does not block Telegram update dispatch. Replacing HTTP/ORM clients with async variants is deferred until measurement justifies the churn.

Dispatcher row claims are concurrency-safe with PostgreSQL leases and `SKIP LOCKED`, but deployment remains one replica. Startup validates schema/config, starts components in order, and reports readiness only when polling/scheduler/dispatcher are running. Shutdown marks unready, stops intake/scheduling, finishes or safely releases work within a deadline, closes clients/pool/health, and returns correct exit status.

## Alternatives Considered

1. Separate scraper and dispatcher workers/deployables.
2. Multiple identical bot replicas with database locking.
3. Webhook-based Telegram ingress.
4. External cron for collection.
5. APScheduler/Celery.
6. Fully synchronous process.

## Why Selected

One process matches the current workload and team size and avoids deployment/order/network failure modes. The outbox provides internal separation/recovery without requiring a worker service. Polling already works and avoids public Telegram ingress. Bounded offload addresses the actual responsiveness defect with less ecosystem churn than an async rewrite.

## Consequences

- Deployment must explicitly enforce one replica.
- Component lifecycle/readiness state becomes explicit.
- A slow dispatcher shares process resources, so batch size and loop fairness need configuration/tests.
- Scaling later requires a new ADR covering Telegram ownership and collector leadership, not just adding replicas.

## Risks

- One process is one failure domain.
- Thread offload around SQLAlchemy sessions must keep sessions thread-local and bounded.
- A bad schedule/dispatcher loop can starve other tasks.
- Provider/DB calls may exceed shutdown deadline.

Mitigation: process supervisor restart, truthful readiness, bounded pools/batches/timeouts, task health checks, lifecycle tests.

## Migration Implications

Extract scheduler/dispatcher as application components before rewriting bootstrap. Add one composition root, remove redundant Telegram initialization, make health server lifecycle-managed, and define shutdown order. Keep Procfile behavior compatible until packaging/deployment changes are separately reviewed.

## Rejected Over-Engineering

- Kubernetes/multi-pod leader election;
- Celery/RQ/background worker fleet;
- broker-backed scheduling;
- separate health service;
- webhook gateway;
- async ORM/client rewrite without latency evidence.

