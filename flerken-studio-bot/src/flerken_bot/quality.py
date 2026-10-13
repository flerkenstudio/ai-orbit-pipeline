from __future__ import annotations

import hashlib
import logging
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

import requests

from .models import Job

LOG = logging.getLogger(__name__)

CATEGORY_RULES = [
    ("Artificial Intelligence & Machine Learning Opportunities", ("artificial intelligence", "machine learning", "ai engineer", "ml engineer", "llm", "data science", "data scientist", "computer vision", "deep learning", "genai", "nlp")),
    ("Cybersecurity Opportunities", ("security", "cyber", "soc ", "penetration", "iam", "infosec", "vulnerability")),
    ("Data Analytics, Research & Intelligence Roles", ("data analyst", "business analyst", "risk analyst", "financial analyst", "ar analyst", "analytics", "research", "business intelligence", "quantitative", "economist")),
    ("Software Development & Core Engineering Opportunities", ("software", "developer", "engineering", "engineer", "backend", "frontend", "full stack", "fullstack", "java", "python", "qa engineer", "sdet", "devops", "sre", "cloud", "mobile", "ios", "android", "systems")),
    ("Product Design, Media & Content Strategy Roles", ("design", "ux", " ui ", "ui/ux", "content", "marketing artist", "video editor", "media", "copywriter", "youtube", "graphic", "brand")),
    ("Business Operations, HR, Marketing & Strategy Roles", ("human resources", " hr ", "recruiter", "recruitment", "talent acquisition", "operations", "strategy", "sales", "finance", "business development", "banking", "alliances", "compliance", "support", "marketing", "coordinator", "partner")),
]


def categorize(job: Job) -> str:
    title_and_dept = f" {job.title.lower()} {job.category.lower()} "
    for category, terms in CATEGORY_RULES:
        if any(term in title_and_dept for term in terms):
            return category
    desc_text = f" {job.description[:500].lower()} "
    for category, terms in CATEGORY_RULES:
        if any(term in desc_text for term in terms):
            return category
    return "Other Early-Career Opportunities"


def _is_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def verify_job(job: Job, session: requests.Session, timeout: int = 15, require_official: bool = True) -> Job:
    """Check URL reachability; do not confuse reachability with proof a role is open."""
    target = (job.official_url or job.url).strip()
    if not target or not _is_http_url(target):
        job.verification_status = "rejected"
        job.verification_note = "Missing or invalid application URL"
        return job
    if require_official and job.source_kind != "official" and not job.official_url:
        job.verification_status = "needs_review"
        job.verification_note = "Aggregator item has no explicit official employer application URL"
        return job
    try:
        response = session.get(target, timeout=timeout, allow_redirects=True, stream=True)
        status = response.status_code
        final_url = response.url
        response.close()
        if status >= 400:
            job.verification_status = "needs_review"
            job.verification_note = f"Application URL returned HTTP {status}; manual review required"
            return job
        job.url = final_url
        job.official_url = final_url if job.source_kind == "official" or job.official_url else ""
        job.verification_status = "verified_link"
        job.verification_note = "URL reachable; role availability still needs confirmation"
    except requests.RequestException as exc:
        job.verification_status = "needs_review"
        job.verification_note = f"Could not verify application URL: {type(exc).__name__}"
    return job


def is_target_job(job: Job, include_india: bool = True, include_remote_global: bool = True) -> bool:
    location = f"{job.location} {job.work_mode}".lower()
    is_india = any(token in location for token in ("india", "bengaluru", "bangalore", "hyderabad", "pune", "mumbai", "delhi", "gurugram", "gurgaon", "chennai", "noida", "kolkata", "indore", "remote india"))
    is_remote = "remote" in location or "worldwide" in location or "global" in location
    if include_india and is_india:
        return True
    if include_remote_global and is_remote:
        return True
    # Unknown locations are retained for review rather than silently dropped.
    return "not specified" in location or not location.strip()


def deduplicate(jobs: list[Job]) -> list[Job]:
    seen: set[str] = set()
    output: list[Job] = []
    for job in jobs:
        key_url = (job.official_url or job.url).strip().lower().rstrip("/")
        key_title_company = f"{job.title.strip().lower()}|{job.company.strip().lower()}"
        key = key_url if key_url else hashlib.sha256(key_title_company.encode()).hexdigest()
        if key in seen:
            LOG.info("Skipping duplicate listing: %s", job.title)
            continue
        seen.add(key)
        output.append(job)
    return output


from concurrent.futures import ThreadPoolExecutor
import re

EARLY_CAREER_INCLUDE = re.compile(
    r"\b(intern|internship|new\s*grad|graduate|entry[\s\-]*level|junior|jr\.?|apprentice|trainee|fellow|associate|early[\s\-]*career|campus|fresher|university|co[\-\s]?op|sde[\s\-]*1|sde[\s\-]*i|swe[\s\-]*1|swe[\s\-]*i|analyst)\b",
    re.IGNORECASE,
)
EARLY_CAREER_EXCLUDE = re.compile(
    r"\b(senior|sr\.?|staff|principal|director|vp|vice\s+president|head\s+of|lead|manager|distinguished|architect|iii|iv)\b",
    re.IGNORECASE,
)


def is_early_career(job: Job) -> bool:
    title = (job.title or "").strip()
    if EARLY_CAREER_EXCLUDE.search(title):
        return False
    if EARLY_CAREER_INCLUDE.search(title):
        return True
    return False


def verify_jobs_concurrent(
    jobs: list[Job],
    session: requests.Session,
    timeout: int = 15,
    require_official: bool = True,
    max_workers: int = 16,
) -> list[Job]:
    if not jobs:
        return []

    def _check(j: Job) -> Job:
        return verify_job(j, session, timeout=timeout, require_official=require_official)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(_check, jobs))


class SeenStore:
    """SQLite ledger to avoid regenerating the same roles across runs."""
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS seen (job_key TEXT PRIMARY KEY, first_seen TEXT DEFAULT CURRENT_TIMESTAMP)")

    @staticmethod
    def key(job: Job) -> str:
        value = (job.official_url or job.url).strip().lower().rstrip("/")
        if not value:
            value = f"{job.company.strip().lower()}|{job.title.strip().lower()}"
        return hashlib.sha256(value.encode()).hexdigest()

    def only_new(self, jobs: list[Job]) -> list[Job]:
        new: list[Job] = []
        with sqlite3.connect(self.path) as db:
            for job in jobs:
                key = self.key(job)
                found = db.execute("SELECT 1 FROM seen WHERE job_key=?", (key,)).fetchone()
                if found:
                    continue
                new.append(job)
        return new

    def mark_seen(self, jobs: list[Job]) -> None:
        with sqlite3.connect(self.path) as db:
            db.executemany("INSERT OR IGNORE INTO seen(job_key) VALUES (?)", [(self.key(job),) for job in jobs])

    def count(self) -> int:
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT COUNT(*) FROM seen").fetchone()
            return int(row[0]) if row else 0

    def clear(self) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM seen")

