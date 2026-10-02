from .unstop import UnstopScraper
from .devfolio import DevfolioScraper
from .hackerearth import HackerEarthScraper
from .generic_static import GenericStaticScraper, load_sources


def get_all_scrapers() -> list:
    """REST adapters + config-driven static sources."""
    scrapers = [UnstopScraper(), DevfolioScraper(), HackerEarthScraper()]
    for src in load_sources():
        if src.get("engine") == "playwright":
            continue
        scrapers.append(GenericStaticScraper(src))
    return scrapers
