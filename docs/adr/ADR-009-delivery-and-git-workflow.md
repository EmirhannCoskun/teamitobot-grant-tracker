# ADR-009: Delivery and Git Workflow

- Status: Accepted
- Date: 2026-08-31

## Context

Neither repository has CI, tags, runtime pinning, migration verification, deployment-as-code beyond a Procfile, or rollback automation. The architecture will be implemented by a team, so contracts must stabilize before parallel work and changes must remain small/reviewable. Two long-lived branches would increase merge and migration conflicts without a separate release train.

## Decision

Use trunk-based development:

- protected `main`;
- short-lived task branches;
- focused PRs corresponding to one work package;
- at least one mandatory review;
- required green CI checks;
- no force-push/direct production changes on `main`;
- no long-lived `develop` branch;
- ADR approval before material architecture deviation.

GitHub Actions gates:

1. reproducible dependency install on the supported Python version;
2. Ruff format/lint;
3. incremental type checking for new domain/application code;
4. unit/regression tests;
5. PostgreSQL integration tests;
6. Alembic empty/legacy migration verification and schema drift check;
7. package/install/import/startup smoke;
8. dependency advisory and secret scans;
9. Docker build only if/when a production Dockerfile is approved.

Use GitHub's PostgreSQL service container in CI. Add Docker Compose only as a local/test PostgreSQL convenience. Keep the current non-container Render deployment until reproducibility/operations provide a measurable reason for a production Dockerfile.

Tag verified releases and record schema revision. Deploy migrations as a reviewed pre-deploy step; verify readiness/scrape/outbox after deploy. Use expand/contract compatibility and a rehearsed backup/restore/rollback runbook.

## Alternatives Considered

1. GitFlow with `develop` and release branches.
2. Long-lived architecture/refactor branch.
3. Direct commits to `main` for a small team.
4. One giant migration/refactor PR.
5. Mandatory production Dockerization before any work.
6. Manual testing/deployment only.

## Why Selected

Small PRs and fast integration reduce the exact cross-module/schema conflicts this plan creates. Protected trunk and automated PostgreSQL/migration gates provide safety without release-branch overhead. Conditional Docker avoids unrelated platform churn.

## Consequences

- Contract work and migration head ownership must be coordinated.
- Work packages need dependency/parallelization labels.
- CI becomes a prerequisite for implementation, not a final hardening step.
- Release tags and schema revisions create an auditable rollback boundary.
- Some staging/deployment steps remain provider-specific and require a runbook.

## Risks

- Slow CI can encourage oversized branches or bypass pressure.
- Multiple concurrent Alembic revisions can create branch heads/conflicts.
- Small PRs can leave temporary compatibility code.
- Required reviews can bottleneck a small team.

Mitigation: fast/slow job split, serialize blocking schema contracts, explicit compatibility cleanup tasks, reviewer rotation by capability.

## Migration Implications

The first implementation PR establishes runtime/tooling/CI gates. Baseline tests follow in parallel. Alembic revisions that touch the same migration head are blocking/serialized. Repository consolidation occurs only after application boundaries, token replacement, and green unified CI are ready.

## Rejected Over-Engineering

- GitFlow/release trains for one deployable;
- merge queues/complex release orchestration before PR volume needs them;
- mandatory Kubernetes/container registry pipeline;
- multi-environment promotion platform;
- monolithic “architecture refactor” branch;
- independent versioning of internal modules.

