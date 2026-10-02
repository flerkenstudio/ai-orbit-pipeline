"""HackerEarth adapter — REST API scraper for hiring & coding challenges."""
import requests

from .base import BaseScraper
from ..config import REQUEST_TIMEOUT


class HackerEarthScraper(BaseScraper):
    source_name = "hackerearth"
    API_URL = "https://www.hackerearth.com/chrome-extension/events/"
    
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }

    def scrape(self) -> list:
        results = []
        try:
            resp = requests.get(self.API_URL, headers=self.HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                print(f"[hackerearth] HTTP {resp.status_code}")
                return results

            items = resp.json().get("response", [])
            for item in items:
                url = item.get("url")
                title = item.get("title")
                if not (url and title):
                    continue

                results.append({
                    "title": str(title).strip(),
                    "organiser": "HackerEarth",
                    "official_url": str(url).strip(),
                    "reg_deadline": item.get("end_timestamp"),
                    "event_date": item.get("start_timestamp"),
                    "prize_pool": "Jobs & Cash Prizes",
                    "source": self.source_name,
                    "discovery_url": "https://www.hackerearth.com/challenges/",
                    "organiser_type": "platform",
                    "type_raw": item.get("challenge_type", "coding"),
                })
        except Exception as e:
            print(f"[hackerearth] Error: {e}")

        return results
