"""Discovery via Hugging Face Hub Spaces API (API-first, open public endpoint)."""
import logging
import re
from src.discovery.base import BaseSource, Candidate
from src.utils.http_client import _session
from src.config import USER_AGENT

log = logging.getLogger("pipeline")


class HuggingFaceSource(BaseSource):
    name = "huggingface"

    def __init__(self, limit_per_page: int = 100, max_pages: int = 5):
        self.limit_per_page = limit_per_page
        self.max_pages = max_pages

    def discover(self) -> list:
        out = []
        url = f"https://huggingface.co/api/spaces?limit={self.limit_per_page}&sort=likes&direction=-1"
        headers = {"User-Agent": USER_AGENT}

        for page in range(1, self.max_pages + 1):
            try:
                r = _session.get(url, headers=headers, timeout=15)
                if r.status_code != 200:
                    log.warning("HuggingFace API HTTP %d on page %d", r.status_code, page)
                    break

                items = r.json()
                if not items or not isinstance(items, list):
                    break

                for item in items:
                    space_id = item.get("id", "")
                    if not space_id:
                        continue
                    repo_name = space_id.split("/")[-1]
                    name = repo_name.replace("-", " ").replace("_", " ").title()
                    likes = item.get("likes", 0)
                    sdk = item.get("sdk", "web")
                    tags = item.get("tags", [])

                    # Infer a category hint from tags/sdk
                    tag_str = " ".join(tags).lower()
                    if any(w in tag_str for w in ["diffusion", "image", "flux", "video", "comic", "canvas"]):
                        cat_hint = "Generative AI"
                    elif any(w in tag_str for w in ["agent", "rag", "autogen", "crew"]):
                        cat_hint = "Agent Framework"
                    elif any(w in tag_str for w in ["chat", "llm", "leaderboard", "eval"]):
                        cat_hint = "Chat & Assistant"
                    elif any(w in tag_str for w in ["audio", "voice", "speech", "tts"]):
                        cat_hint = "Audio & Speech"
                    elif any(w in tag_str for w in ["code", "coding", "developer"]):
                        cat_hint = "Coding"
                    else:
                        cat_hint = "Open Source"

                    space_url = f"https://huggingface.co/spaces/{space_id}"
                    out.append(Candidate(
                        name=name,
                        url=space_url,
                        description=f"{name} — AI application hosted on Hugging Face Spaces ({sdk}, {likes:,} likes).",
                        category_hint=cat_hint,
                        source_name="Hugging Face",
                        source_url=space_url,
                        pricing="Free",
                        open_source=True,
                        social_links={"huggingface": space_url},
                        extra={
                            "likes": likes,
                            "sdk": sdk,
                            "tags": tags,
                        }
                    ))

                log.info("HuggingFace page %d fetched (%d spaces, cumulative: %d)",
                         page, len(items), len(out))

                # Check Link header for next cursor
                link_header = r.headers.get("Link", "")
                next_url = None
                if link_header:
                    match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
                    if match:
                        next_url = match.group(1)

                if next_url:
                    url = next_url
                else:
                    break

            except Exception as exc:
                log.error("HuggingFace discovery failed on page %d: %s", page, exc)
                break

        return out
