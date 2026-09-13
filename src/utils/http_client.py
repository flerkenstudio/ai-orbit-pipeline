"""Resilient HTTP client with retries, backoff, and rate limiting."""
import time
import logging
import requests
from typing import Optional

from src.config import DEFAULT_HEADERS, REQUEST_TIMEOUT, MAX_RETRIES

log = logging.getLogger("pipeline")
_session = requests.Session()
_session.headers.update(DEFAULT_HEADERS)
_last_call = 0.0


def _throttle(min_interval: float):
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _last_call = time.time()


def fetch(url: str, retries: int = MAX_RETRIES,
          min_interval: float = 0.0) -> Optional[requests.Response]:
    """GET with exponential backoff. Returns None on permanent failure."""
    for attempt in range(1, retries + 1):
        try:
            _throttle(min_interval)
            r = _session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            if r.status_code == 429:
                wait = 2 ** attempt * 5
                log.warning("429 rate limited %s — sleeping %ss", url, wait)
                time.sleep(wait)
                continue
            return r
        except requests.RequestException as exc:
            log.error("Attempt %d/%d failed for %s: %s",
                      attempt, retries, url, exc)
            time.sleep(2 ** attempt)
    log.error("Permanently failed: %s", url)
    return None


def fetch_json(url: str, **kwargs):
    r = fetch(url, **kwargs)
    if r is None:
        return None
    try:
        return r.json()
    except ValueError:
        log.error("Invalid JSON from %s", url)
        return None
