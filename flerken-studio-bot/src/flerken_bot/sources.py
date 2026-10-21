"""Small, explicit adapters for public job-board endpoints and RSS feeds."""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from html import unescape
from html.parser import HTMLParser
from typing import Any

import requests

from .models import Job

LOG = logging.getLogger(__name__)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def clean_html(value: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(value or "")
        return re.sub(r"\s+", " ", unescape(" ".join(parser.parts))).strip()
    except Exception:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()


def _get_json(url: str, session: requests.Session, timeout: int) -> Any:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def collect_greenhouse(source: dict[str, Any], session: requests.Session, timeout: int) -> list[Job]:
    board = str(source.get("board", "")).strip()
    if not board or board.startswith("REPLACE_"):
        LOG.warning("Skipping Greenhouse source %s: configure its board token", source.get("name"))
        return []
    base_domain = "boards-api.eu.greenhouse.io" if source.get("eu") else "boards-api.greenhouse.io"
    payload = _get_json(f"https://{base_domain}/v1/boards/{board}/jobs?content=true", session, timeout)
    jobs: list[Job] = []
    for item in payload.get("jobs", []):
        location = (item.get("location") or {}).get("name") or "Location not specified"
        content = clean_html(item.get("content") or "")
        jobs.append(Job(
            title=item.get("title") or "Untitled role",
            company=str(source.get("company") or source.get("name") or board),
            url=item.get("absolute_url") or "",
            official_url=item.get("absolute_url") or "",
            location=location,
            work_mode="Remote" if "remote" in location.lower() else "In-office / unspecified",
            description=content,
            source_name=str(source.get("name") or board),
            source_kind="official",
            published_at=str(item.get("updated_at") or ""),
            verification_status="pending",
        ))
    return jobs


def collect_lever(source: dict[str, Any], session: requests.Session, timeout: int) -> list[Job]:
    site = str(source.get("site", "")).strip()
    if not site or site.startswith("REPLACE_"):
        LOG.warning("Skipping Lever source %s: configure its site", source.get("name"))
        return []
    payload = _get_json(f"https://api.lever.co/v0/postings/{site}?mode=json", session, timeout)
    jobs: list[Job] = []
    for item in payload if isinstance(payload, list) else []:
        categories = item.get("categories") or {}
        location = categories.get("location") or "Location not specified"
        workplace = item.get("workplaceType") or ""
        mode = workplace.title() if workplace else ("Remote" if "remote" in location.lower() else "In-office / unspecified")
        url = item.get("hostedUrl") or item.get("applyUrl") or ""
        jobs.append(Job(
            title=item.get("text") or "Untitled role",
            company=str(source.get("company") or source.get("name") or site),
            url=url,
            official_url=url,
            location=location,
            work_mode=mode,
            category=str(categories.get("team") or categories.get("department") or "Other Opportunities"),
            description=clean_html(item.get("descriptionPlain") or item.get("description") or ""),
            source_name=str(source.get("name") or site),
            source_kind="official",
            published_at=str(item.get("createdAt") or ""),
            verification_status="pending",
        ))
    return jobs


def collect_ashby(source: dict[str, Any], session: requests.Session, timeout: int) -> list[Job]:
    site = str(source.get("site") or source.get("board") or source.get("slug") or "").strip()
    if not site or site.startswith("REPLACE_"):
        LOG.warning("Skipping Ashby source %s: configure its board/site", source.get("name"))
        return []
    url = f"https://api.ashbyhq.com/posting-api/job-board/{site}"
    payload = _get_json(url, session, timeout)
    jobs: list[Job] = []
    for item in payload.get("jobs", []) if isinstance(payload, dict) else []:
        title = (item.get("title") or "Untitled role").strip()
        location = item.get("location") or "Location not specified"
        is_remote = bool(item.get("isRemote"))
        workplace = item.get("workplaceType") or ""
        mode = "Remote" if is_remote else (workplace.title() if workplace else ("Remote" if "remote" in location.lower() else "In-office / unspecified"))
        job_url = (item.get("jobUrl") or "").strip()
        if not job_url and item.get("id"):
            job_url = f"https://jobs.ashbyhq.com/{site}/{item['id']}"
        dept = item.get("department") or item.get("team") or "Other Opportunities"
        content = clean_html(item.get("descriptionPlain") or item.get("descriptionHtml") or "")
        jobs.append(Job(
            title=title,
            company=str(source.get("company") or source.get("name") or site),
            url=job_url,
            official_url=job_url,
            location=location,
            work_mode=mode,
            category=str(dept),
            description=content,
            source_name=str(source.get("name") or site),
            source_kind="official",
            published_at=str(item.get("publishedAt") or ""),
            verification_status="pending",
        ))
    return jobs


def collect_rss(source: dict[str, Any], session: requests.Session, timeout: int) -> list[Job]:
    url = str(source.get("url", "")).strip()
    if not url:
        return []
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    jobs: list[Job] = []
    # Handles standard RSS 2.0 and common Atom feeds.
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "Untitled role").strip()
        link = (item.findtext("link") or "").strip()
        description = clean_html(item.findtext("description") or "")
        pub_date = (item.findtext("pubDate") or "").strip()
        official_url = (item.findtext("official_url") or "").strip()
        jobs.append(Job(
            title=title,
            company=str(source.get("name") or "Aggregator listing"),
            url=official_url or link,
            official_url=official_url,
            location="Location not specified",
            description=description,
            source_name=str(source.get("name") or url),
            source_kind=str(source.get("kind") or "aggregator"),
            published_at=pub_date,
            verification_status="pending",
            verification_note="Aggregator feed: official employer URL must be confirmed",
        ))
    # Atom namespace support
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//atom:entry", ns):
        title = (entry.findtext("atom:title", default="Untitled role", namespaces=ns) or "Untitled role").strip()
        link_node = entry.find("atom:link", ns)
        link = (link_node.attrib.get("href", "") if link_node is not None else "").strip()
        summary = entry.findtext("atom:summary", default="", namespaces=ns) or ""
        jobs.append(Job(
            title=title, company=str(source.get("name") or "Aggregator listing"), url=link,
            description=clean_html(summary), source_name=str(source.get("name") or url),
            source_kind=str(source.get("kind") or "aggregator"),
            published_at=entry.findtext("atom:updated", default="", namespaces=ns) or "",
            verification_status="pending",
            verification_note="Aggregator feed: official employer URL must be confirmed",
        ))
    return jobs


def collect_sources(config: dict[str, Any]) -> list[Job]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    collection = config.get("collection", {})
    timeout = int(collection.get("request_timeout_seconds", 15))
    session = requests.Session()
    session.headers.update({"User-Agent": collection.get("user_agent", "FlerkenStudioBot/0.1")})
    jobs: list[Job] = []
    adapters = {"greenhouse": collect_greenhouse, "lever": collect_lever, "ashby": collect_ashby, "rss": collect_rss}

    enabled_sources = []
    for source in config.get("sources", []):
        if not source.get("enabled", False):
            continue
        kind = str(source.get("type", "")).lower()
        adapter = adapters.get(kind)
        if adapter is None:
            LOG.warning("Unknown source type %r; skipping", kind)
            continue
        enabled_sources.append((source, kind, adapter))

    if not enabled_sources:
        return []

    def _fetch_one(item):
        src, k, fn = item
        try:
            found = fn(src, session, timeout)
            LOG.info("Source %s returned %d listings", src.get("name", k), len(found))
            return found
        except (requests.RequestException, ValueError, ET.ParseError) as exc:
            LOG.warning("Could not collect from source %s: %s", src.get("name", k), exc)
            return []

    with ThreadPoolExecutor(max_workers=12) as pool:
        for found in pool.map(_fetch_one, enabled_sources):
            jobs.extend(found)
    return jobs

