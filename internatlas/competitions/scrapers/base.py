"""Abstract base for all scrapers."""
import time
import random
from abc import ABC, abstractmethod
from urllib.parse import urljoin

from ..config import REQUEST_DELAY_SECONDS


class BaseScraper(ABC):
    source_name = "base"

    @abstractmethod
    def scrape(self) -> list:
        """Return list of raw dicts: title, official_url, + optional fields."""

    def polite_delay(self):
        time.sleep(REQUEST_DELAY_SECONDS + random.uniform(0, 2))

    @staticmethod
    def absolute_url(base: str, href: str) -> str:
        return urljoin(base, href)
