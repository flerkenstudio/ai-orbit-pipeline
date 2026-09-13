"""Discovery via GitHub Search API (API-first, no scraping)."""
import logging
import requests

from src.discovery.base import BaseSource, Candidate
from src.utils.http_client import _session
from src.config import GITHUB_TOKEN

log = logging.getLogger("pipeline")

QUERIES = [
    "topic:ai-tool stars:>100",
    "topic:ai-agent stars:>100",
    "topic:generative-ai stars:>300",
    "topic:llm-agent stars:>100",
    "topic:copilot stars:>100",
    "topic:mcp-server stars:>20",
    "topic:rag stars:>150",
    "topic:langchain stars:>200",
    "topic:crewai stars:>50",
    "topic:text-to-image stars:>100",
    "topic:speech-to-text stars:>100",
    "topic:prompt-engineering stars:>200",
    "topic:agentic stars:>50",
    "topic:ai-coding stars:>50",
]


class GitHubSource(BaseSource):
    name = "github"

    def __init__(self, max_pages: int = 2 if GITHUB_TOKEN else 1):
        self.max_pages = max_pages

    def discover(self) -> list:
        out = []
        headers = {}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"

        for q in QUERIES:
            for page in range(1, self.max_pages + 1):
                try:
                    r = _session.get(
                        "https://api.github.com/search/repositories",
                        params={"q": q, "per_page": 50, "page": page, "sort": "stars"},
                        headers=headers, timeout=15,
                    )
                    if r.status_code in (403, 429):
                        log.warning("GitHub rate limit reached (%d) for '%s' page %d. Continuing...", r.status_code, q, page)
                        break
                    if r.status_code != 200:
                        log.warning("GitHub '%s' page %d -> HTTP %d", q, page, r.status_code)
                        break

                    items = r.json().get("items", [])
                    if not items:
                        break

                    for item in items:
                        homepage = (item.get("homepage") or "").strip()
                        url = homepage if homepage.startswith("http") \
                            else item.get("html_url", "")
                        gh_url = item.get("html_url", "")
                        stars = item.get("stargazers_count", 0)
                        out.append(Candidate(
                            name=item.get("name", "").replace("-", " ").title(),
                            url=url,
                            description=item.get("description") or "",
                            category_hint="Open Source",
                            source_name="GitHub",
                            source_url=gh_url,
                            pricing="Open Source",
                            open_source=True,
                            social_links={"github": gh_url} if gh_url else {},
                            extra={"stars": stars,
                                   "language": item.get("language", ""),
                                   "pushed_at": item.get("pushed_at", "")},
                        ))
                    log.info("GitHub query '%s' page %d done (total so far: %d)", q, page, len(out))
                except requests.RequestException as exc:
                    log.error("GitHub query '%s' page %d failed: %s", q, page, exc)
                    break
        return out
