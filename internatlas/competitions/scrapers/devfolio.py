"""Devfolio adapter — Fast & reliable REST API scraper.
Fetches open and upcoming hackathons directly from Devfolio API."""
import requests

from .base import BaseScraper
from ..config import REQUEST_TIMEOUT


class DevfolioScraper(BaseScraper):
    source_name = "devfolio"
    API_URL = "https://api.devfolio.co/api/search/hackathons"
    
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    TYPES = ["application_open", "upcoming"]

    def scrape(self) -> list:
        results = []
        seen_slugs = set()

        for t in self.TYPES:
            try:
                payload = {"type": t, "from": 0, "size": 50}
                resp = requests.post(
                    self.API_URL,
                    json=payload,
                    headers=self.HEADERS,
                    timeout=REQUEST_TIMEOUT,
                )
                if resp.status_code != 200:
                    print(f"[devfolio] HTTP {resp.status_code} for type {t}")
                    continue

                hits = resp.json().get("hits", {}).get("hits", [])
                for hit in hits:
                    src = hit.get("_source", {})
                    slug = src.get("slug")
                    if not slug or slug in seen_slugs:
                        continue
                    seen_slugs.add(slug)

                    site_url = src.get("site_url")
                    if site_url and site_url.startswith("http"):
                        official_url = site_url
                    else:
                        official_url = f"https://{slug}.devfolio.co"

                    org_name = (
                        src.get("organisation_name")
                        or src.get("location")
                        or "Devfolio Partner"
                    )

                    prizes = src.get("prizes") or []
                    prize_text = ""
                    if prizes:
                        names = [p.get("name") for p in prizes if isinstance(p, dict) and p.get("name")]
                        prize_text = f"Prizes: {', '.join(names[:3])}"

                    results.append({
                        "title": (src.get("name") or "").strip(),
                        "organiser": str(org_name).strip(),
                        "official_url": official_url,
                        "reg_deadline": src.get("ends_at") or src.get("starts_at"),
                        "event_date": src.get("starts_at"),
                        "prize_pool": prize_text,
                        "source": self.source_name,
                        "discovery_url": "https://devfolio.co/hackathons",
                        "organiser_type": "college" if any(w in str(org_name).lower() for w in ["college", "university", "institute", "iit", "nit", "bits"]) else "platform",
                        "type_raw": "hackathon",
                        "eligibility": src.get("desc", "")[:200] if src.get("desc") else "",
                    })
            except Exception as e:
                print(f"[devfolio] Error scraping type {t}: {e}")
                continue

        return results
