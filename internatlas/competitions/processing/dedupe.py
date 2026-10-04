"""Dedupe keying + SQLite upsert (new = insert, existing = refresh)."""
import sqlite3
from datetime import datetime

from ..schema import FIELDS


def dedupe_key(rec: dict) -> str:
    discovery = (rec.get("discovery_url") or "").lower().strip()
    if discovery.startswith("http"):
        return f"disc||{discovery}"
    deadline = rec.get("reg_deadline") or ""
    org = (rec.get("organiser") or "unknown").lower().strip()
    title = (rec.get("title") or "").lower().strip()
    return f"{org}||{title}||{deadline}"


def upsert_records(conn: sqlite3.Connection, records: list) -> dict:
    counts = {"inserted": 0, "updated": 0, "skipped": 0}
    now = datetime.now().isoformat()
    cur = conn.cursor()
    seen_keys = set()
    for rec in records:
        if rec is None:
            counts["skipped"] += 1
            continue
        key = dedupe_key(rec)
        if key in seen_keys:
            counts["skipped"] += 1
            continue
        seen_keys.add(key)
        existing = cur.execute(
            "SELECT id FROM competitions WHERE dedupe_key = ?", (key,)
        ).fetchone()
        if existing:
            cur.execute(
                "UPDATE competitions SET last_verified = ?, status = 'live', "
                "official_url = ?, discovery_url = ?, priority_score = ?, premium = ?, prize_pool = ?, prize_value = ?, reg_deadline = ? "
                "WHERE id = ?",
                (now, rec.get("official_url"), rec.get("discovery_url"), rec.get("priority_score", 0), rec.get("premium", 0), rec.get("prize_pool"), rec.get("prize_value"), rec.get("reg_deadline"), existing[0]),
            )
            counts["updated"] += 1
        else:
            cols = ["dedupe_key"] + [f for f in FIELDS if f != "id"]
            vals = [rec.get(f) for f in FIELDS if f != "id"]
            cols_str = "dedupe_key, " + ",".join([f for f in FIELDS if f != "id"])
            vals_all = [key] + vals
            cur.execute(
                f"INSERT INTO competitions ({cols_str}) "
                f"VALUES ({','.join('?' for _ in vals_all)})",
                vals_all,
            )
            counts["inserted"] += 1
    conn.commit()
    return counts


def mark_expired(conn: sqlite3.Connection):
    today = datetime.now().date().isoformat()
    conn.execute(
        "UPDATE competitions SET status='expired' "
        "WHERE reg_deadline IS NOT NULL AND reg_deadline < ? "
        "AND status IN ('live','broken_link')",
        (today,),
    )
    conn.commit()


def fetch_all(conn: sqlite3.Connection) -> list:
    cur = conn.execute(
        "SELECT * FROM competitions ORDER BY priority_score DESC, reg_deadline IS NULL, reg_deadline ASC"
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
