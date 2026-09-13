"""Discovery via Curated Awesome-AI Lists (Direct markdown parsing, no scraping)."""
import logging
import re
from src.discovery.base import BaseSource, Candidate
from src.utils.http_client import _session
from src.config import USER_AGENT

log = logging.getLogger("pipeline")

AWESOME_LISTS = [
    {
        "name": "Awesome Generative AI",
        "url": "https://raw.githubusercontent.com/steven2358/awesome-generative-ai/main/README.md",
        "category_hint": "Generative AI",
    },
    {
        "name": "Awesome Open LLMs",
        "url": "https://raw.githubusercontent.com/eugeneyan/open-llms/main/README.md",
        "category_hint": "LLM & Foundation Models",
    },
]


class AwesomeListsSource(BaseSource):
    name = "awesome_lists"

    def discover(self) -> list:
        out = []
        headers = {"User-Agent": USER_AGENT}

        for entry in AWESOME_LISTS:
            try:
                r = _session.get(entry["url"], headers=headers, timeout=15)
                if r.status_code != 200:
                    log.warning("Awesome list '%s' HTTP %d", entry["name"], r.status_code)
                    continue

                text = r.text
                # Match markdown entries: - [Name](https://...) - Description
                # or [Name](https://...) : Description
                pattern = r'\[([^\]]{2,50})\]\((https?://[^\s\)]+)\)\s*[-–—:]\s*([^\n\r]{15,250})'
                matches = re.findall(pattern, text)

                for name, url, desc in matches:
                    # Filter out purely editorial links (e.g. twitter, papers, news sites)
                    if any(bad in url.lower() for bad in ["twitter.com", "x.com", "arxiv.org", "wikipedia.org", "doi.org"]):
                        continue

                    clean_name = name.strip(" *`")
                    clean_desc = desc.strip(" *`")

                    is_open_source = "github.com" in url.lower()
                    pricing = "Open Source" if is_open_source else "Freemium"

                    out.append(Candidate(
                        name=clean_name,
                        url=url,
                        description=clean_desc,
                        category_hint=entry["category_hint"],
                        source_name=entry["name"],
                        source_url=entry["url"],
                        pricing=pricing,
                        open_source=is_open_source,
                        social_links={"github": url} if is_open_source else {},
                        extra={"registry": entry["name"]},
                    ))

                log.info("Awesome list '%s' parsed -> %d tools (total so far: %d)",
                         entry["name"], len(matches), len(out))

            except Exception as exc:
                log.error("Failed to parse awesome list '%s': %s", entry["name"], exc)

        return out
