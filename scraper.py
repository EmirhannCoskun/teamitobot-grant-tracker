"""
Compatibility scraper facade for FIRST Robotics grant opportunities.

The FIRST provider adapter owns HTTP fetching and HTML parsing. This module
preserves the legacy Scraper interface while the rest of the application is
migrated to the new architecture.
"""

from datetime import datetime

import pytz

from adapters.first_web.client import FirstWebClient
from adapters.first_web.errors import (
    FirstWebRequestError,
    FirstWebTimeoutError,
)
from adapters.first_web.parser import parse_grants
from config import config


TURKEY_TZ = pytz.timezone("Europe/Istanbul")


class Scraper:
    """Compatibility facade for collecting active FIRST FRC grants."""

    @staticmethod
    def scrape() -> list[dict] | None:
        """Scrape currently active FRC grants using the new provider adapter."""

        try:
            print(f"🔍 Scraping {config.GRANT_URL}...")

            client = FirstWebClient(
                config.GRANT_URL,
                timeout=config.REQUEST_TIMEOUT,
            )

            fetch_result = client.fetch()
            candidates = parse_grants(fetch_result.html)

            print(
                f"⏱️ FIRST provider latency: "
                f"{fetch_result.latency_seconds:.3f}s"
            )

            today = datetime.now(TURKEY_TZ).date()

            active_candidates = [
                candidate
                for candidate in candidates
                if candidate.window.start <= today <= candidate.window.end
            ]

            grants = [
                {
                    "title": candidate.title,
                    "start_date": candidate.window.start,
                    "end_date": candidate.window.end,
                    "url": candidate.application_url,
                }
                for candidate in active_candidates
            ]

            unique_grants = []

            for grant in grants:
                if not any(
                    existing["title"] == grant["title"]
                    and existing["start_date"] == grant["start_date"]
                    and existing["end_date"] == grant["end_date"]
                    for existing in unique_grants
                ):
                    unique_grants.append(grant)

            print(f"📅 Today: {today.strftime('%Y-%m-%d')}")
            print(f"✅ Scraped {len(unique_grants)} active FRC grants")

            for grant in unique_grants:
                print(
                    f"   • {grant['title']} "
                    f"({grant['start_date']} → {grant['end_date']})"
                )

                if grant["url"]:
                    print(f"     🔗 {grant['url']}")

            return unique_grants

        except FirstWebTimeoutError:
            print("❌ Scraper timeout")
            return None

        except FirstWebRequestError as error:
            print(f"❌ Request error: {error}")
            return None

        except Exception as error:
            print(f"❌ Scraper error: {error}")
            return None