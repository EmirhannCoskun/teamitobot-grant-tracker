# ADR-001: Repository Boundary

- Status: Accepted for modernization planning
- Date: 2026-08-31
- Decision owners: project maintainers

## Context

The grant bot is split across `teamitobot-grant-tracker` and `itobot-token-setup`. The second repository was created to simplify Telegram integration. The audit had to determine whether that split represents independent product/runtime boundaries or accidental organization.

## Current state

`teamitobot-grant-tracker` is one deployable Python process containing Telegram long polling, FIRST scraping, PostgreSQL persistence, notification delivery, and a health server.

`itobot-token-setup` is a local Flask utility. It validates a Telegram token with `getMe` and saves it to `itobot-token-setup/data/config.json`.

The main bot never reads that file; it requires `TELEGRAM_BOT_TOKEN` from its environment. There is no library, HTTP, webhook, messaging, shared database/file, subprocess, release, or manual transfer contract between repositories.

## Forces

### Independent lifecycle

- The main bot can be deployed without the setup repository by supplying environment secrets.
- The setup utility can run independently, but its output has no consumer, so this is isolation rather than a useful independent lifecycle.
- Normal Telegram/grant features belong only to the main app; no evidence shows coordinated independent releases adding value.

### Reusability

The setup utility is branded for İTOBOT, stores one specific Telegram token schema, and has no package/API contract. It is not realistically reusable by another application without modification.

### Coupling

Code-level coupling is zero. Conceptual coupling is total: the utility exists solely to configure the bot. The missing configuration contract is a defect, not a sign of healthy decoupling.

### Ownership

Both repositories use Python, were changed by the same project in the same timeframe, and have no owner/team metadata suggesting separate maintainers.

### Technology boundary

Both use Python and `requests`. Flask is used only for the optional local UI. There is no distinct ecosystem requiring repository isolation.

### Security boundary

Keeping a credential-editing UI out of the production process is valuable. A separate Git repository is not required for that boundary. Runtime composition and deployment configuration provide the meaningful boundary.

### Deployment/scaling boundary

The setup utility has no production deployment and should remain loopback-only. The main bot must run as one replica. Neither component needs independent production scaling.

## Options

### Option A: Keep two repositories

Advantages:

- Preserves current Git history and local-tool isolation.
- Setup tests/releases can change without touching the bot repository.

Disadvantages:

- Leaves the primary setup flow disconnected unless a new cross-repo contract is invented.
- Duplicates manifests, documentation, CI setup, dependency maintenance, and release administration.
- Makes discoverability and compatibility worse for one small team/product.

Operational cost: two pipelines/release processes would be required to make the split professional, despite only one production runtime.

Developer experience: users must clone two repositories and still manually solve secret transfer.

Deployment impact: no benefit; setup remains local and main remains one service.

Testing impact: requires a new cross-repository contract test.

Security impact: apparent isolation, but no stronger than keeping a local-only tool outside the production entry point in one repository.

Migration cost: lowest immediate cost, highest ongoing cost.

### Option B: Monorepo with multiple deployable applications

Advantages:

- One change/CI surface with explicit app boundaries.
- Could preserve the Flask app unchanged.

Disadvantages:

- Treats the local setup screen as a production deployable even though no requirement supports that.
- Adds build/deploy matrix complexity and compatibility policies for a tiny system.

Operational cost: medium; two artifacts/process definitions.

Developer experience: better discoverability, but still two runtimes and a secret handoff contract.

Deployment impact: risks accidental public deployment of the credential editor.

Testing impact: easier cross-app tests, still more than needed.

Security impact: must strongly prevent setup app exposure.

Migration cost: medium.

### Option C: Single modular application repository

One production application, with Telegram as an adapter around application use cases. Environment/provider secret storage remains canonical. If the setup UI must be preserved during migration, keep it under `tools/token-setup` as loopback-only operator tooling, excluded from the production entry point/artifact; retire it after its useful validation/export behavior is replaced.

Advantages:

- Matches the actual one-product, one-team, one-runtime system.
- Removes compatibility/release ambiguity.
- Enables atomic changes across domain, Telegram, persistence, tests, and docs.
- Keeps a real security boundary by excluding the tool from production composition.
- Simplest target architecture and CI.

Disadvantages:

- Requires planned history/archive and documentation work.
- A retained setup tool still needs one explicit secret export/deploy contract.
- Contributors lose independent repository permissions/versioning, for which no current requirement exists.

Operational cost: lowest; one production artifact/pipeline.

Developer experience: one clone, one test command, one configuration contract.

Deployment impact: one bot service; setup utility is never deployed with it.

Testing impact: one suite can cover application behavior and optional tooling contract.

Security impact: reduces secret-flow confusion; preserves loopback/tool boundary by composition.

Migration cost: medium but incremental and reversible.

### Option D: Retire the setup repository without moving its UI

Advantages:

- Absolute simplest runtime/repository state.
- Uses the already-working environment/provider secret mechanism.
- Eliminates plaintext local token storage and Flask attack surface.

Disadvantages:

- Removes a polished local setup experience.
- Requires operator documentation or a smaller CLI/provider-specific setup step.
- Must preserve any stakeholder-required token validation behavior.

Operational cost: lowest.

Developer experience: simpler for experienced deployers, potentially less friendly for first-time operators.

Deployment impact: none beyond existing bot.

Testing impact: setup tests can be retired after equivalent secret/config validation is covered.

Security impact: strongest reduction in surface.

Migration cost: low if no active users depend on the UI; unknown until usage is confirmed.

## Decision

**The system should not remain two repositories. Choose Option C: consolidate into a single modular application repository with one deployable bot.**

The production application continues to obtain `TELEGRAM_BOT_TOKEN` from environment/provider secret storage. Do not merge Flask routes into `bot.py` or expose them through the health server. Preserve the setup utility temporarily as local-only tooling during migration only if a real operator need is confirmed; otherwise take the Option D execution path and retire it after documentation/config tests replace its value.

This is a repository consolidation decision, not an instruction to combine every concern into one module.

## Consequences

Positive:

- one source of truth for runtime configuration and documentation;
- one CI/release/versioning path;
- atomic feature changes across adapters and core;
- fewer dependency and ownership boundaries;
- easier baseline and integration testing.

Negative/required work:

- preserve/archive the setup repository and its 83-test behavior baseline;
- confirm whether anyone actively uses the UI;
- define the operator secret workflow before archiving;
- ensure production artifact excludes local credential tooling;
- communicate the new canonical repository and make the old repository read-only after cutover.

## Migration constraints

- Do not move repositories until Stage 0 tests and Stage 1 critical fixes exist.
- Tag both pre-consolidation states.
- Keep old deployment configuration functional through cutover.
- Never expose the setup utility publicly to make integration easier.
- No database schema or public command changes are part of this ADR itself.

