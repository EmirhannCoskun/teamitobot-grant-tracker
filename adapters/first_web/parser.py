"""Parser for FIRST grant opportunity pages.

This module is intentionally pure: it does not depend on application config,
network clients, or global state. It converts provider HTML into typed
GrantCandidate values.
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from domain.grants import GrantCandidate

FIRST_BASE_URL = "https://www.firstinspires.org"


def parse_grants(html: str) -> list[GrantCandidate]:
    """Parse FIRST grant cards into typed GrantCandidate values.

    A malformed card is skipped without preventing other valid cards from
    being parsed.
    """

    soup = BeautifulSoup(html, "html.parser")
    candidates: list[GrantCandidate] = []

    for card in soup.select(".card-header"):
        try:
            candidate = _parse_card(card, soup)

            if candidate is not None:
                candidates.append(candidate)

        except (ValueError, TypeError):
            # One malformed provider card must not invalidate other cards.
            continue

    return candidates


def _parse_card(card, soup: BeautifulSoup) -> GrantCandidate | None:
    """Parse one provider grant card."""

    title_element = card.select_one("h3.grant-name")

    if title_element is None:
        return None

    title = " ".join(title_element.stripped_strings)

    if not title:
        return None

    frc_program = card.select_one(".grant-programs .program-tag.frc")

    if frc_program is None:
        return None

    start_date, end_date = _parse_dates(card)

    if start_date is None or end_date is None:
        return None

    application_url = _parse_application_url(card, soup)

    return GrantCandidate.normalize(
        source="first",
        title=title,
        programs=("FRC",),
        start_date=start_date,
        end_date=end_date,
        application_url=application_url,
    )


def _parse_dates(card) -> tuple[object | None, object | None]:
    """Extract the start and end dates from a grant card."""

    start_date = None
    end_date = None

    for date_item in card.select(".grant-dates .date-item"):
        text = " ".join(date_item.stripped_strings)

        if text.startswith("Start:"):
            raw_date = text.removeprefix("Start:").strip()
            start_date = _parse_date(raw_date)

        elif text.startswith("End:"):
            raw_date = text.removeprefix("End:").strip()
            end_date = _parse_date(raw_date)

    return start_date, end_date


def _parse_date(value: str):
    """Parse FIRST's provider date format."""

    try:
        return datetime.strptime(value, "%m/%d/%Y").date()
    except ValueError:
        return None


def _parse_application_url(card, soup: BeautifulSoup) -> str | None:
    """Extract and normalize the application URL."""

    details_button = card.select_one(".grant-details-toggle[aria-controls]")

    if details_button is None:
        return None

    details_id = details_button.get("aria-controls")

    if not details_id:
        return None

    details = soup.select_one(f"#{details_id}")

    if details is None:
        return None

    apply_link = details.select_one("a.grant-apply-btn[href]")

    if apply_link is None:
        return None

    href = apply_link.get("href")

    if not href:
        return None

    return urljoin(FIRST_BASE_URL, href)
