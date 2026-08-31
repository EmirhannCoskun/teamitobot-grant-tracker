# Security Review

Audit date: 2026-08-31

## Scope and methods

The review covered tracked source, manifests, ignore rules, sensitive filenames across Git history, token/private-key/database-credential-shaped diffs, HTTP input/output paths, filesystem operations, ORM usage, shell/process execution, logging, authorization, and dependency advisories.

No actual secret values are reproduced here.

## Secret findings and rotation decision

- No `.env`, `config.json`, private key, credential file, or live-looking database URL is tracked in either current tree.
- History filename scanning found no historically tracked sensitive file names.
- Token-shaped strings in `itobot-token-setup` history are synthetic test fixtures, not credible live bot credentials.
- The main repository reads `TELEGRAM_BOT_TOKEN=<REDACTED>` and `DATABASE_URL=<REDACTED>` from environment variables.
- The setup repository stores `telegram_bot_token=<REDACTED>` in ignored local JSON.

**Rotation conclusion:** repository evidence alone does not require credential rotation. Rotate the Telegram token if the local `data/config.json` has ever been copied, backed up insecurely, exposed to other OS users, or deployed beyond loopback. Rotate any credential if a broader secret-scanning system reports exposure; this audit's history scan was pattern-based, not a guarantee about every external fork/cache.

## Security findings

| ID | Severity | Finding | Evidence | Recommendation |
| --- | --- | --- | --- | --- |
| SEC-01 | HIGH if exposed; LOW on loopback | Setup endpoints have no operator authentication | `app.py:299-570`; only CSRF is enforced; server binds `127.0.0.1` at `43`, `579-582` | Preserve loopback-only scope. Do not deploy publicly without authenticated operator access and TLS |
| SEC-02 | MEDIUM | Token is plaintext and file permissions are not hardened | `token_manager.py:92-116` atomically writes JSON but does not set restrictive mode/ACL | Prefer provider secret storage; if local file remains, create with owner-only permissions where supported and document OS limitations |
| SEC-03 | MEDIUM | Main manifest contains known advisories | `requests==2.31.0` and `python-dotenv==1.0.0`; pip-audit found four advisories | Upgrade in a tested stage; current called code paths do not appear to exercise the advisory-specific APIs |
| SEC-04 | MEDIUM | Telegram chat IDs are logged directly | `bot.py:114`, `132`, `167`, `542-551`; database retains chat ID and username | Treat as personal data; minimize/redact logs and define retention/deletion behavior |
| SEC-05 | MEDIUM | Token setup and bot secret contracts disagree | Setup writes a file; bot uses environment (`config.py:18`) | Adopt one supported environment/provider-secret contract and remove misleading claims |
| SEC-06 | LOW | Session secret silently changes on every restart when not configured | `app.py:30-33` | Accept for ephemeral loopback use or require a configured secret if sessions must survive/reach multiple workers |
| SEC-07 | LOW under loopback | In-memory rate limiter is unbounded by unique client IP and not synchronized | `app.py:153-190` | Keep local-only; if exposed through a proxy, use a bounded thread-safe limiter and trusted-proxy configuration |
| SEC-08 | LOW | Success page states Telegram is connected based only on token file presence | `app.py:488-504`; it does not revalidate on page load | Label as “token saved/previously validated” or revalidate deliberately without leaking details |
| SEC-09 | LOW | Main ignore rules cover `.env` and `.env.local` but not the broader `.env.*` family | `teamitobot-grant-tracker/.gitignore:1-3` | Ignore `.env.*` with an explicit `!.env.example` exception to reduce future accidental commits |

## Dependency advisory details

`pip-audit` was run against both manifests on 2026-08-31.

### Main repository

Four advisories in two packages:

- `requests 2.31.0`: CVE-2024-35195 (session pool after `verify=False`), CVE-2024-47081 (`.netrc` leakage with crafted URLs), and CVE-2026-25645 (`extract_zipped_paths` predictable temporary path).
- `python-dotenv 1.0.0`: CVE-2026-28684 (`set_key`/`unset_key` symlink handling).

The audited code does not use `requests.Session`, `verify=False`, user-controlled request URLs, `extract_zipped_paths`, `set_key`, or `unset_key`. Immediate exploitability is therefore low, but carrying known-vulnerable pins is avoidable risk and fails a reasonable supply-chain baseline.

### Setup repository

No known vulnerabilities were reported for the resolved dependency set.

No dependency was upgraded during this phase.

## Input and injection review

- **SQL injection:** queries use SQLAlchemy expressions; no raw SQL or string-built query was found.
- **Command injection:** neither repository executes shell commands or subprocesses.
- **Path traversal:** token file paths are fixed from `__file__`; request input does not select paths.
- **SSRF:** main and setup request targets are fixed. The token changes a Telegram URL path segment but must match a restrictive token regex; host/scheme remain fixed.
- **Unsafe deserialization:** setup uses `json.load` with a 4 KiB file-size guard; no pickle/YAML object loading.
- **XSS:** templates do not render user-controlled token or bot username. Client error output uses `textContent`, not `innerHTML`.
- **CSRF:** state-changing setup routes validate a per-session header using constant-time comparison. Tests cover missing/invalid tokens.
- **Request size:** Flask enforces 4 KiB maximum request size.
- **Security headers:** CSP, frame denial, MIME sniff protection, and no-referrer policy are set on Flask responses.

## Telegram-specific security

- There are no privileged/admin commands, so public command access is consistent with product behavior.
- Bot token values are not printed or returned by the code. The setup tests explicitly assert this.
- Telegram message content derived from FIRST is not escaped. This is primarily a delivery/reliability problem; a compromised upstream page could also control displayed links. Continue to show explicit trusted domains or escape/render safely.
- Token validation necessarily places the token in Telegram's API URL. Application/proxy HTTP logging must never log full outbound URLs.

## Static scan context

Bandit found no high-severity issue. Its main medium item was the intended all-interface health bind. Setup production code produced only a low-confidence false positive on the JSON key name `telegram_bot_token`.

## Minimum security baseline

1. One canonical secret source: deployment-provider environment secret; never a committed or shared plaintext file.
2. Loopback-only setup utility, or retire it; never silently expose it as part of the health web service.
3. Tested dependency upgrades and automated advisory scanning in CI.
4. Structured logging with token/URL redaction and minimized chat identifiers.
5. Document data retention and a user deletion/deactivation path.
6. Explicitly escape Telegram output and classify permanent Telegram authorization failures.
