"""Standardized record definition + SQLite setup."""
import sqlite3
from datetime import datetime

from . import config

FIELDS = [
    "id", "title", "organiser", "organiser_type", "category",
    "eligibility", "mode", "team_size", "location",
    "reg_deadline", "event_date", "prize_pool", "prize_value",
    "reg_fee", "rounds", "official_url", "discovery_url",
    "source", "premium", "priority_score", "status",
    "first_seen", "last_verified",
]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS competitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dedupe_key TEXT UNIQUE,
    title TEXT,
    organiser TEXT,
    organiser_type TEXT,
    category TEXT,
    eligibility TEXT,
    mode TEXT,
    team_size TEXT,
    location TEXT,
    reg_deadline TEXT,
    event_date TEXT,
    prize_pool TEXT,
    prize_value REAL,
    reg_fee REAL DEFAULT 0,
    rounds TEXT,
    official_url TEXT,
    discovery_url TEXT,
    source TEXT,
    premium INTEGER DEFAULT 0,
    priority_score INTEGER DEFAULT 0,
    status TEXT DEFAULT 'live',
    first_seen TEXT,
    last_verified TEXT
);
"""

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_status ON competitions(status);
CREATE INDEX IF NOT EXISTS idx_deadline ON competitions(reg_deadline);
CREATE INDEX IF NOT EXISTS idx_priority ON competitions(priority_score);
"""


def init_db(db_path=None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or config.DB_PATH)
    cur = conn.cursor()
    cur.execute(CREATE_TABLE_SQL)
    
    columns = [row[1] for row in cur.execute("PRAGMA table_info(competitions)").fetchall()]
    if "priority_score" not in columns:
        cur.execute("ALTER TABLE competitions ADD COLUMN priority_score INTEGER DEFAULT 0;")
        conn.commit()

    conn.executescript(INDEX_SQL)
    conn.commit()
    return conn


def make_record(**kwargs) -> dict:
    rec = {f: kwargs.get(f) for f in FIELDS}
    now = datetime.now().isoformat()
    rec["first_seen"] = rec["first_seen"] or now
    rec["last_verified"] = now
    rec["status"] = rec["status"] or "live"
    rec["premium"] = int(bool(rec["premium"]))
    rec["priority_score"] = rec["priority_score"] or 0
    rec["reg_fee"] = rec["reg_fee"] or 0
    return rec
