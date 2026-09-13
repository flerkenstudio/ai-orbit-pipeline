"""Extract official logos from the site itself — never third-party CDNs."""
import logging
from urllib.parse import urljoin, urlparse

log = logging.getLogger("pipeline")


def extract_logo(soup, base_url: str) -> str:
    try:
        # Priority 1: apple-touch-icon (usually high-res)
        for link in soup.find_all("link", rel=True):
            rel = " ".join(link.get("rel", [])).lower()
            if "apple-touch-icon" in rel and link.get("href"):
                return urljoin(base_url, link["href"])

        # Priority 2: og:image (high quality brand image)
        og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
        if og and og.get("content"):
            content = og["content"].strip()
            if content.startswith("http") or content.startswith("/"):
                return urljoin(base_url, content)

        # Priority 3: standard icons
        for link in soup.find_all("link", rel=True):
            rel = " ".join(link.get("rel", [])).lower()
            if any(k in rel for k in ("icon", "shortcut icon", "fluid-icon")) and link.get("href"):
                return urljoin(base_url, link["href"])

        # Priority 4: twitter:image
        tw = soup.find("meta", attrs={"name": "twitter:image"}) or soup.find("meta", property="twitter:image")
        if tw and tw.get("content"):
            return urljoin(base_url, tw["content"].strip())
    except Exception as exc:
        log.warning("Logo extraction failed %s: %s", base_url, exc)

    # Fallback to high-res Google favicon service so logo is never empty
    try:
        domain = urlparse(base_url).netloc
        if domain:
            return f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
    except Exception:
        pass

    return urljoin(base_url, "/favicon.ico")
