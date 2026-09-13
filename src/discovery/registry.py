"""Orchestrates all discovery sources with per-source error isolation."""
import logging

from src.discovery.seed_source import SeedSource
from src.discovery.github_source import GitHubSource
from src.discovery.hackernews_source import HackerNewsSource

log = logging.getLogger("pipeline")


def run_discovery() -> list:
    sources = [SeedSource(), GitHubSource(), HackerNewsSource()]
    all_candidates = []
    for src in sources:
        try:
            batch = src.discover()
            all_candidates.extend(batch)
            log.info("Source %-12s -> %d candidates", src.name, len(batch))
        except Exception as exc:              # graceful degradation
            log.error("Source %s crashed, skipping: %s", src.name, exc)
    log.info("TOTAL candidates discovered: %d", len(all_candidates))
    return all_candidates
