"""Discovery via Hacker News Algolia API — great for AI tool launches."""
import logging
import requests

from src.discovery.base import BaseSource, Candidate
from src.utils.http_client import _session

log = logging.getLogger("pipeline")

QUERIES = ["AI tool", "AI assistant", "Show HN AI"]


NON_TOOL_KEYWORDS = [
    "scraps", "bias", "violate", "lawsuit", "employees", "do not work",
    "little value", "infected", "what happened after", "tokenmaxxing",
    "fired", "layoffs", "banned", "security hole", "scam", "regulation",
    "is dead", "future of", "vs", "why i", "why you", "how to"
]


class HackerNewsSource(BaseSource):
    name = "hackernews"

    def discover(self) -> list:
        out = []
        for q in QUERIES:
            try:
                r = _session.get(
                    "https://hn.algolia.com/api/v1/search",
                    params={"query": q, "tags": "story",
                            "hitsPerPage": 50, "numericFilters": "points>10"},
                    timeout=15,
                )
                if r.status_code != 200:
                    log.warning("HN '%s' -> HTTP %d", q, r.status_code)
                    continue
                for hit in r.json().get("hits", []):
                    url = hit.get("url") or ""
                    title = hit.get("title") or ""
                    if not url or "news.ycombinator.com" in url:
                        continue
                    
                    t_lower = title.lower()
                    if any(k in t_lower for k in NON_TOOL_KEYWORDS) or "?" in title:
                        continue

                    # Clean prefix like "Show HN: ", "Launch HN: "
                    clean_name = title
                    for pfx in ["Show HN: ", "Launch HN: ", "Show HN - ", "Launch HN - "]:
                        if clean_name.startswith(pfx):
                            clean_name = clean_name[len(pfx):]
                            break
                    # If it has a subtitle "Name – description", use first part as name
                    for sep in [" – ", " - ", " — "]:
                        if sep in clean_name and len(clean_name.split(sep)[0]) <= 30:
                            clean_name = clean_name.split(sep)[0]
                            break

                    out.append(Candidate(
                        name=clean_name.strip(),
                        url=url,
                        description=title,
                        source_name="Hacker News",
                        source_url="https://news.ycombinator.com/item?id="
                                   + str(hit.get("objectID", "")),
                        extra={"points": hit.get("points", 0)},
                    ))
            except requests.RequestException as exc:
                log.error("HN query '%s' failed: %s", q, exc)
        log.info("HackerNews discovery -> %d candidates", len(out))
        return out
