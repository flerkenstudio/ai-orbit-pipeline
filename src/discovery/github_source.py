"""Discovery via GitHub Search API (API-first, no scraping)."""
import logging
import requests

from src.discovery.base import BaseSource, Candidate
from src.utils.http_client import _session
from src.config import GITHUB_TOKEN

log = logging.getLogger("pipeline")

QUERIES = [
    "topic:ai-tool stars:>150",
    "topic:ai-agent stars:>200",
    "topic:generative-ai stars:>500",
    "topic:llm-agent stars:>150",
    "topic:copilot stars:>200",
]


class GitHubSource(BaseSource):
    name = "github"

    def discover(self) -> list:
        out = []
        headers = {}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"
        for q in QUERIES:
            try:
                r = _session.get(
                    "https://api.github.com/search/repositories",
                    params={"q": q, "per_page": 50, "sort": "stars"},
                    headers=headers, timeout=15,
                )
                if r.status_code != 200:
                    log.warning("GitHub '%s' -> HTTP %d", q, r.status_code)
                    continue
                for item in r.json().get("items", []):
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
                log.info("GitHub query '%s' done (total so far: %d)", q, len(out))
            except requests.RequestException as exc:
                log.error("GitHub query '%s' failed: %s", q, exc)
        return out
