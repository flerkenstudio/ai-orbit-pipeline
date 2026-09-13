"""URL normalization: https enforcement, tracking param removal, canonical form."""
import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_content",
    "utm_term", "ref", "fbclid", "gclid", "mc_cid", "mc_eid",
}


def normalize_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    p = urlparse(url)
    qs = parse_qs(p.query)
    qs = {k: v for k, v in qs.items() if k.lower() not in TRACKING_PARAMS}
    query = urlencode(qs, doseq=True)
    path = re.sub(r"/+$", "", p.path) or "/"
    host = p.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return urlunparse(("https", host, path, "", query, ""))


def domain_of(url: str) -> str:
    try:
        return urlparse(normalize_url(url)).netloc
    except Exception:
        return ""


def canonical_domain(url: str) -> str:
    """Registrable-ish domain: last two labels (handles most .com/.io/.ai)."""
    dom = domain_of(url)
    parts = dom.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return dom
