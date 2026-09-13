"""Discovery via Product Hunt GraphQL API (API-first, official developer token)."""
import logging
from src.discovery.base import BaseSource, Candidate
from src.utils.http_client import _session
from src.config import PRODUCT_HUNT_TOKEN, USER_AGENT

log = logging.getLogger("pipeline")

GRAPHQL_QUERY = """
query GetPosts($cursor: String, $first: Int) {
  posts(first: $first, after: $cursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        name
        tagline
        website
        url
        votesCount
        thumbnail {
          url
        }
        topics {
          edges {
            node {
              name
            }
          }
        }
      }
    }
  }
}
"""


class ProductHuntSource(BaseSource):
    name = "producthunt"

    def __init__(self, first: int = 50, max_pages: int = 4):
        self.first = first
        self.max_pages = max_pages

    def discover(self) -> list:
        if not PRODUCT_HUNT_TOKEN:
            log.info("No PRODUCT_HUNT_TOKEN found — skipping Product Hunt discovery.")
            return []

        out = []
        headers = {
            "Authorization": f"Bearer {PRODUCT_HUNT_TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }

        cursor = None
        for page in range(1, self.max_pages + 1):
            try:
                payload = {
                    "query": GRAPHQL_QUERY,
                    "variables": {"first": self.first, "cursor": cursor}
                }
                r = _session.post(
                    "https://api.producthunt.com/v2/api/graphql",
                    json=payload,
                    headers=headers,
                    timeout=15,
                )
                if r.status_code != 200:
                    log.warning("Product Hunt API HTTP %d on page %d", r.status_code, page)
                    break

                data = r.json()
                if "errors" in data:
                    log.error("Product Hunt API errors: %s", data["errors"])
                    break

                posts_data = data.get("data", {}).get("posts", {})
                edges = posts_data.get("edges", [])
                if not edges:
                    break

                for edge in edges:
                    node = edge.get("node", {})
                    name = (node.get("name") or "").strip()
                    if not name:
                        continue

                    url = (node.get("website") or node.get("url") or "").strip()
                    tagline = (node.get("tagline") or "").strip()
                    ph_url = node.get("url", "")
                    votes = node.get("votesCount", 0)
                    thumbnail = (node.get("thumbnail") or {}).get("url", "")

                    topic_nodes = [t.get("node", {}).get("name", "") for t in node.get("topics", {}).get("edges", [])]
                    topic_str = " ".join(topic_nodes).lower()

                    if any(w in topic_str for w in ["developer", "coding", "code", "devops"]):
                        cat_hint = "Developer Tools"
                    elif any(w in topic_str for w in ["ai", "artificial intelligence", "machine learning"]):
                        cat_hint = "Generative AI"
                    elif any(w in topic_str for w in ["productivity", "task", "project"]):
                        cat_hint = "Productivity"
                    elif any(w in topic_str for w in ["design", "ui", "ux"]):
                        cat_hint = "Design"
                    else:
                        cat_hint = "Chat & Assistant"

                    out.append(Candidate(
                        name=name,
                        url=url,
                        description=f"{name} — {tagline}" if tagline else f"{name} — AI tool launched on Product Hunt.",
                        category_hint=cat_hint,
                        source_name="Product Hunt",
                        source_url=ph_url,
                        logo_url=thumbnail,
                        pricing="Freemium",
                        open_source=False,
                        social_links={"producthunt": ph_url},
                        extra={"votes": votes, "ph_id": node.get("id"), "topics": topic_nodes},
                    ))

                log.info("Product Hunt page %d fetched (%d tools, cumulative: %d)",
                         page, len(edges), len(out))

                page_info = posts_data.get("pageInfo", {})
                if page_info.get("hasNextPage") and page_info.get("endCursor"):
                    cursor = page_info["endCursor"]
                else:
                    break

            except Exception as exc:
                log.error("Product Hunt discovery failed on page %d: %s", page, exc)
                break

        return out
