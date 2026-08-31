# ADR-006: Configuration and Secrets

- Status: Accepted
- Date: 2026-08-31

## Context

`config.py` reads environment variables into class attributes and validates at import time. Numeric values are converted but not range-checked; `LOG_LEVEL` and `ENVIRONMENT` are unused. Domain/infrastructure imports trigger configuration validation. The setup repository writes a plaintext token file that the bot never reads. Production README already relies on Render/environment secrets.

## Decision

Use one immutable typed settings object created and validated in bootstrap. Domain and application modules receive ordinary values/ports and never read the environment.

Canonical production sources:

- deployment-provider environment/secret store for `TELEGRAM_BOT_TOKEN` and `DATABASE_URL`;
- non-secret environment variables for runtime tuning;
- `.env` only for local development, loaded only by bootstrap.

Validate required presence, types, ranges, supported modes, and cross-field constraints before resources start. Errors identify the variable but never its value. Fatal invalid configuration exits non-zero.

Use standard-library parsing/dataclasses initially; do not add a settings framework unless validation complexity grows. Keep `python-dotenv` only for local convenience and upgrade it under normal dependency work.

The Flask/file token setup is not a configuration source. Replace it with documentation and optionally a non-persisting CLI that validates a provided environment/token via Telegram `getMe` without logging it.

## Alternatives Considered

1. Keep import-time class globals.
2. Make `data/config.json` canonical.
3. Store secrets in PostgreSQL.
4. Add Pydantic Settings or another configuration framework immediately.
5. Add a production web UI for changing secrets.

## Why Selected

Environment/provider secret storage already configures the working deployment and avoids a new secret database/UI. Explicit bootstrap validation improves tests, failure messages, and dependency direction with little code. A new configuration framework has no demonstrated benefit for the small setting set.

## Consequences

- Imports no longer require live secrets.
- Startup has one redacted configuration summary and one validation path.
- Tests can construct settings directly.
- Local `.env` remains convenient but is never a production contract.
- Token changes use provider operations/redeploy rather than an application endpoint.

## Risks

- A transition period can accidentally support two sources with different precedence.
- Logs/exceptions could leak URLs/tokens if redaction is incomplete.
- Removing the UI may surprise an undiscovered local user.

Mitigation: one documented precedence, redaction tests, usage confirmation/cutover notice, and archive-readiness after transition. Actual repository archive/delete requires separate Software Captain approval.

## Migration Implications

Introduce settings construction behind current `config` compatibility first; migrate callers; add startup/config tests; then remove direct class globals/import-time validation. Update `.gitignore` to cover `.env.*` while allowing a redacted `.env.example`. The token tool is removed only after the canonical workflow and optional validator are available.

## Rejected Over-Engineering

- Vault/Secrets Manager integration layer without a current provider requirement;
- dynamic runtime secret reload;
- production secret-management UI;
- secrets in DB/files committed or mounted by the app;
- configuration service;
- new validation framework solely for a handful of values.
