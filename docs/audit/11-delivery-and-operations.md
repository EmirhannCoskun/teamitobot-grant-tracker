# Delivery and Operations

Audit date: 2026-08-31

## Artifacts found

| Capability | `teamitobot-grant-tracker` | `itobot-token-setup` |
| --- | --- | --- |
| GitHub Actions/CI | None | None |
| Docker/Compose | None | None |
| Platform config | `Procfile` only | None |
| Runtime version pin | README says Python 3.12+; not enforced | None |
| Dependency lock/hashes | None | None |
| Migration tooling | None | N/A |
| Release tags/versioning | None | None |
| Rollback procedure | None | None |
| Health check | Unconditional embedded HTTP server | None |
| Deployment scripts | None | None |
| Environment templates | None | None |

## Current deployment reconstruction

README describes Render plus PostgreSQL and UptimeRobot. The only enforceable artifact is:

```text
web: python bot.py
```

The bot is therefore presented to the platform as a web service solely to expose its embedded health endpoint. The process also runs polling and scheduling. There is no `render.yaml`, runtime declaration, database resource link, health path declaration, environment manifest, replica count, or release command.

The setup app is a loopback Flask development server. It should not be inferred to be a production service.

## Operational constraints

### Single replica

One and only one main replica is currently safe. This is not encoded in deployment configuration. More replicas would compete for Telegram polling and duplicate scheduler/delivery work.

### Database changes

`create_all` runs in the main process at startup. There is no ordered migration phase, version table, compatibility window, or rollback plan. A code rollback after an implicit/manual schema change has unknown behavior.

### Exit and restart

Fatal exceptions at the outer entry point are printed and swallowed (`bot.py:752-764`), so the process can exit with code 0. Automated platforms may treat this as a clean stop rather than a failure requiring urgent restart/alerting.

## Two-repository release analysis

There is no version compatibility problem today because there is no integration contract at all. That is worse than coordinated release friction for the promised setup workflow: releases cannot be declared compatible or incompatible.

| Concern | Current result |
| --- | --- |
| Coordinated feature release | Manual; no cross-repo CI or issue/release link |
| Version compatibility | Undefined; no API/file/env contract |
| Deployment order | Undefined; setup output is never consumed |
| Rollback compatibility | Undefined |
| Separate scaling | Not required; setup is local-only |
| Separate owners | No evidence; same project/technology/commit timeframe |

## Minimum target pipeline

For the consolidated repository:

1. **Validate**: install from locked/resolved dependencies, compile, lint, unit tests.
2. **Integrate**: disposable PostgreSQL, migrations up/down or forward-compat check, application integration tests.
3. **Secure**: dependency advisory and secret scanning; fail only under an agreed severity/exploitability policy.
4. **Build**: create one immutable artifact with Python version and commit metadata.
5. **Smoke**: start with fake Telegram/FIRST and disposable PostgreSQL; assert readiness and graceful shutdown.
6. **Deploy one replica**: apply reviewed migrations in a dedicated phase, then deploy runtime.
7. **Verify**: readiness, last successful scrape, Telegram authentication, pending queue age.

GitHub Actions is sufficient. A container is optional: use it if Render/runtime reproducibility requires it, not as an architectural goal.

## Release and rollback

- Tag releases after baseline tests exist.
- Keep configuration additions backward-compatible for at least one deploy.
- Use expand/migrate/contract for schema changes that cannot be rolled back atomically.
- Back up PostgreSQL before identity/timezone migrations and rehearse restoration.
- Roll back application code only to a version compatible with the current schema migration.
- Preserve the old repository read-only during consolidation until the first consolidated release is verified.

## Environment management

Required environment variables should be documented in a redacted `.env.example` or platform manifest, with type/range and ownership:

```text
TELEGRAM_BOT_TOKEN=<REDACTED>
DATABASE_URL=<REDACTED>
CHECK_INTERVAL=900
PORT=8080
LOG_LEVEL=INFO
```

Production values belong in Render/provider secret storage. The setup UI must not become a public endpoint for modifying a live token.

## Health and deployment checks

The deployment should distinguish liveness/readiness and verify one-replica mode. A successful socket bind alone is insufficient. During shutdown, readiness should turn false before polling/scheduling stop.

## Developer experience

Add one documented command for each supported task:

- create environment/install dependencies;
- run unit tests;
- run PostgreSQL integration tests;
- run bot locally with fake adapters or a test token;
- run the optional local setup tool while it exists;
- lint/security audit;
- apply/revert migrations.

Avoid maintaining separate duplicated setup documents and dependency files once the repositories consolidate.

