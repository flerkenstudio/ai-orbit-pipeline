"""Config-driven scraper for static listing pages (sources.yaml)."""
import requests
import yaml
from bs4 import BeautifulSoup

from ..config import SOURCES_FILE, REQUEST_TIMEOUT
from .base import BaseScraper


class GenericStaticScraper(BaseScraper):
    def __init__(self, source: dict):
        self.source = source
        self.source_name = source["name"]

    def scrape(self) -> list:
        s = self.source
        sel = s["selectors"]
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        try:
            r = requests.get(s["url"], headers=headers, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"[{self.source_name}] FAILED: {e}")
            return []

        soup = BeautifulSoup(r.text, "html.parser")
        out = []
        for card in soup.select(sel["card"]):
            t = card.select_one(sel["title"])
            a = card.select_one(sel["link"])
            if not (t and a):
                continue
            dl = card.select_one(sel["deadline"]) if sel.get("deadline") else None
            out.append({
                "title": t.get_text(strip=True),
                "organiser": s.get("organiser", ""),
                "organiser_type": s.get("organiser_type", "college"),
                "official_url": self.absolute_url(s["url"], a.get("href", "")),
                "reg_deadline": dl.get_text(strip=True) if dl else None,
                "source": self.source_name,
                "discovery_url": s["url"],
            })
        return out


def load_sources() -> list:
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []
