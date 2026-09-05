"""Pure domain model for grant discovery and identity."""

from domain.grants import (
    DateWindow,
    DomainValidationError,
    GrantCandidate,
    GrantOccurrence,
)
from domain.identity import (
    IDENTITY_VERSION,
    AliasKind,
    IdentityAlias,
    IdentityConflict,
    ResolutionAction,
    ResolutionDecision,
    ResolutionReason,
    generate_identity_aliases,
    resolve_occurrence,
    source_key_for,
)

__all__ = [
    "AliasKind",
    "DateWindow",
    "DomainValidationError",
    "GrantCandidate",
    "GrantOccurrence",
    "IdentityAlias",
    "IdentityConflict",
    "IDENTITY_VERSION",
    "ResolutionAction",
    "ResolutionDecision",
    "ResolutionReason",
    "generate_identity_aliases",
    "resolve_occurrence",
    "source_key_for",
]
