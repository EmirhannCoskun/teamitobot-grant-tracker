"""Grant candidate and occurrence value objects.

This module deliberately has no provider, persistence, framework, or environment
dependencies.  Provider adapters normalize their raw records into
``GrantCandidate`` values before identity resolution.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import TYPE_CHECKING, Iterable
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

if TYPE_CHECKING:
    from domain.identity import IdentityAlias

_WHITESPACE = re.compile(r"\s+")
_SOURCE = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_PROGRAM_CODE = re.compile(r"[A-Z][A-Z0-9_-]{1,31}\Z")
_POSITIONAL_HTML_ID = re.compile(
    r"(?:grant[-_]?details?|details?)[-_]?\d+\Z",
    re.IGNORECASE,
)
_SOURCE_KEY = re.compile(r"(?:v[1-9]\d*:[0-9a-f]{64}|legacy:[1-9]\d*)\Z")
_TRACKING_PARAMETERS = frozenset(
    {"fbclid", "gclid", "dclid", "mc_cid", "mc_eid", "msclkid"}
)
_PROGRAM_ALIASES = {
    "frc": "FRC",
    "first robotics competition": "FRC",
    "first® robotics competition": "FRC",
}


class DomainValidationError(ValueError):
    """A provider value cannot satisfy the frozen domain contract."""


def normalize_text(value: str, *, field: str) -> str:
    """Apply NFKC and whitespace normalization while preserving display case."""
    if not isinstance(value, str):
        raise DomainValidationError(f"{field} must be a string")
    normalized = _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", value)).strip()
    if not normalized:
        raise DomainValidationError(f"{field} must not be empty")
    return normalized


def normalize_source(value: str) -> str:
    """Normalize and validate a stable provider/source code."""
    source = normalize_text(value, field="source").casefold().replace("-", "_")
    if not _SOURCE.fullmatch(source):
        raise DomainValidationError(
            "source must start with a letter and contain only lowercase letters, "
            "digits, or underscores"
        )
    return source


def normalize_programs(values: str | Iterable[str]) -> tuple[str, ...]:
    """Map provider program labels to sorted, unique stable program codes."""
    raw_values = (values,) if isinstance(values, str) else tuple(values)
    if not raw_values:
        raise DomainValidationError("at least one program is required")

    programs: set[str] = set()
    for raw_value in raw_values:
        label = normalize_text(raw_value, field="program")
        folded = label.casefold()
        program = _PROGRAM_ALIASES.get(folded, label.upper())
        if not _PROGRAM_CODE.fullmatch(program):
            raise DomainValidationError(f"unsupported program label: {label!r}")
        programs.add(program)
    return tuple(sorted(programs))


def normalize_date(value: date | str, *, field: str) -> date:
    """Normalize a date or strict ISO ``YYYY-MM-DD`` value."""
    if isinstance(value, datetime):
        raise DomainValidationError(f"{field} must be a date, not a datetime")
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise DomainValidationError(f"{field} must be a date or ISO date string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise DomainValidationError(
            f"{field} must use the ISO YYYY-MM-DD format"
        ) from error
    if parsed.isoformat() != value:
        raise DomainValidationError(f"{field} must use the ISO YYYY-MM-DD format")
    return parsed


def _is_tracking_parameter(name: str) -> bool:
    folded = name.casefold()
    return folded.startswith("utm_") or folded in _TRACKING_PARAMETERS


def canonicalize_application_url(value: str | None) -> str | None:
    """Canonicalize a safe HTTP(S) application locator.

    Scheme and host case, default ports, fragments, and known tracking-only
    parameters do not affect identity.  Path and semantic query parameters,
    including provider form identifiers, are preserved.
    """
    if value is None:
        return None
    raw_url = normalize_text(value, field="application_url")
    if any(character.isspace() for character in raw_url):
        raise DomainValidationError("application_url must not contain whitespace")

    try:
        parts = urlsplit(raw_url)
        port = parts.port
    except ValueError as error:
        raise DomainValidationError("application_url is invalid") from error

    scheme = parts.scheme.casefold()
    if scheme not in {"http", "https"} or not parts.hostname:
        raise DomainValidationError("application_url must be an absolute HTTP(S) URL")
    if parts.username is not None or parts.password is not None:
        raise DomainValidationError("application_url must not contain credentials")

    try:
        host = parts.hostname.encode("idna").decode("ascii").casefold()
    except UnicodeError as error:
        raise DomainValidationError("application_url host is invalid") from error
    if ":" in host:
        host = f"[{host}]"
    default_port = (scheme == "http" and port == 80) or (
        scheme == "https" and port == 443
    )
    netloc = host if port is None or default_port else f"{host}:{port}"

    query_items = [
        (name, query_value)
        for name, query_value in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking_parameter(name)
    ]
    query = urlencode(query_items, doseq=True, quote_via=quote)
    path = parts.path or "/"
    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_provider_occurrence_id(value: str | None) -> str | None:
    """Validate documented provider identity and reject positional DOM IDs."""
    if value is None:
        return None
    provider_id = normalize_text(value, field="provider_occurrence_id")
    if _POSITIONAL_HTML_ID.fullmatch(provider_id):
        raise DomainValidationError(
            "positional HTML IDs are not stable provider occurrence identity"
        )
    if len(provider_id) > 255:
        raise DomainValidationError("provider_occurrence_id must be at most 255 chars")
    return provider_id


@dataclass(frozen=True, slots=True)
class DateWindow:
    """Inclusive application window."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if isinstance(self.start, datetime) or not isinstance(self.start, date):
            raise DomainValidationError("start_date must be a date")
        if isinstance(self.end, datetime) or not isinstance(self.end, date):
            raise DomainValidationError("end_date must be a date")
        if self.end < self.start:
            raise DomainValidationError("end_date must not be before start_date")

    @classmethod
    def normalize(cls, start: date | str, end: date | str) -> DateWindow:
        """Build a validated window from date or strict ISO values."""
        return cls(
            start=normalize_date(start, field="start_date"),
            end=normalize_date(end, field="end_date"),
        )

    def overlaps(self, other: DateWindow) -> bool:
        """Return whether two inclusive windows share at least one day."""
        return self.start <= other.end and other.start <= self.end


@dataclass(frozen=True, slots=True)
class GrantCandidate:
    """Canonical provider observation accepted by identity resolution."""

    source: str
    title: str
    programs: tuple[str, ...]
    window: DateWindow
    application_url: str | None = None
    provider_occurrence_id: str | None = None

    def __post_init__(self) -> None:
        if self.source != normalize_source(self.source):
            raise DomainValidationError("source must already be canonical")
        if self.title != normalize_text(self.title, field="title"):
            raise DomainValidationError("title must already be canonical")
        if self.programs != normalize_programs(self.programs):
            raise DomainValidationError("programs must already be canonical")
        if not isinstance(self.window, DateWindow):
            raise DomainValidationError("window must be a DateWindow")
        if self.application_url != canonicalize_application_url(self.application_url):
            raise DomainValidationError("application_url must already be canonical")
        if self.provider_occurrence_id != normalize_provider_occurrence_id(
            self.provider_occurrence_id
        ):
            raise DomainValidationError(
                "provider_occurrence_id must already be canonical"
            )

    @classmethod
    def normalize(
        cls,
        *,
        source: str,
        title: str,
        programs: str | Iterable[str],
        start_date: date | str,
        end_date: date | str,
        application_url: str | None = None,
        provider_occurrence_id: str | None = None,
    ) -> GrantCandidate:
        """Normalize a raw provider record into a domain candidate."""
        return cls(
            source=normalize_source(source),
            title=normalize_text(title, field="title"),
            programs=normalize_programs(programs),
            window=DateWindow.normalize(start_date, end_date),
            application_url=canonicalize_application_url(application_url),
            provider_occurrence_id=normalize_provider_occurrence_id(
                provider_occurrence_id
            ),
        )


@dataclass(frozen=True, slots=True)
class GrantOccurrence:
    """Identity-bearing grant occurrence projection used by the resolver."""

    occurrence_id: int | None
    source: str
    source_key: str
    identity_version: int
    title: str
    programs: tuple[str, ...]
    window: DateWindow
    application_url: str | None
    aliases: tuple[IdentityAlias, ...]

    def __post_init__(self) -> None:
        if self.occurrence_id is not None and (
            isinstance(self.occurrence_id, bool)
            or not isinstance(self.occurrence_id, int)
            or self.occurrence_id <= 0
        ):
            raise DomainValidationError("occurrence_id must be a positive integer")
        if self.source != normalize_source(self.source):
            raise DomainValidationError("source must already be canonical")
        if not _SOURCE_KEY.fullmatch(self.source_key):
            raise DomainValidationError(
                "source_key must be versioned or legacy identity"
            )
        if isinstance(self.identity_version, bool) or self.identity_version < 1:
            raise DomainValidationError("identity_version must be a positive integer")
        if self.title != normalize_text(self.title, field="title"):
            raise DomainValidationError("title must already be canonical")
        if self.programs != normalize_programs(self.programs):
            raise DomainValidationError("programs must already be canonical")
        if not isinstance(self.window, DateWindow):
            raise DomainValidationError("window must be a DateWindow")
        if self.application_url != canonicalize_application_url(self.application_url):
            raise DomainValidationError("application_url must already be canonical")
        if not self.aliases:
            raise DomainValidationError(
                "an occurrence requires at least one identity alias"
            )
        if any(alias.source != self.source for alias in self.aliases):
            raise DomainValidationError("all occurrence aliases must use its source")
        if len(set(self.aliases)) != len(self.aliases):
            raise DomainValidationError("occurrence aliases must be unique")

    @classmethod
    def from_candidate(
        cls,
        candidate: GrantCandidate,
        *,
        source_key: str,
        identity_version: int,
        aliases: Iterable[IdentityAlias],
    ) -> GrantOccurrence:
        """Create a not-yet-persisted occurrence from a resolved candidate."""
        return cls(
            occurrence_id=None,
            source=candidate.source,
            source_key=source_key,
            identity_version=identity_version,
            title=candidate.title,
            programs=candidate.programs,
            window=candidate.window,
            application_url=candidate.application_url,
            aliases=tuple(aliases),
        )

    def record_observation(
        self,
        candidate: GrantCandidate,
        aliases: Iterable[IdentityAlias],
    ) -> GrantOccurrence:
        """Update mutable metadata without changing durable occurrence identity."""
        if candidate.source != self.source:
            raise DomainValidationError("candidate source must match occurrence source")
        combined_aliases = tuple(dict.fromkeys((*self.aliases, *tuple(aliases))))
        return replace(
            self,
            title=candidate.title,
            programs=candidate.programs,
            window=candidate.window,
            application_url=candidate.application_url,
            aliases=combined_aliases,
        )
