"""Single entry point: run_substack_pipeline()."""
from .scrapers import scrape_all_ats_portals
from .processor import organize_for_substack
from .schema import init_db, upsert_jobs, fetch_all_jobs
from .exporter import (
    export_substack_docx,
    export_substack_xlsx,
    generate_substack_markdown,
    build_substack_metadata,
)


def run_substack_pipeline(
    include_seed: bool = True,
    progress_cb=None,
    verbose: bool = True,
) -> dict:
    """Scrapes direct ATS portals, organizes into 6 Substack sections, persists to SQLite,
    and generates both Word (.docx) and Excel (.xlsx) files."""
    log = print if verbose else (lambda *a, **k: None)

    # 1. Scrape ATS boards + verified direct seed portals
    raw_jobs = scrape_all_ats_portals(include_seed=include_seed, progress_cb=progress_cb)
    log(f"[substack] Scraped {len(raw_jobs)} raw early-career/internship roles")

    # 2. Organize into 6 Substack sections (with Top 10 Hottest)
    organized = organize_for_substack(raw_jobs)

    # 3. Persist to SQLite
    conn = init_db()
    counts = upsert_jobs(conn, organized)
    all_stored = organize_for_substack(fetch_all_jobs(conn))
    # Update sections in DB after re-organizing full stored list
    upsert_jobs(conn, all_stored)
    final_jobs = fetch_all_jobs(conn)
    conn.close()
    log(f"[substack] DB counts: {counts}, Total active: {len(final_jobs)}")

    # 4. Export Word (.docx) & Excel (.xlsx)
    docx_path = export_substack_docx(final_jobs)
    xlsx_path = export_substack_xlsx(final_jobs)
    markdown_text = generate_substack_markdown(final_jobs)
    meta = build_substack_metadata(final_jobs)

    log(f"[substack] Word (.docx) written: {docx_path}")
    log(f"[substack] Excel (.xlsx) written: {xlsx_path}")

    return {
        "total": len(final_jobs),
        "counts": counts,
        "docx_path": str(docx_path),
        "docx_file": docx_path.name,
        "xlsx_path": str(xlsx_path),
        "xlsx_file": xlsx_path.name,
        "title": meta["title"],
        "subtitle": meta["subtitle"],
        "date_str": meta["date_str"],
        "markdown": markdown_text,
    }
