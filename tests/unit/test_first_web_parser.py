from pathlib import Path

from adapters.first_web.parser import parse_grants

FIXTURES = Path(__file__).parent.parent / "fixtures" / "first"


def load_fixture(name: str) -> str:
    """Load a FIRST provider HTML fixture."""
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parses_active_frc_grant_into_typed_candidate():
    candidates = parse_grants(load_fixture("active-frc.html"))

    assert len(candidates) == 1

    candidate = candidates[0]

    assert candidate.source == "first"
    assert candidate.title == "Active FRC Grant"
    assert candidate.programs == ("FRC",)
    assert candidate.window.start.isoformat() == "2026-08-01"
    assert candidate.window.end.isoformat() == "2026-09-30"
    assert candidate.application_url == "https://example.com/apply"


def test_ignores_non_frc_grants():
    candidates = parse_grants(load_fixture("non-frc.html"))

    assert candidates == []


def test_skips_card_with_malformed_date():
    candidates = parse_grants(load_fixture("malformed-date.html"))

    assert candidates == []


def test_returns_empty_list_for_empty_provider_page():
    candidates = parse_grants(load_fixture("empty.html"))

    assert candidates == []


def test_parses_relative_application_url():
    candidates = parse_grants(load_fixture("relative-url.html"))

    assert len(candidates) == 1

    assert (
        candidates[0].application_url
        == "https://www.firstinspires.org/grants/test/apply"
    )


def test_card_without_details_is_still_parsed():
    candidates = parse_grants(load_fixture("missing-details.html"))

    assert len(candidates) == 1
    assert candidates[0].application_url is None


def test_one_malformed_card_does_not_abort_other_valid_cards():
    candidates = parse_grants(load_fixture("mixed-valid-malformed.html"))

    assert len(candidates) == 1

    candidate = candidates[0]

    assert candidate.title == "Valid FRC Grant"
    assert candidate.source == "first"
    assert candidate.programs == ("FRC",)
