"""Unstop adapter — Fast & reliable REST API scraper.
Fetches competitions, hackathons, and quizzes directly from Unstop public search API."""
import requests

from .base import BaseScraper
from ..config import REQUEST_TIMEOUT


class UnstopScraper(BaseScraper):
    source_name = "unstop"
    API_URL = "https://unstop.com/api/public/opportunity/search-result"
    
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://unstop.com/competitions",
    }

    CATEGORIES = ["competitions", "hackathons", "quizzes"]
    PAGES_PER_CATEGORY = 3  # 50 items/page * 3 pages = 150 items per category

    def scrape(self) -> list:
        results = []
        seen_urls = set()

        for category in self.CATEGORIES:
            for page in range(1, self.PAGES_PER_CATEGORY + 1):
                try:
                    params = {
                        "opportunity": category,
                        "page": page,
                        "per_page": 50,
                    }
                    resp = requests.get(
                        self.API_URL,
                        headers=self.HEADERS,
                        params=params,
                        timeout=REQUEST_TIMEOUT,
                    )
                    if resp.status_code != 200:
                        print(f"[unstop] HTTP {resp.status_code} for {category} page {page}")
                        continue
                    
                    payload = resp.json()
                    items = payload.get("data", {}).get("data", [])
                    if not items:
                        break

                    for item in items:
                        seo_url = item.get("seo_url") or item.get("public_url") or ""
                        if not seo_url:
                            continue
                        
                        clean_seo = seo_url.strip('/')
                        if clean_seo.startswith("http"):
                            official_url = clean_seo
                        else:
                            official_url = f"https://unstop.com/{clean_seo}"

                        if official_url in seen_urls:
                            continue
                        seen_urls.add(official_url)

                        # Extract organiser details
                        org = item.get("organisation") or {}
                        org_name = ""
                        org_tier = None
                        if isinstance(org, dict):
                            org_name = org.get("name", "")
                            org_tier = org.get("tier")
                        elif isinstance(org, str):
                            org_name = org

                        # Extract prizes
                        prize_text = ""
                        prizes_data = item.get("prizes") or []
                        if isinstance(prizes_data, list) and prizes_data:
                            total_cash = 0
                            cash_strings = []
                            for p in prizes_data:
                                if isinstance(p, dict):
                                    cash = p.get("cash")
                                    rank = p.get("rank", "Prize")
                                    if cash and isinstance(cash, (int, float)) and cash > 0:
                                        total_cash += cash
                                        cash_strings.append(f"{rank}: ₹{cash:,.0f}")
                            if total_cash > 0:
                                prize_text = f"₹{total_cash:,.0f} Total ({', '.join(cash_strings[:2])})"
                            else:
                                prize_text = prizes_data[0].get("others") or "Certificates & Rewards"
                        elif item.get("prize"):
                            prize_text = str(item.get("prize"))

                        # Extract reg deadline & dates
                        reg_deadline = item.get("end_date") or item.get("regn_end_date")
                        event_date = item.get("start_date")

                        # Extract filters / tags
                        filters = item.get("filters") or []
                        filter_names = [
                            f.get("name") for f in filters if isinstance(f, dict) and f.get("name")
                        ]
                        
                        results.append({
                            "title": (item.get("title") or "").strip(),
                            "organiser": org_name.strip(),
                            "organiser_tier": org_tier,
                            "official_url": official_url,
                            "reg_deadline": reg_deadline,
                            "event_date": event_date,
                            "prize_pool": prize_text,
                            "source": self.source_name,
                            "discovery_url": f"https://unstop.com/{category}",
                            "organiser_type": "college" if org_tier in (1, 2) else "platform",
                            "type_raw": item.get("type"),
                            "subtype_raw": item.get("subtype"),
                            "filter_tags": ", ".join(filter_names),
                            "registrations_count": item.get("registerations_count"),
                            "views_count": item.get("views_count"),
                            "eligibility": item.get("regnRequirements"),
                        })
                except Exception as e:
                    print(f"[unstop] Error scraping {category} page {page}: {e}")
                    continue

        return results
