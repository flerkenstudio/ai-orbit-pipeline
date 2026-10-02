"""THE single entry point: run_competitions_pipeline()."""
from .scrapers import get_all_scrapers
from .processing.cleaner import clean
from .processing.dedupe import upsert_records, mark_expired, fetch_all
from .processing.linkcheck import check_links
from .export.excel import export
from .schema import init_db
from .config import LINKCHECK_CONCURRENCY


def run_competitions_pipeline(verbose: bool = True, linkcheck: bool = True,
                              only: str = None, raw_override: list = None) -> str:
    """Returns path of the generated Excel file.
    only: run just one source by name. raw_override: skip scraping (demo/tests)."""
    log = print if verbose else (lambda *a, **k: None)

    # 1. SCRAPE (one failure never kills the run)
    if raw_override is not None:
        raw = list(raw_override)
    else:
        raw = []
        for scraper in get_all_scrapers():
            if only and scraper.source_name != only:
                continue
            try:
                items = scraper.scrape()
                log(f"[{scraper.source_name}] {len(items)} items")
                raw.extend(items)
            except Exception as e:
                log(f"[{scraper.source_name}] ERROR: {e}")

    # 2. CLEAN + 3. UPSERT
    cleaned = [clean(r) for r in raw]
    conn = init_db()
    counts = upsert_records(conn, cleaned)
    log(f"DB: {counts}")

    # 4. LIFECYCLE
    mark_expired(conn)

    # 5. LINK CHECK (live records only)
    if linkcheck:
        live = [r for r in fetch_all(conn) if r["status"] == "live"]
        check_links(live, concurrency=LINKCHECK_CONCURRENCY)
        for r in live:
            conn.execute("UPDATE competitions SET status=? WHERE id=?",
                         (r["status"], r["id"]))
        conn.commit()

    # 6. EXPORT
    path = export(fetch_all(conn))
    conn.close()
    log(f"Excel written: {path}")
    return str(path)
