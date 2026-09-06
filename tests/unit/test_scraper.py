from datetime import date
from unittest.mock import patch

from adapters.first_web.client import FirstWebFetchResult
from adapters.first_web.errors import (
    FirstWebRequestError,
    FirstWebTimeoutError,
)
from domain.grants import GrantCandidate
from scraper import Scraper


def make_candidate(
    title: str,
    start_date: date,
    end_date: date,
    application_url: str | None = None,
) -> GrantCandidate:
    return GrantCandidate.normalize(
        source="first",
        title=title,
        programs=("FRC",),
        start_date=start_date,
        end_date=end_date,
        application_url=application_url,
    )


def make_fetch_result(
    html: str = "<html></html>",
    latency_seconds: float = 0.123,
) -> FirstWebFetchResult:
    return FirstWebFetchResult(
        html=html,
        latency_seconds=latency_seconds,
    )


@patch("scraper.parse_grants")
@patch("scraper.FirstWebClient")
def test_scraper_returns_only_active_grants(
    mock_client_class,
    mock_parse_grants,
):
    active_grant = make_candidate(
        "Active Grant",
        date(2026, 1, 1),
        date(2026, 12, 31),
        "https://example.com/active",
    )

    expired_grant = make_candidate(
        "Expired Grant",
        date(2025, 1, 1),
        date(2025, 12, 31),
        "https://example.com/expired",
    )

    mock_client = mock_client_class.return_value
    mock_client.fetch.return_value = make_fetch_result()

    mock_parse_grants.return_value = [
        active_grant,
        expired_grant,
    ]

    with patch("scraper.datetime") as mock_datetime:
        mock_datetime.now.return_value.date.return_value = date(2026, 6, 1)

        grants = Scraper.scrape()

    assert grants == [
        {
            "title": "Active Grant",
            "start_date": active_grant.window.start,
            "end_date": active_grant.window.end,
            "url": "https://example.com/active",
        }
    ]


@patch("scraper.parse_grants")
@patch("scraper.FirstWebClient")
def test_scraper_returns_legacy_dict_format(
    mock_client_class,
    mock_parse_grants,
):
    candidate = make_candidate(
        "Test Grant",
        date(2026, 1, 1),
        date(2026, 12, 31),
        "https://example.com/apply",
    )

    mock_client = mock_client_class.return_value
    mock_client.fetch.return_value = make_fetch_result()

    mock_parse_grants.return_value = [candidate]

    with patch("scraper.datetime") as mock_datetime:
        mock_datetime.now.return_value.date.return_value = date(2026, 6, 1)

        grants = Scraper.scrape()

    assert isinstance(grants, list)
    assert isinstance(grants[0], dict)

    assert grants[0]["title"] == "Test Grant"
    assert grants[0]["start_date"] == date(2026, 1, 1)
    assert grants[0]["end_date"] == date(2026, 12, 31)
    assert grants[0]["url"] == "https://example.com/apply"


@patch("scraper.FirstWebClient")
def test_scraper_returns_none_on_timeout(
    mock_client_class,
):
    mock_client = mock_client_class.return_value

    mock_client.fetch.side_effect = FirstWebTimeoutError(
        "FIRST provider request timed out"
    )

    grants = Scraper.scrape()

    assert grants is None


@patch("scraper.FirstWebClient")
def test_scraper_returns_none_on_request_error(
    mock_client_class,
):
    mock_client = mock_client_class.return_value

    mock_client.fetch.side_effect = FirstWebRequestError(
        "FIRST provider request failed"
    )

    grants = Scraper.scrape()

    assert grants is None


@patch("scraper.parse_grants")
@patch("scraper.FirstWebClient")
def test_scraper_removes_duplicate_grants(
    mock_client_class,
    mock_parse_grants,
):
    candidate = make_candidate(
        "Duplicate Grant",
        date(2026, 1, 1),
        date(2026, 12, 31),
        "https://example.com/apply",
    )

    mock_client = mock_client_class.return_value
    mock_client.fetch.return_value = make_fetch_result()

    mock_parse_grants.return_value = [
        candidate,
        candidate,
    ]

    with patch("scraper.datetime") as mock_datetime:
        mock_datetime.now.return_value.date.return_value = date(2026, 6, 1)

        grants = Scraper.scrape()

    assert len(grants) == 1
    assert grants[0]["title"] == "Duplicate Grant"
