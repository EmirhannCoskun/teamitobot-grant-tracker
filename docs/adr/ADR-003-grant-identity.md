# ADR-003: Grant Occurrence Identity

- Status: Accepted
- Date: 2026-08-31

## Context

The application compares `(title, start_date, end_date)` to detect new grants (`bot.py:406-424`), while `DB.add_grant` upserts on title or legacy text (`database.py:333-380`). An audit probe proved that two seasons with the same title collapse to one row. FIRST's current page exposes positional `grant-details-N` IDs, not documented stable provider identifiers. Application URLs often contain occurrence-specific form IDs, but current data also has different program/date occurrences sharing the same URL. Titles can change between seasons.

The product needs recurring opportunities to coexist, exact reprocessing to be idempotent, metadata correction not to overwrite identity, and legacy migration without silent loss.

## Decision

Model a concrete `GrantOccurrence` with a stable internal database ID. Do not require `GrantDefinition` now.

Use versioned identity evidence scoped by provider:

- documented stable `provider_occurrence_id`, when available;
- canonical `application_locator` plus program scope as non-unique continuity evidence;
- exact unique `observation_fingerprint` computed as SHA-256 over canonical JSON of provider, normalized title, sorted program codes, start date, and end date.

Resolution algorithm v1:

1. provider-ID alias match;
2. exact observation fingerprint match;
3. unique same-program application-locator match only when date windows overlap;
4. otherwise create a new occurrence;
5. on ambiguity, never merge—create a distinct occurrence and emit a structured conflict event.

Attach new evidence to an existing occurrence when a continuity match succeeds. Strong provider/observation aliases map to only one occurrence; application-locator evidence may map to multiple recurrences and is never sufficient without the program/window rule. Update mutable fields in place; never change the internal ID or its initial source key. Non-overlapping recurring windows remain distinct even if a URL is reused.

Backfill every legacy row one-to-one. Rows lacking enough identity data receive a unique `legacy:<existing grant id>` source key. No backfill de-duplicates or deletes rows automatically.

## Alternatives Considered

1. Title alone.
2. `(title, start_date, end_date)` as a permanent DB natural key.
3. Application URL alone.
4. Positional `grant-details-N` HTML ID.
5. `GrantDefinition` plus `GrantOccurrence` inferred from normalized sponsor/title.
6. Manual UUID assigned on every scrape with no source aliases.

## Why Selected

An internal surrogate prevents metadata from redefining durable identity. Aliases make exact provider reprocessing idempotent and allow metadata corrections to attach to an existing occurrence. Conservative ambiguity handling favors an observable possible duplicate over the current silent overwrite/loss.

`GrantDefinition` does not solve provider identity and would require unreliable lineage inference. No current feature queries cross-season definitions.

## Consequences

- A `grant_identity_aliases` table and identity algorithm version are required.
- Exact duplicates are prevented by provider-scoped unique strong aliases and occurrence source keys.
- Rare ambiguous provider edits can create a duplicate occurrence and notification; this is preferable to merging two grants.
- Operators need structured identity-conflict visibility.
- A future stable provider ID can be attached as a new alias without changing occurrence IDs.

## Risks

- URL canonicalization mistakes can create or merge aliases incorrectly.
- Overlap-based continuity cannot prove identity when a provider changes every identifying field.
- Identity algorithm changes require migration/versioning and regression fixtures.

Mitigation: version keys, preserve all aliases, test current/legacy/recurring fixtures, and never silently merge ambiguity.

## Migration Implications

Add nullable identity fields and alias storage, backfill one-to-one, validate counts, then add uniqueness/NOT NULL constraints. Keep legacy IDs. The first migration must not collapse duplicate-title rows. Cut over reads/writes only after backfill verification against a sanitized production snapshot.

## Rejected Over-Engineering

- probabilistic/fuzzy title matching;
- machine-learning entity resolution;
- a manually curated sponsor taxonomy;
- `GrantDefinition` without a stable source/use case;
- event sourcing of every scrape;
- global identity across unrelated providers before a second provider exists.
