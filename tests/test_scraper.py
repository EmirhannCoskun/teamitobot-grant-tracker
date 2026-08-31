from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "first"


def load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


@pytest.fixture
def scraper():
    with patch.dict(
        "os.environ",
        {
            "TELEGRAM_BOT_TOKEN": "123456789:TEST_TOKEN",
            "DATABASE_URL": "postgresql://test:test@localhost:5432/test",
        },
    ):
        from scraper import Scraper

        return Scraper


def mock_config(monkeypatch):
    monkeypatch.setattr(
        "scraper.config.GRANT_URL",
        "https://example.com/grants",
    )
    monkeypatch.setattr(
        "scraper.config.REQUEST_TIMEOUT",
        10,
    )


def test_active_frc_grant_is_scraped(scraper, monkeypatch):
    mock_config(monkeypatch)

    html = load_fixture("active-frc.html")

    class MockResponse:
        text = html

        def raise_for_status(self):
            pass

    with patch("scraper.requests.get", return_value=MockResponse()):
        with patch("scraper.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = date(
                2026, 9, 1
            )
            mock_datetime.strptime.side_effect = __import__(
                "datetime"
            ).datetime.strptime

            grants = scraper.scrape()

    assert grants is not None
    assert len(grants) == 1
    assert grants[0]["title"] == "Active FRC Grant"
    assert grants[0]["start_date"] == date(2026, 8, 1)
    assert grants[0]["end_date"] == date(2026, 9, 30)


def test_inactive_frc_grant_is_excluded(scraper, monkeypatch):
    mock_config(monkeypatch)

    html = load_fixture("inactive-frc.html")

    class MockResponse:
        text = html

        def raise_for_status(self):
            pass

    with patch("scraper.requests.get", return_value=MockResponse()):
        with patch("scraper.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = date(
                2026, 9, 1
            )
            mock_datetime.strptime.side_effect = __import__(
                "datetime"
            ).datetime.strptime

            grants = scraper.scrape()

    assert grants == []


def test_non_frc_grant_is_excluded(scraper, monkeypatch):
    mock_config(monkeypatch)

    html = load_fixture("non-frc.html")

    class MockResponse:
        text = html

        def raise_for_status(self):
            pass

    with patch("scraper.requests.get", return_value=MockResponse()):
        with patch("scraper.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = date(
                2026, 9, 1
            )
            mock_datetime.strptime.side_effect = __import__(
                "datetime"
            ).datetime.strptime

            grants = scraper.scrape()

    assert grants == []


def test_relative_url_is_normalized(scraper, monkeypatch):
    mock_config(monkeypatch)

    html = load_fixture("relative-url.html")

    class MockResponse:
        text = html

        def raise_for_status(self):
            pass

    with patch("scraper.requests.get", return_value=MockResponse()):
        with patch("scraper.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = date(
                2026, 9, 1
            )
            mock_datetime.strptime.side_effect = __import__(
                "datetime"
            ).datetime.strptime

            grants = scraper.scrape()

    assert len(grants) == 1
    assert grants[0]["url"].startswith(
        "https://www.firstinspires.org/"
    )


def test_duplicate_grants_are_deduplicated(scraper, monkeypatch):
    mock_config(monkeypatch)

    html = load_fixture("duplicate.html")

    class MockResponse:
        text = html

        def raise_for_status(self):
            pass

    with patch("scraper.requests.get", return_value=MockResponse()):
        with patch("scraper.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = date(
                2026, 9, 1
            )
            mock_datetime.strptime.side_effect = __import__(
                "datetime"
            ).datetime.strptime

            grants = scraper.scrape()

    assert len(grants) == 1


def test_missing_details_does_not_crash(scraper, monkeypatch):
    mock_config(monkeypatch)

    html = load_fixture("missing-details.html")

    class MockResponse:
        text = html

        def raise_for_status(self):
            pass

    with patch("scraper.requests.get", return_value=MockResponse()):
        with patch("scraper.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = date(
                2026, 9, 1
            )
            mock_datetime.strptime.side_effect = __import__(
                "datetime"
            ).datetime.strptime

            grants = scraper.scrape()

    assert len(grants) == 1
    assert grants[0]["url"] is None


def test_malformed_date_is_excluded(scraper, monkeypatch):
    mock_config(monkeypatch)

    html = load_fixture("malformed-date.html")

    class MockResponse:
        text = html

        def raise_for_status(self):
            pass

    with patch("scraper.requests.get", return_value=MockResponse()):
        with patch("scraper.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = date(
                2026, 9, 1
            )
            mock_datetime.strptime.side_effect = __import__(
                "datetime"
            ).datetime.strptime

            grants = scraper.scrape()

    assert grants == []


def test_empty_page_returns_empty_list(scraper, monkeypatch):
    mock_config(monkeypatch)

    html = load_fixture("empty.html")

    class MockResponse:
        text = html

        def raise_for_status(self):
            pass

    with patch("scraper.requests.get", return_value=MockResponse()):
        with patch("scraper.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = date(
                2026, 9, 1
            )

            grants = scraper.scrape()

    assert grants == []


def test_network_error_returns_none(scraper, monkeypatch):
    mock_config(monkeypatch)

    with patch(
        "scraper.requests.get",
        side_effect=__import__("requests").exceptions.Timeout(),
    ):
        grants = scraper.scrape()

    assert grants is None