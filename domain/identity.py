"""Versioned grant occurrence alias generation and resolution policy."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from domain.grants import (
    DomainValidationError,
    GrantCandidate,
    GrantOccurrence,
    normalize_source,
)

IDENTITY_VERSION = 1
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class AliasKind(str, Enum):
    """Provider-scoped kinds of identity evidence."""

    PROVIDER_ID = "provider_id"
    APPLICATION_LOCATOR = "application_locator"
    OBSERVATION_FINGERPRINT = "observation_fingerprint"
    LEGACY_ID = "legacy_id"


@dataclass(frozen=True, slots=True, order=True)
class IdentityAlias:
    """A versioned, hashed, provider-scoped identity claim."""

    source: str
    kind: AliasKind
    version: int
    digest: str

    @property
    def alias_kind(self) -> str:
        """Persistence-facing alias kind value."""
        return self.kind.value

    @property
    def alias_version(self) -> int:
        """Persistence-facing normalization version."""
        return self.version

    @property
    def alias_hash(self) -> str:
        """Persistence-facing lowercase SHA-256 value."""
        return self.digest

    def __post_init__(self) -> None:
        if self.source != normalize_source(self.source):
            raise DomainValidationError("alias source must already be canonical")
        if not isinstance(self.kind, AliasKind):
            raise DomainValidationError("alias kind is invalid")
        if isinstance(self.version, bool) or self.version < 1:
            raise DomainValidationError("alias version must be a positive integer")
        if not _SHA256.fullmatch(self.digest):
            raise DomainValidationError("alias digest must be lowercase SHA-256 hex")


class ResolutionAction(str, Enum):
    """Persistence action required by an identity decision."""

    USE_EXISTING = "use_existing"
    CREATE_NEW = "create_new"
    CREATE_NEW_WITH_CONFLICT = "create_new_with_conflict"
    CONFLICT = "conflict"


class ResolutionReason(str, Enum):
    """Evidence responsible for a resolution decision."""

    PROVIDER_ID = "provider_id"
    OBSERVATION_FINGERPRINT = "observation_fingerprint"
    APPLICATION_CONTINUITY = "application_continuity"
    NO_MATCH = "no_match"
    AMBIGUOUS_APPLICATION = "ambiguous_application"
    CONFLICTING_STRONG_EVIDENCE = "conflicting_strong_evidence"


@dataclass(frozen=True, slots=True)
class IdentityConflict:
    """Structured conflict suitable for logs, metrics, or manual review."""

    reason: ResolutionReason
    candidate_source_key: str
    competing_occurrence_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ResolutionDecision:
    """Pure result of resolving one candidate against stored occurrences."""

    action: ResolutionAction
    reason: ResolutionReason
    occurrence: GrantOccurrence | None
    aliases_to_attach: tuple[IdentityAlias, ...] = ()
    conflict: IdentityConflict | None = None

    def __post_init__(self) -> None:
        creates = {
            ResolutionAction.CREATE_NEW,
            ResolutionAction.CREATE_NEW_WITH_CONFLICT,
        }
        if self.action in creates and (
            self.occurrence is None or self.occurrence.occurrence_id is not None
        ):
            raise DomainValidationError("create decisions require a new occurrence")
        if self.action is ResolutionAction.USE_EXISTING and (
            self.occurrence is None or self.occurrence.occurrence_id is None
        ):
            raise DomainValidationError("match decisions require a stored occurrence")
        if self.action is ResolutionAction.CONFLICT and self.occurrence is not None:
            raise DomainValidationError(
                "unresolvable conflicts cannot select an occurrence"
            )
        has_conflict = self.conflict is not None
        expects_conflict = self.action in {
            ResolutionAction.CREATE_NEW_WITH_CONFLICT,
            ResolutionAction.CONFLICT,
        }
        if has_conflict != expects_conflict:
            raise DomainValidationError(
                "conflict payload does not match resolution action"
            )


def _canonical_digest(payload: object) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _alias(
    candidate: GrantCandidate, kind: AliasKind, payload: object
) -> IdentityAlias:
    return IdentityAlias(
        source=candidate.source,
        kind=kind,
        version=IDENTITY_VERSION,
        digest=_canonical_digest(payload),
    )


def generate_identity_aliases(
    candidate: GrantCandidate,
) -> tuple[IdentityAlias, ...]:
    """Generate v1 aliases in strongest-to-weakest order.

    Human-readable text is case-folded only in hash input.  Canonical display
    values on the candidate retain their case.
    """
    common = {"source": candidate.source}
    aliases: list[IdentityAlias] = []
    if candidate.provider_occurrence_id is not None:
        aliases.append(
            _alias(
                candidate,
                AliasKind.PROVIDER_ID,
                {
                    **common,
                    "provider_occurrence_id": (
                        candidate.provider_occurrence_id.casefold()
                    ),
                },
            )
        )
    if candidate.application_url is not None:
        aliases.append(
            _alias(
                candidate,
                AliasKind.APPLICATION_LOCATOR,
                {
                    **common,
                    "application_locator": candidate.application_url,
                    "programs": list(candidate.programs),
                },
            )
        )
    aliases.append(
        _alias(
            candidate,
            AliasKind.OBSERVATION_FINGERPRINT,
            {
                **common,
                "title": candidate.title.casefold(),
                "programs": list(candidate.programs),
                "start_date": candidate.window.start.isoformat(),
                "end_date": candidate.window.end.isoformat(),
            },
        )
    )
    return tuple(aliases)


def source_key_for(candidate: GrantCandidate) -> str:
    """Derive an immutable key from the strongest initial unique alias."""
    aliases = generate_identity_aliases(candidate)
    strongest = next(
        alias
        for alias in aliases
        if alias.kind in {AliasKind.PROVIDER_ID, AliasKind.OBSERVATION_FINGERPRINT}
    )
    return f"v{IDENTITY_VERSION}:{strongest.digest}"


def _owners(
    alias: IdentityAlias | None,
    occurrences: tuple[GrantOccurrence, ...],
) -> tuple[GrantOccurrence, ...]:
    if alias is None:
        return ()
    return tuple(
        occurrence for occurrence in occurrences if alias in occurrence.aliases
    )


def _owner_ids(occurrences: Iterable[GrantOccurrence]) -> tuple[int, ...]:
    ids = {
        occurrence.occurrence_id
        for occurrence in occurrences
        if occurrence.occurrence_id is not None
    }
    return tuple(sorted(ids))


def _new_occurrence(
    candidate: GrantCandidate,
    aliases: tuple[IdentityAlias, ...],
) -> GrantOccurrence:
    return GrantOccurrence.from_candidate(
        candidate,
        source_key=source_key_for(candidate),
        identity_version=IDENTITY_VERSION,
        aliases=aliases,
    )


def _matched(
    occurrence: GrantOccurrence,
    candidate: GrantCandidate,
    aliases: tuple[IdentityAlias, ...],
    reason: ResolutionReason,
) -> ResolutionDecision:
    new_aliases = tuple(alias for alias in aliases if alias not in occurrence.aliases)
    return ResolutionDecision(
        action=ResolutionAction.USE_EXISTING,
        reason=reason,
        occurrence=occurrence.record_observation(candidate, aliases),
        aliases_to_attach=new_aliases,
    )


def _strong_conflict(
    source_key: str,
    occurrences: Iterable[GrantOccurrence],
) -> ResolutionDecision:
    conflict = IdentityConflict(
        reason=ResolutionReason.CONFLICTING_STRONG_EVIDENCE,
        candidate_source_key=source_key,
        competing_occurrence_ids=_owner_ids(occurrences),
    )
    return ResolutionDecision(
        action=ResolutionAction.CONFLICT,
        reason=conflict.reason,
        occurrence=None,
        conflict=conflict,
    )


def resolve_occurrence(
    candidate: GrantCandidate,
    occurrences: Iterable[GrantOccurrence],
) -> ResolutionDecision:
    """Apply identity resolution v1 without I/O or persistence side effects."""
    candidates = tuple(
        occurrence
        for occurrence in occurrences
        if occurrence.source == candidate.source
    )
    if any(occurrence.occurrence_id is None for occurrence in candidates):
        raise DomainValidationError("resolution requires persisted occurrences")

    aliases = generate_identity_aliases(candidate)
    source_key = source_key_for(candidate)
    provider_alias = next(
        (alias for alias in aliases if alias.kind is AliasKind.PROVIDER_ID),
        None,
    )
    observation_alias = next(
        alias for alias in aliases if alias.kind is AliasKind.OBSERVATION_FINGERPRINT
    )
    application_alias = next(
        (alias for alias in aliases if alias.kind is AliasKind.APPLICATION_LOCATOR),
        None,
    )

    provider_owners = _owners(provider_alias, candidates)
    observation_owners = _owners(observation_alias, candidates)
    strong_owners = {*provider_owners, *observation_owners}
    if len(provider_owners) > 1 or len(observation_owners) > 1:
        return _strong_conflict(source_key, strong_owners)
    if provider_owners:
        provider_owner = provider_owners[0]
        if observation_owners and observation_owners[0] != provider_owner:
            return _strong_conflict(source_key, strong_owners)
        return _matched(
            provider_owner,
            candidate,
            aliases,
            ResolutionReason.PROVIDER_ID,
        )
    if observation_owners:
        return _matched(
            observation_owners[0],
            candidate,
            aliases,
            ResolutionReason.OBSERVATION_FINGERPRINT,
        )

    continuity_matches = tuple(
        occurrence
        for occurrence in _owners(application_alias, candidates)
        if occurrence.programs == candidate.programs
        and occurrence.window.overlaps(candidate.window)
    )
    if len(continuity_matches) == 1:
        return _matched(
            continuity_matches[0],
            candidate,
            aliases,
            ResolutionReason.APPLICATION_CONTINUITY,
        )
    occurrence = _new_occurrence(candidate, aliases)
    if len(continuity_matches) > 1:
        conflict = IdentityConflict(
            reason=ResolutionReason.AMBIGUOUS_APPLICATION,
            candidate_source_key=source_key,
            competing_occurrence_ids=_owner_ids(continuity_matches),
        )
        return ResolutionDecision(
            action=ResolutionAction.CREATE_NEW_WITH_CONFLICT,
            reason=conflict.reason,
            occurrence=occurrence,
            conflict=conflict,
        )
    return ResolutionDecision(
        action=ResolutionAction.CREATE_NEW,
        reason=ResolutionReason.NO_MATCH,
        occurrence=occurrence,
    )
