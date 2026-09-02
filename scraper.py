"""
Web scraper for FIRST Robotics grant opportunities
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

from config import config

TURKEY_TZ = pytz.timezone("Europe/Istanbul")


class Scraper:
    """FIRST website scraper"""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    @staticmethod
    def scrape() -> list | None:
        """Scrape currently active FRC grants from FIRST website."""

        try:
            print(f"🔍 Scraping {config.GRANT_URL}...")

            response = requests.get(
                config.GRANT_URL,
                headers=Scraper.HEADERS,
                timeout=config.REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            grants = []
            today = datetime.now(TURKEY_TZ).date()

            # Each grant is represented by a card-header containing
            # the grant name, programs, dates and application link.
            for card in soup.select(".card-header"):

                # ------------------------------------------
                # 1. Grant name
                # ------------------------------------------

                name_element = card.select_one("h3.grant-name")

                if not name_element:
                    continue

                name = " ".join(name_element.stripped_strings)

                if not name:
                    continue

                # ------------------------------------------
                # 2. Check whether grant is for FRC
                # ------------------------------------------

                frc_program = card.select_one(".grant-programs .program-tag.frc")

                if not frc_program:
                    continue

                # ------------------------------------------
                # 3. Extract dates
                # ------------------------------------------

                date_items = card.select(".grant-dates .date-item")

                start_date = None
                end_date = None

                for date_item in date_items:

                    text = " ".join(date_item.stripped_strings)

                    if text.startswith("Start:"):
                        date_text = text.replace("Start:", "").strip()

                        try:
                            start_date = datetime.strptime(date_text, "%m/%d/%Y").date()
                        except ValueError:
                            pass

                    elif text.startswith("End:"):
                        date_text = text.replace("End:", "").strip()

                        try:
                            end_date = datetime.strptime(date_text, "%m/%d/%Y").date()
                        except ValueError:
                            pass

                # If we can't determine the dates, don't include
                # the grant. This prevents false positives.
                if not start_date or not end_date:
                    continue

                # ------------------------------------------
                # 4. Check whether grant is currently active
                # ------------------------------------------

                if not (start_date <= today <= end_date):
                    continue

                # ------------------------------------------
                # 5. Extract application URL
                # ------------------------------------------

                grant_url = None

                details_button = card.select_one(".grant-details-toggle[aria-controls]")

                if details_button:
                    details_id = details_button.get("aria-controls")

                    details = soup.select_one(f"#{details_id}")

                    if details:
                        apply_link = details.select_one("a.grant-apply-btn[href]")

                    if apply_link:
                        grant_url = apply_link.get("href")

                # Some grants may use a relative URL.
                if grant_url and grant_url.startswith("/"):
                    grant_url = f"https://www.firstinspires.org{grant_url}"

                # ------------------------------------------
                # 6. Avoid duplicate grants within one scrape
                # ------------------------------------------

                grant = {
                    "title": name,
                    "start_date": start_date,
                    "end_date": end_date,
                    "url": grant_url,
                }

                if not any(
                    existing["title"] == name
                    and existing["start_date"] == start_date
                    and existing["end_date"] == end_date
                    for existing in grants
                ):
                    grants.append(grant)

            print(f"📅 Today: {today.strftime('%Y-%m-%d')}")
            print(f"✅ Scraped {len(grants)} active FRC grants")

            for grant in grants:
                print(
                    f"   • {grant['title']} "
                    f"({grant['start_date']} → {grant['end_date']})"
                )

                if grant["url"]:
                    print(f"     🔗 {grant['url']}")

            return grants

        except requests.exceptions.Timeout:
            print("❌ Scraper timeout")
            return None

        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return None

        except Exception as e:
            print(f"❌ Scraper error: {e}")
            return None
