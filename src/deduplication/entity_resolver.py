"""Entity resolution: domain-first, then fuzzy name matching."""
import logging
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from src.cleaning.url_normalizer import canonical_domain, normalize_url
from src.normalization.entity_normalizer import canonical_name

log = logging.getLogger("pipeline")
FUZZY_THRESHOLD = 92


@dataclass
class Entity:
    id: str = ""
    entity_type: str = "Tool"
    name: str = ""
    description: str = ""
    url: str = ""
    logo_url: str = ""
    categories: list = field(default_factory=list)
    source: dict = field(default_factory=dict)
    aliases: set = field(default_factory=set)
    verified: bool = False
    http_status: int = 0
    last_verified: str = ""
    pricing: str = ""
    features: list = field(default_factory=list)
    social_links: dict = field(default_factory=dict)
    open_source: bool = False


class EntityResolver:
    def __init__(self):
        self.by_domain: dict = {}
        self.review_queue: list = []
        self.stats = {"created": 0, "merged:domain": 0,
                      "merged:name": 0, "review": 0}

    def _merge_cand_into_entity(self, existing: Entity, cand):
        existing.aliases.add(cand.name)
        if not existing.logo_url and getattr(cand, "logo_url", ""):
            existing.logo_url = cand.logo_url
        if not existing.pricing and getattr(cand, "pricing", ""):
            existing.pricing = cand.pricing
        if not existing.features and getattr(cand, "features", []):
            existing.features = cand.features
        if getattr(cand, "social_links", {}):
            for k, v in cand.social_links.items():
                if k not in existing.social_links:
                    existing.social_links[k] = v
        if getattr(cand, "open_source", False):
            existing.open_source = True
        if getattr(cand, "verified", False):
            existing.verified = True
            existing.http_status = cand.http_status

    def resolve(self, cand):
        cand.url = normalize_url(cand.url)
        dom = canonical_domain(cand.url)
        cname = canonical_name(cand.name)

        # Tier 1 — exact canonical domain
        if dom and dom in self.by_domain:
            existing = self.by_domain[dom]
            self._merge_cand_into_entity(existing, cand)
            self.stats["merged:domain"] += 1
            return existing, "merged:domain"

        # Tier 2 — fuzzy canonical name
        for name, existing in self.by_domain.items():
            if cname and fuzz.token_sort_ratio(
                    cname, canonical_name(existing.name)) >= FUZZY_THRESHOLD:
                if canonical_domain(existing.url) != dom:
                    self.review_queue.append(
                        (existing.name, cand.name, existing.url, cand.url))
                    self.stats["review"] += 1
                    log.info("REVIEW needed: '%s' vs '%s'",
                             existing.name, cand.name)
                self._merge_cand_into_entity(existing, cand)
                self.stats["merged:name"] += 1
                return existing, "merged:name"

        # New entity
        entity = Entity(
            name=cand.name.strip(),
            description=cand.description,
            url=cand.url,
            logo_url=getattr(cand, "logo_url", ""),
            source={"name": cand.source_name, "url": cand.source_url},
            categories=[cand.category_hint] if cand.category_hint else [],
            verified=getattr(cand, "verified", False),
            http_status=getattr(cand, "http_status", 0),
            pricing=getattr(cand, "pricing", ""),
            features=getattr(cand, "features", []),
            social_links=getattr(cand, "social_links", {}),
            open_source=getattr(cand, "open_source", False),
        )
        if dom:
            self.by_domain[dom] = entity
        self.stats["created"] += 1
        return entity, "created"
