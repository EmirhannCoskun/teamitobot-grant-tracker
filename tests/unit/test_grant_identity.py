from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

from domain.grants import (
    DateWindow,
    DomainValidationError,
    GrantCandidate,
    GrantOccurrence,
    canonicalize_application_url,
)
from domain.identity import (
    AliasKind,
    ResolutionAction,
    ResolutionReason,
    generate_identity_aliases,
    resolve_occurrence,
    source_key_for,
)


def candidate(**overrides: object) -> GrantCandidate:
    values: dict[str, object] = {
        "source": "first-team-grants",
        "title": "John Deere Team Grant",
        "programs": ["FIRST Robotics Competition"],
        "start_date": "2026-08-01",
        "end_date": "2026-09-30",
        "application_url": "https://Apply.Example/forms/season?id=42&utm_source=x#top",
    }
    values.update(overrides)
    return GrantCandidate.normalize(**values)  # type: ignore[arg-type]


def stored(
    item: GrantCandidate,
    occurrence_id: int,
    *,
    aliases=None,
    source_key: str | None = None,
) -> GrantOccurrence:
    item_aliases = generate_identity_aliases(item) if aliases is None else aliases
    return replace(
        GrantOccurrence.from_candidate(
            item,
            source_key=source_key or source_key_for(item),
            identity_version=1,
            aliases=item_aliases,
        ),
        occurrence_id=occurrence_id,
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Acme\tGrant\n2026  ", "Acme Grant 2026"),
        ("ＡＣＭＥ Grant", "ACME Grant"),
        ("Café Grant", "Café Grant"),
    ],
)
def test_unicode_and_whitespace_normalization(raw: str, expected: str) -> None:
    assert candidate(title=raw).title == expected


@pytest.mark.parametrize(
    ("raw_programs", "expected"),
    [
        ("FRC", ("FRC",)),
        ("first robotics competition", ("FRC",)),
        (["FTC", "FRC", "frc"], ("FRC", "FTC")),
    ],
)
def test_program_normalization(raw_programs, expected: tuple[str, ...]) -> None:
    assert candidate(programs=raw_programs).programs == expected


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (date(2026, 8, 1), date(2026, 9, 30)),
        ("2026-08-01", "2026-09-30"),
    ],
)
def test_date_normalization(start, end) -> None:
    item = candidate(start_date=start, end_date=end)
    assert item.window == DateWindow(date(2026, 8, 1), date(2026, 9, 30))


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("08/01/2026", "2026-09-30"),
        ("2026-10-01", "2026-09-30"),
        (datetime(2026, 8, 1, tzinfo=timezone.utc), date(2026, 9, 30)),
    ],
)
def test_invalid_date_windows_are_rejected(start, end) -> None:
    with pytest.raises(DomainValidationError):
        candidate(start_date=start, end_date=end)


def test_date_window_overlap_is_inclusive() -> None:
    first = DateWindow.normalize("2026-01-01", "2026-01-31")
    touching = DateWindow.normalize("2026-01-31", "2026-02-20")
    later = DateWindow.normalize("2026-02-01", "2026-02-20")

    assert first.overlaps(touching)
    assert not first.overlaps(later)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "HTTPS://EXAMPLE.COM:443/forms/apply?formId=ABC&utm_medium=email#go",
            "https://example.com/forms/apply?formId=ABC",
        ),
        (
            "http://example.com:80?grant=7&fbclid=tracker",
            "http://example.com/?grant=7",
        ),
        (
            "https://example.com/Form/CaseSensitive?form=One&step=2",
            "https://example.com/Form/CaseSensitive?form=One&step=2",
        ),
    ],
)
def test_application_url_normalization(raw: str, expected: str) -> None:
    assert canonicalize_application_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["/relative", "javascript:alert(1)", "https://user:secret@example.com/form"],
)
def test_unsafe_or_non_absolute_application_url_is_rejected(raw: str) -> None:
    with pytest.raises(DomainValidationError):
        candidate(application_url=raw)


def test_title_only_candidate_is_rejected() -> None:
    with pytest.raises(DomainValidationError, match="program"):
        candidate(programs=[])


@pytest.mark.parametrize("html_id", ["grant-details-12", "grant_detail_8", "details9"])
def test_positional_html_id_is_rejected_as_provider_identity(html_id: str) -> None:
    with pytest.raises(DomainValidationError, match="positional HTML"):
        candidate(provider_occurrence_id=html_id)


def test_aliases_are_versioned_deterministic_and_casefold_human_text() -> None:
    mixed_case = candidate(
        title="Boeing TEAM Grant",
        provider_occurrence_id="OCC-2026-A",
    )
    lower_case = candidate(
        title="boeing team grant",
        provider_occurrence_id="occ-2026-a",
    )

    assert generate_identity_aliases(mixed_case) == generate_identity_aliases(
        lower_case
    )
    assert all(alias.version == 1 for alias in generate_identity_aliases(mixed_case))
    assert source_key_for(mixed_case).startswith("v1:")
    assert mixed_case.title == "Boeing TEAM Grant"


def test_v1_alias_hash_contract_has_stable_vectors() -> None:
    item = candidate(provider_occurrence_id="FIRST-2026-42")

    aliases = generate_identity_aliases(item)

    assert [(alias.kind.value, alias.version, alias.digest) for alias in aliases] == [
        (
            "provider_id",
            1,
            "ee3e6eb06f410cedb8970028dd0db150369869eb2e01b253590c31fb88f712f9",
        ),
        (
            "application_locator",
            1,
            "2f71155a7dfdbc8bdb5ea938556a242136cecbb48fe3fd5c0821df31aabf58a7",
        ),
        (
            "observation_fingerprint",
            1,
            "d161aee4cb6eb4559abb45f4f24b40c617bce7dd4740bb084e0250cc28bd3e49",
        ),
    ]
    assert source_key_for(item) == (
        "v1:ee3e6eb06f410cedb8970028dd0db150369869eb2e01b253590c31fb88f712f9"
    )


def test_exact_replay_resolves_idempotently() -> None:
    item = candidate()
    existing = stored(item, 41)

    decision = resolve_occurrence(item, [existing])

    assert decision.action is ResolutionAction.USE_EXISTING
    assert decision.reason is ResolutionReason.OBSERVATION_FINGERPRINT
    assert decision.occurrence == existing
    assert decision.aliases_to_attach == ()


def test_stable_provider_id_supports_metadata_correction() -> None:
    original = candidate(provider_occurrence_id="FIRST-2026-42")
    existing = stored(original, 42)
    corrected = candidate(
        provider_occurrence_id="first-2026-42",
        title="Corrected display title",
        start_date="2026-08-05",
        end_date="2026-10-02",
        application_url="https://apply.example/forms/corrected?id=77",
    )

    decision = resolve_occurrence(corrected, [existing])

    assert decision.action is ResolutionAction.USE_EXISTING
    assert decision.reason is ResolutionReason.PROVIDER_ID
    assert decision.occurrence is not None
    assert decision.occurrence.occurrence_id == 42
    assert decision.occurrence.source_key == existing.source_key
    assert decision.occurrence.title == "Corrected display title"
    assert decision.aliases_to_attach


def test_unique_overlapping_application_locator_supports_continuity_update() -> None:
    original = candidate(title="Original title")
    existing = stored(original, 71)
    renamed = candidate(
        title="Renamed grant",
        start_date="2026-09-15",
        end_date="2026-10-15",
    )

    decision = resolve_occurrence(renamed, [existing])

    assert decision.action is ResolutionAction.USE_EXISTING
    assert decision.reason is ResolutionReason.APPLICATION_CONTINUITY
    assert decision.occurrence is not None
    assert decision.occurrence.occurrence_id == 71
    assert decision.occurrence.source_key == existing.source_key


def test_shared_application_url_does_not_cross_programs() -> None:
    # Sanitized regression of the observed BAE case: one application form was
    # exposed for distinct program-scoped opportunities.  URL alone must not
    # collapse those occurrences.
    bae_url = "https://forms.benevity.org/66a3c657-4e6e-4c72-a1ae-4b11d1e8e605"
    frc = candidate(
        title="BAE Systems, Inc. FRC Grant FY26",
        programs="FRC",
        application_url=bae_url,
    )
    ftc = candidate(
        title="BAE Systems FTC Grant FY26",
        programs="FTC",
        application_url=bae_url,
    )

    decision = resolve_occurrence(ftc, [stored(frc, 1)])

    assert decision.action is ResolutionAction.CREATE_NEW
    assert decision.reason is ResolutionReason.NO_MATCH


def test_non_overlapping_annual_recurrence_creates_distinct_occurrence() -> None:
    season_2026 = candidate()
    season_2027 = candidate(
        start_date="2027-08-01",
        end_date="2027-09-30",
    )

    decision = resolve_occurrence(season_2027, [stored(season_2026, 2026)])

    assert decision.action is ResolutionAction.CREATE_NEW
    assert decision.occurrence is not None
    assert decision.occurrence.occurrence_id is None
    assert decision.occurrence.source_key != source_key_for(season_2026)


def test_ambiguous_application_match_creates_distinct_occurrence_and_conflict() -> None:
    first = candidate(title="Earlier observation", start_date="2026-07-01")
    second = candidate(title="Another observation", end_date="2026-10-30")
    incoming = candidate(title="New provider wording")

    decision = resolve_occurrence(
        incoming,
        [stored(first, 10), stored(second, 20)],
    )

    assert decision.action is ResolutionAction.CREATE_NEW_WITH_CONFLICT
    assert decision.reason is ResolutionReason.AMBIGUOUS_APPLICATION
    assert decision.occurrence is not None
    assert decision.occurrence.occurrence_id is None
    assert decision.conflict is not None
    assert decision.conflict.competing_occurrence_ids == (10, 20)


def test_conflicting_strong_aliases_never_silently_merge() -> None:
    provider_observation = candidate(
        title="Provider owner",
        provider_occurrence_id="stable-7",
    )
    fingerprint_observation = candidate(
        title="Fingerprint owner",
        provider_occurrence_id=None,
    )
    incoming = candidate(
        title="Fingerprint owner",
        provider_occurrence_id="stable-7",
    )
    provider_alias = next(
        alias
        for alias in generate_identity_aliases(provider_observation)
        if alias.kind is AliasKind.PROVIDER_ID
    )
    fingerprint_alias = next(
        alias
        for alias in generate_identity_aliases(fingerprint_observation)
        if alias.kind is AliasKind.OBSERVATION_FINGERPRINT
    )
    owner_one = stored(provider_observation, 1, aliases=(provider_alias,))
    owner_two = stored(fingerprint_observation, 2, aliases=(fingerprint_alias,))

    decision = resolve_occurrence(incoming, [owner_one, owner_two])

    assert decision.action is ResolutionAction.CONFLICT
    assert decision.reason is ResolutionReason.CONFLICTING_STRONG_EVIDENCE
    assert decision.occurrence is None
    assert decision.conflict is not None
    assert decision.conflict.competing_occurrence_ids == (1, 2)


def test_occurrences_from_other_sources_never_match() -> None:
    first = candidate()
    other = candidate(source="another-provider")

    decision = resolve_occurrence(other, [stored(first, 1)])

    assert decision.action is ResolutionAction.CREATE_NEW
