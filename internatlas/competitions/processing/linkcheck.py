"""Cheap dead-link detection on official URLs."""
from concurrent.futures import ThreadPoolExecutor

import requests

from ..config import REQUEST_TIMEOUT, DEAD_STATUS_CODES

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def check_url(url: str) -> bool:
    """True = alive, False = dead."""
    if not url:
        return False
    try:
        r = requests.head(url, headers=HEADERS, timeout=REQUEST_TIMEOUT,
                          allow_redirects=True)
        if r.status_code in (403, 405, 501):   # HEAD not allowed -> try GET
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, stream=True)
            r.close()
        return r.status_code not in DEAD_STATUS_CODES
    except requests.RequestException:
        return False


def check_links(records: list, concurrency=5) -> None:
    """Sets rec['status'] = 'broken_link' in-place for dead URLs."""
    urls = [r.get("official_url") or "" for r in records]
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        alive = list(ex.map(check_url, urls))
    for rec, ok in zip(records, alive):
        if not ok and rec.get("status") == "live":
            rec["status"] = "broken_link"
