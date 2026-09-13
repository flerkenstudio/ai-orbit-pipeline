"""Extract rich metadata (pricing model, features, social links) from HTML."""
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


PRICING_INDICATORS = {
    "open_source": [
        "open source", "open-source", "mit license", "apache 2.0",
        "gnu general public license", "self-hostable", "self-hosted"
    ],
    "freemium": [
        "freemium", "free tier", "free plan", "free trial", "get started free",
        "start free", "free forever", "try for free", "free version"
    ],
    "paid": [
        "pricing", "plans & pricing", "billed monthly", "billed annually",
        "per month", "subscription", "buy now", "/mo", "pro plan", "enterprise"
    ],
    "free": [
        "100% free", "completely free", "totally free", "no credit card required"
    ],
}


def extract_pricing(soup: BeautifulSoup, page_text: str, is_github: bool = False) -> str:
    """Infer pricing model from page content, links, and buttons."""
    if is_github:
        return "Open Source"

    text_lower = page_text.lower()

    # Check for Open Source signals first
    for term in PRICING_INDICATORS["open_source"]:
        if term in text_lower:
            return "Open Source"

    # Check for navigation / button links containing 'pricing'
    has_pricing_page = False
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").lower()
        anchor_text = a.get_text(strip=True).lower()
        if "pricing" in href or "pricing" in anchor_text or "plans" in anchor_text:
            has_pricing_page = True
            break

    # Check for Freemium signals (Free plan/tier alongside paid plans)
    for term in PRICING_INDICATORS["freemium"]:
        if term in text_lower:
            return "Freemium"

    for term in PRICING_INDICATORS["free"]:
        if term in text_lower:
            return "Free"

    if has_pricing_page:
        return "Freemium"

    for term in PRICING_INDICATORS["paid"]:
        if term in text_lower:
            return "Paid"

    return "Freemium"  # Default common baseline for modern AI web tools


def extract_social_links(soup: BeautifulSoup, base_url: str) -> dict:
    """Extract GitHub, Twitter/X, Discord, and Docs links."""
    socials = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        netloc = parsed.netloc.lower()
        path = parsed.path.lower()

        if "github.com" in netloc and len(path.strip("/").split("/")) >= 2:
            # e.g., github.com/owner/repo
            if "github" not in socials:
                parts = path.strip("/").split("/")
                socials["github"] = f"https://github.com/{parts[0]}/{parts[1]}"
        elif ("twitter.com" in netloc or "x.com" in netloc) and path.strip("/") and not path.startswith(("/intent", "/share")):
            if "twitter" not in socials:
                socials["twitter"] = full_url
        elif "discord.gg" in netloc or ("discord.com" in netloc and "/invite" in path):
            if "discord" not in socials:
                socials["discord"] = full_url
        elif "docs" in netloc or "/docs" in path or "documentation" in path:
            if "docs" not in socials:
                socials["docs"] = full_url

    return socials


def extract_features(soup: BeautifulSoup, max_features: int = 4) -> list:
    """Extract key capabilities / features from headings and high-signal text."""
    features = []
    seen = set()

    # Generic headings to ignore
    ignore_patterns = [
        r"cookie", r"privacy", r"terms", r"sign in", r"log in", r"sign up",
        r"get started", r"navigation", r"footer", r"menu", r"subscribe",
        r"pricing", r"contact", r"about us", r"frequently asked", r"faq",
        r"all rights reserved", r"copyright", r"join our", r"newsletter"
    ]

    # Look through h1, h2, h3 and feature list items
    candidates = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        txt = tag.get_text(strip=True)
        if 15 <= len(txt) <= 120:
            candidates.append(txt)

    # Also check list items inside feature sections if any
    for li in soup.find_all("li"):
        txt = li.get_text(strip=True)
        if 20 <= len(txt) <= 100:
            candidates.append(txt)

    for cand in candidates:
        cand_clean = re.sub(r"\s+", " ", cand).strip()
        cand_lower = cand_clean.lower()
        if any(re.search(pat, cand_lower) for pat in ignore_patterns):
            continue
        if cand_lower not in seen:
            seen.add(cand_lower)
            features.append(cand_clean)
            if len(features) >= max_features:
                break

    return features
