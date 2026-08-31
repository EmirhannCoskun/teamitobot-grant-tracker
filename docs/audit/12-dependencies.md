# Dependency Audit

Audit date: 2026-08-31

No dependency was changed during the audit.

## `teamitobot-grant-tracker`

| Dependency | Classification | Evidence and recommendation |
| --- | --- | --- |
| `requests==2.31.0` | Necessary; high-risk version pin | Used by `scraper.py:34`; pip-audit reports three advisories. Current fixed-URL/simple-GET code does not use the vulnerable specialized paths, but upgrade under parser/HTTP tests |
| `beautifulsoup4==4.12.2` | Necessary | Directly implements FIRST HTML parsing; keep unless FIRST exposes a stable official structured API |
| `python-telegram-bot==21.7` | Necessary | Core polling/handler/send adapter. No duplicate Telegram library exists |
| `sqlalchemy==2.0.52` | Necessary | Appropriate ORM/transaction foundation; current code should use its unit-of-work and migration ecosystem more effectively |
| `python-dotenv==1.0.0` | Questionable in production; advisory-bearing pin | Convenient for local development; code only calls `load_dotenv`. pip-audit reports one advisory in mutation APIs not used here. Keep dev convenience or remove production dependency after config cleanup |
| `pytz==2023.3.post1` | Replaceable | Python 3.12+ includes `zoneinfo`; migration is optional and should follow timezone tests, not precede them |
| `psycopg2-binary==2.9.12` | Necessary driver; packaging choice to review | Required by current PostgreSQL URL/SQLAlchemy. Keep until a deliberate psycopg driver decision with deployment tests |

### Advisory result

As of 2026-08-31, `pip-audit` resolved four known vulnerabilities:

| Package | Advisory | Fixed version reported | Current-path exposure |
| --- | --- | --- | --- |
| requests 2.31.0 | CVE-2024-35195 | 2.32.0 | Low: code does not use a persistent Session or `verify=False` |
| requests 2.31.0 | CVE-2024-47081 | 2.32.4 | Low: URL is fixed; no application-managed `.netrc` use found |
| requests 2.31.0 | CVE-2026-25645 | 2.33.0 | Not on observed path: `extract_zipped_paths` is unused |
| python-dotenv 1.0.0 | CVE-2026-28684 | 1.2.2 | Not on observed path: `set_key`/`unset_key` are unused |

Upgrade is still recommended because the pins are old and known-vulnerable; exploitability context informs priority, not whether dependency hygiene matters.

## `itobot-token-setup`

| Dependency | Classification | Evidence and recommendation |
| --- | --- | --- |
| `Flask==3.1.3` | Necessary only if local web UI is retained | Provides routes/session/templates. The product need for a web UI is questionable, not the framework implementation |
| `requests==2.34.2` | Necessary if validation remains | Performs fixed Telegram `getMe` request with explicit timeouts |
| `pytest==9.1.1` | Necessary development dependency; duplicate in runtime set | Tests need it, deployed/runtime utility does not. Move to dev/test dependency group after consolidation |

`pip-audit` found no known vulnerabilities in the resolved setup dependency set on the audit date.

## Overlap and duplication

Both repositories depend on Python and `requests`, but there is no reusable shared HTTP abstraction to extract. A shared wrapper would add indirection with no current benefit. Consolidation should produce one dependency definition with dev/test grouping, while adapters continue using the client appropriate to their execution model.

`requests` in the main async process is a functional mismatch because it blocks the event loop. Options, in order of simplicity:

1. run the current synchronous scraper in a worker thread with explicit timeout/cancellation limits;
2. if measured concurrency needs justify it, use the async HTTP client already transitively used by `python-telegram-bot` or another explicit async client;
3. do not invent a generic HTTP abstraction across unrelated FIRST and Telegram setup calls.

## Manifest and supply-chain gaps

- Exact top-level pins but no hash-locked transitive resolution.
- No Python runtime constraint enforced by packaging.
- No runtime/dev dependency separation.
- No automated advisory/license/update workflow.
- No documented dependency update cadence.
- Two independent manifests increase drift without providing independent production lifecycles.

## Target dependency policy

1. Declare supported Python version(s) in one project file/runtime artifact.
2. Separate runtime and development dependencies.
3. Generate a reproducible lock/resolution appropriate to the chosen deployment tool.
4. Run tests and `pip-audit` on dependency changes.
5. Review direct dependencies quarterly or when advisories appear.
6. Remove only dependencies proven unused; avoid framework replacement during boundary cleanup.

