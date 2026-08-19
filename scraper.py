"""
Web scraper for FIRST Robotics grant opportunities
"""
import requests
from bs4 import BeautifulSoup
from config import config


class Scraper:
    """FIRST website scraper"""
    
    KEYWORDS = [
        "grant", "team", "first", "opportunity",
        "funding", "frc", "scholarship", "award"
    ]
    
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    
    @staticmethod
    def scrape() -> list:
        """Scrape grants from FIRST website"""
        try:
            print(f"🔍 Scraping {config.GRANT_URL}...")
            
            response = requests.get(
                config.GRANT_URL,
                headers=Scraper.HEADERS,
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            raw_texts = []

            # Extract text from relevant elements
            for element in soup.select("h1, h2, h3, h4, .field-content, p, a, .opportunity"):
                text = element.get_text(strip=True)
                # Normalize whitespace so the same content scraped with
                # slightly different spacing doesn't count as a "new" grant.
                text = " ".join(text.split())

                # Filter by content
                if text and 15 < len(text) < 500:
                    if any(kw in text.lower() for kw in Scraper.KEYWORDS):
                        raw_texts.append(text)

            # Remove exact duplicates first
            candidates = list(set(raw_texts))

            # Remove near-duplicates: our selector list overlaps on purpose
            # (e.g. a heading AND the link inside it both match), so the same
            # grant can be captured twice with slightly different text. If
            # one captured text is fully contained inside a longer captured
            # text, keep only the longer one.
            candidates.sort(key=len, reverse=True)
            grants = []
            for text in candidates:
                if not any(text in kept for kept in grants):
                    grants.append(text)

            print(f"✅ Scraped {len(grants)} unique grants")
            return grants
            
        except requests.exceptions.Timeout:
            print("❌ Scraper timeout")
            return []
        except Exception as e:
            print(f"❌ Scraper error: {e}")
            return []