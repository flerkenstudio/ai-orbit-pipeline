"""SQLite schema and helpers for InternAtlas Substack Internships Pipeline."""
import sqlite3
from datetime import datetime
from . import config

FIELDS = [
    "id", "company", "role_title", "location", "work_mode",
    "section", "is_hot", "apply_url", "ats_source",
    "priority_score", "status", "first_seen", "last_verified"
]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS substack_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dedupe_key TEXT UNIQUE,
    company TEXT,
    role_title TEXT,
    location TEXT,
    work_mode TEXT,
    section TEXT,
    is_hot INTEGER DEFAULT 0,
    apply_url TEXT,
    ats_source TEXT,
    priority_score INTEGER DEFAULT 0,
    status TEXT DEFAULT 'live',
    first_seen TEXT,
    last_verified TEXT
);
CREATE INDEX IF NOT EXISTS idx_substack_section ON substack_jobs(section);
CREATE INDEX IF NOT EXISTS idx_substack_hot ON substack_jobs(is_hot);
CREATE INDEX IF NOT EXISTS idx_substack_priority ON substack_jobs(priority_score);
"""


def init_db(db_path=None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or config.DB_PATH)
    conn.executescript(CREATE_TABLE_SQL)
    conn.commit()
    return conn


def upsert_jobs(conn: sqlite3.Connection, jobs: list) -> dict:
    counts = {"inserted": 0, "updated": 0, "skipped": 0}
    now = datetime.now().isoformat()
    cur = conn.cursor()
    seen_keys = set()

    for job in jobs:
        if not job or not job.get("apply_url") or not job.get("role_title"):
            counts["skipped"] += 1
            continue
        key = job["apply_url"].strip().lower()
        if key in seen_keys:
            counts["skipped"] += 1
            continue
        seen_keys.add(key)

        existing = cur.execute(
            "SELECT id FROM substack_jobs WHERE dedupe_key = ?", (key,)
        ).fetchone()

        if existing:
            cur.execute(
                """UPDATE substack_jobs
                   SET company=?, role_title=?, location=?, work_mode=?,
                       section=?, is_hot=?, ats_source=?, priority_score=?,
                       status='live', last_verified=?
                   WHERE id=?""",
                (
                    job.get("company", ""),
                    job.get("role_title", ""),
                    job.get("location", ""),
                    job.get("work_mode", "In-Office"),
                    job.get("section", ""),
                    int(bool(job.get("is_hot", 0))),
                    job.get("ats_source", ""),
                    int(job.get("priority_score", 50)),
                    now,
                    existing[0],
                ),
            )
            counts["updated"] += 1
        else:
            cur.execute(
                """INSERT INTO substack_jobs
                   (dedupe_key, company, role_title, location, work_mode,
                    section, is_hot, apply_url, ats_source, priority_score,
                    status, first_seen, last_verified)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'live', ?, ?)""",
                (
                    key,
                    job.get("company", ""),
                    job.get("role_title", ""),
                    job.get("location", ""),
                    job.get("work_mode", "In-Office"),
                    job.get("section", ""),
                    int(bool(job.get("is_hot", 0))),
                    job.get("apply_url", ""),
                    job.get("ats_source", ""),
                    int(job.get("priority_score", 50)),
                    now,
                    now,
                ),
            )
            counts["inserted"] += 1

    conn.commit()
    return counts


def fetch_all_jobs(conn: sqlite3.Connection) -> list:
    cur = conn.execute(
        "SELECT * FROM substack_jobs WHERE status='live' ORDER BY is_hot DESC, priority_score DESC, company ASC"
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
