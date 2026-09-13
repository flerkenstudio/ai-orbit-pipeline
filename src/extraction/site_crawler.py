"""Fetch the official site for verification + richer metadata."""
import logging

from urllib.parse import urlparse
from bs4 import BeautifulSoup

from src.utils.http_client import fetch
from src.config import RATE_LIMIT_SLEEP
from src.extraction.logo_extractor import extract_logo
from src.extraction.feature_extractor import (
    extract_pricing, extract_features, extract_social_links
)

log = logging.getLogger("pipeline")


def enrich_from_official_site(candidate) -> None:
    """Verify the site is live and pull rich metadata (logo, description, pricing, features, socials)."""
    if not candidate.url:
        candidate.verified = False
        return

    # Default fallback logo via Google Favicons if none exists
    domain = urlparse(candidate.url).netloc
    if domain and not candidate.logo_url:
        candidate.logo_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"

    is_gh = "github.com" in candidate.url.lower() or candidate.source_name.lower() == "github"
    if is_gh:
        candidate.pricing = "Open Source"
        candidate.open_source = True

    r = fetch(candidate.url, min_interval=RATE_LIMIT_SLEEP)
    if r is None or r.status_code != 200:
        log.warning("Site unreachable: %s (%s)",
                    candidate.url, getattr(r, "status_code", "network-error"))
        candidate.verified = False
        if not candidate.pricing:
            candidate.pricing = "Open Source" if is_gh else "Freemium"
        return

    final_url = r.url                      # post-redirect canonical URL
    candidate.url = final_url
    candidate.verified = True
    candidate.http_status = r.status_code

    try:
        soup = BeautifulSoup(r.text, "lxml")
        candidate.logo_url = extract_logo(soup, final_url)

        # Description: og:description or meta description
        meta = (soup.find("meta", property="og:description")
                or soup.find("meta", attrs={"name": "description"})
                or soup.find("meta", attrs={"name": "twitter:description"}))
        if meta and meta.get("content") and len(meta["content"].strip()) > len(candidate.description or ""):
            candidate.description = meta["content"].strip()

        title = soup.find("title")
        if title and not candidate.name:
            candidate.name = title.get_text(strip=True)

        # Extract pricing, features, social links
        candidate.pricing = extract_pricing(soup, r.text, is_github=is_gh)
        candidate.features = extract_features(soup)
        candidate.social_links = extract_social_links(soup, final_url)
        if "github" in candidate.social_links or is_gh:
            candidate.open_source = True

    except Exception as exc:
        log.warning("Parse failed for %s: %s", final_url, exc)
        if not candidate.pricing:
            candidate.pricing = "Open Source" if is_gh else "Freemium"

    log.info("Enriched %-30s pricing=%s features=%d logo=%s",
             candidate.name[:30], candidate.pricing, len(candidate.features),
             str(candidate.logo_url)[:50])
