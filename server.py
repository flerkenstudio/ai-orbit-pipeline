"""FastAPI backend server for AI Orbit Pipeline.
Provides endpoints to trigger the pipeline, stream live logs via SSE, and inspect status.
"""
import asyncio
import json
import logging
import os
import threading
import time
from collections import deque
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel

from urllib.parse import urlparse
from run import run_pipeline
from src.discovery.base import Candidate
from src.cleaning.url_normalizer import normalize_url
from src.extraction.site_crawler import enrich_from_official_site
from src.cleaning.text_cleaner import clean_description
from src.deduplication.entity_resolver import EntityResolver
from src.classification.categorizer import categorize
from src.utils.uuid_generator import stable_uuid
from src.validation.quality_gate import run_validation
from src.export.exporters import export_entities, export_sheets_csv
from src.export.supabase_exporter import export_to_supabase


class ScrapeUrlRequest(BaseModel):
    url: str
    name: Optional[str] = None
    category_hint: Optional[str] = None

class DirectoryScrapeRequest(BaseModel):
    url: str = "https://www.example.com/"
    limit: Optional[int] = 100
    workers: Optional[int] = 25


class CompetitionRunRequest(BaseModel):
    demo: bool = False
    no_linkcheck: bool = True
    only: Optional[str] = None


class SubstackRunRequest(BaseModel):
    include_seed: bool = True




from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    global main_loop
    main_loop = asyncio.get_running_loop()
    yield

app = FastAPI(title="AI Orbit Pipeline API", lifespan=lifespan)

# Enable CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory execution state
state = {
    "is_running": False,
    "start_time": None,
    "elapsed_seconds": 0,
    "stage": "idle",  # idle, discovery, extraction, classification, validation, export, completed, error
    "current": 0,
    "total": 0,
    "percent": 0.0,
    "last_tool": None,
    "summary": None,
}

dir_scrape_state = {
    "is_running": False,
    "total": 0,
    "completed": 0,
    "extracted": 0,
    "percent": 0.0,
    "last_tool": None,
    "output_xlsx": "agenthunter_agents_full.xlsx",
    "output_csv": "agenthunter_agents_full.csv",
    "status": "idle",
    "error": None,
}
dir_stop_event = threading.Event()

competitions_state = {
    "is_running": False,
    "last_run": None,
    "total": 0,
    "live": 0,
    "summary": None,
    "status": "idle",
    "error": None,
}
competitions_stop_event = threading.Event()

substack_state = {
    "is_running": False,
    "last_run": None,
    "total": 0,
    "completed_boards": 0,
    "total_boards": 0,
    "last_company": None,
    "summary": None,
    "status": "idle",
    "error": None,
}



recent_logs = deque(maxlen=250)
subscribers: List[asyncio.Queue] = []
main_loop = None


class BroadcastLogHandler(logging.Handler):
    """Logging handler that forwards records to SSE subscribers and in-memory buffer."""
    def emit(self, record):
        try:
            msg = self.format(record)
            entry = {
                "type": "log",
                "level": record.levelname,
                "message": msg,
                "timestamp": time.strftime("%H:%M:%S", time.localtime(record.created)),
            }
            recent_logs.append(entry)
            broadcast_event(entry)
        except Exception:
            pass


log_handler = BroadcastLogHandler()
log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(message)s", "%H:%M:%S"))
logging.getLogger("pipeline").addHandler(log_handler)
logging.getLogger("pipeline").setLevel(logging.INFO)


def broadcast_event(data: dict):
    """Broadcast an event to all connected SSE clients."""
    global main_loop, subscribers
    if not subscribers or not main_loop:
        return
    msg = f"data: {json.dumps(data)}\n\n"
    for q in list(subscribers):
        try:
            main_loop.call_soon_threadsafe(q.put_nowait, msg)
        except Exception:
            pass


stop_event = threading.Event()


def pipeline_worker():
    """Background worker that runs the ingestion pipeline."""
    stop_event.clear()
    state["is_running"] = True
    state["start_time"] = time.time()
    state["stage"] = "discovery"
    state["current"] = 0
    state["total"] = 0
    state["percent"] = 0.0
    state["last_tool"] = None
    state["summary"] = None

    def on_progress(event: dict):
        state["stage"] = event.get("stage", state["stage"])
        if event.get("type") == "progress":
            state["current"] = event.get("current", state["current"])
            state["total"] = event.get("total", state["total"])
            state["percent"] = event.get("percent", state["percent"])
            state["last_tool"] = event.get("tool")
        elif event.get("type") == "discovery_done":
            state["total"] = event.get("unique_count", 0)
        elif event.get("type") == "completed":
            state["summary"] = event
        elif event.get("type") == "stopped":
            state["stage"] = "stopped"
            state["is_running"] = False

        broadcast_event(event)

    try:
        logging.getLogger("pipeline").info("Pipeline execution triggered via Web UI.")
        res = run_pipeline(progress_callback=on_progress, stop_check=stop_event.is_set)
        if res and res.get("stopped"):
            state["stage"] = "stopped"
        else:
            state["summary"] = res
            state["stage"] = "completed"
    except Exception as exc:
        logging.getLogger("pipeline").error(f"Pipeline crashed: {exc}", exc_info=True)
        state["stage"] = "error"
        broadcast_event({"type": "error", "message": str(exc)})
    finally:
        state["is_running"] = False
        if state["start_time"]:
            state["elapsed_seconds"] = round(time.time() - state["start_time"], 1)




@app.get("/api/pipeline/status")
async def get_status():
    elapsed = round(time.time() - state["start_time"], 1) if state["is_running"] and state["start_time"] else state["elapsed_seconds"]
    return {
        **state,
        "elapsed_seconds": elapsed,
        "recent_logs": list(recent_logs)[-50:],
    }


@app.post("/api/pipeline/run")
async def trigger_run():
    if state["is_running"]:
        return JSONResponse(status_code=409, content={"status": "already_running", "message": "Pipeline is already running"})

    t = threading.Thread(target=pipeline_worker, daemon=True)
    t.start()
    return {"status": "started", "message": "AI Orbit Pipeline started in background"}


@app.post("/api/pipeline/stop")
async def stop_run():
    if not state["is_running"]:
        return JSONResponse(status_code=400, content={"status": "not_running", "message": "Pipeline is not currently running"})
    stop_event.set()
    logging.getLogger("pipeline").warning("Pipeline stop requested by user.")
    broadcast_event({
        "type": "stage",
        "stage": "stopping",
        "message": "Stopping pipeline... Cleanly finishing current operation."
    })
    return {"status": "stopping", "message": "Stop signal sent to pipeline worker"}


@app.get("/api/pipeline/stream")
async def stream_events():
    """SSE endpoint for live log and progress streaming."""
    q = asyncio.Queue()
    subscribers.append(q)

    async def event_generator():
        try:
            # Send initial sync event
            init_data = {
                "type": "init",
                "state": state,
                "recent_logs": list(recent_logs)[-30:],
            }
            yield f"data: {json.dumps(init_data)}\n\n"

            while True:
                data = await q.get()
                yield data
        except asyncio.CancelledError:
            pass
        finally:
            if q in subscribers:
                subscribers.remove(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/pipeline/entities")
async def get_entities():
    """Return the latest entities.json for local UI display."""
    path = "data/entities.json"
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})
    return []


@app.post("/api/pipeline/scrape-url")
async def scrape_single_url(req: ScrapeUrlRequest):
    raw_url = (req.url or "").strip()
    if not raw_url:
        return JSONResponse(status_code=400, content={"error": "URL is required"})

    clean_url = normalize_url(raw_url)
    parsed = urlparse(clean_url)
    if not clean_url or not clean_url.startswith("http") or not parsed.netloc or "." not in parsed.netloc:
        return JSONResponse(status_code=400, content={"error": "Invalid HTTP/HTTPS URL"})

    log = logging.getLogger("pipeline")
    log.info("Single URL scrape requested: %s", clean_url)

    # 1. Build initial candidate
    cand = Candidate(
        name=req.name.strip() if req.name else "",
        url=clean_url,
        description="",
        category_hint=req.category_hint or "",
        source_name="Direct URL Ingestion",
        source_url=clean_url,
    )

    # 2. Enrich from website (metadata, pricing, features, logo, live probe)
    try:
        enrich_from_official_site(cand)
    except Exception as exc:
        log.warning("Enrichment error for %s: %s", clean_url, exc)

    cand.description = clean_description(cand.description)
    if len(cand.description) < 30 and getattr(cand, "features", None):
        feat_text = ". ".join(cand.features[:2])
        cand.description = clean_description(f"{cand.description} — {feat_text}".strip(" —"))
    if len(cand.description) < 30:
        cand.description = clean_description(
            f"{cand.name or 'AI Tool'} — AI powered platform and tool for {cand.category_hint or 'automation and productivity'}."
        )

    # 3. Entity resolution & classification
    resolver = EntityResolver()
    entity, action = resolver.resolve(cand)
    entity.categories = categorize(entity)
    entity.id = stable_uuid(entity.entity_type, entity.url)

    # 4. Data quality validation
    report = run_validation([entity])

    # 5. Incremental export to Supabase (exact schema, upsert on conflict)
    try:
        export_to_supabase([entity], [], report)
    except Exception as err:
        log.warning("Supabase upsert note for %s: %s", entity.name, err)

    # 6. Cumulative local storage
    try:
        cumulative = export_entities([entity])
        export_sheets_csv(cumulative)
    except Exception as err:
        log.warning("Local export warning: %s", err)

    result = {
        "id": entity.id,
        "name": entity.name,
        "entity_type": entity.entity_type,
        "description": entity.description,
        "url": entity.url,
        "logo_url": entity.logo_url,
        "categories": entity.categories,
        "aliases": sorted(entity.aliases),
        "pricing": getattr(entity, "pricing", ""),
        "features": getattr(entity, "features", []),
        "social_links": getattr(entity, "social_links", {}),
        "open_source": getattr(entity, "open_source", False),
        "verified": entity.verified,
        "http_status": entity.http_status,
        "last_verified": entity.last_verified,
        "source": entity.source,
    }

    log.info("Successfully scraped & ingested single URL: %s (%s)", entity.name, entity.url)
    return result


@app.get("/api/pipeline/directory-status")
async def get_directory_status():
    """Return status of directory scraping operation."""
    return dir_scrape_state


@app.post("/api/pipeline/scrape-directory")
async def start_directory_scrape(req: DirectoryScrapeRequest):
    """Trigger a batch directory scrape (e.g. AgentHunter.io) in background with progress."""
    if dir_scrape_state["is_running"]:
        return JSONResponse(status_code=409, content={"error": "A directory scrape is already in progress"})

    dir_stop_event.clear()
    dir_scrape_state["is_running"] = True
    dir_scrape_state["total"] = 0
    dir_scrape_state["completed"] = 0
    dir_scrape_state["extracted"] = 0
    dir_scrape_state["percent"] = 0.0
    dir_scrape_state["last_tool"] = "Starting..."
    dir_scrape_state["status"] = "running"
    dir_scrape_state["error"] = None

    limit_val = req.limit
    workers_val = req.workers or 25
    domain_slug = urlparse(req.url).netloc.replace(".", "_") or "site"
    output_filename = f"{domain_slug}_tools_{limit_val if limit_val else 'full'}.xlsx"
    output_path = os.path.join("data", "export", output_filename)
    dir_scrape_state["output_xlsx"] = output_filename
    dir_scrape_state["output_csv"] = output_filename.replace(".xlsx", ".csv")

    def run_worker():
        from src.scrapers.universal_scraper import run_universal_scraper
        try:
            def on_dir_progress(ev):
                dir_scrape_state["total"] = ev.get("total", dir_scrape_state["total"])
                dir_scrape_state["completed"] = ev.get("completed", dir_scrape_state["completed"])
                dir_scrape_state["extracted"] = ev.get("extracted", dir_scrape_state["extracted"])
                dir_scrape_state["percent"] = ev.get("percent", dir_scrape_state["percent"])
                dir_scrape_state["last_tool"] = ev.get("last_tool", dir_scrape_state["last_tool"])
                dir_scrape_state["status"] = ev.get("status", dir_scrape_state["status"])
                broadcast_event({"type": "directory_progress", **dir_scrape_state})

            run_universal_scraper(
                target_url=req.url,
                limit=limit_val,
                max_workers=workers_val,
                output_file=output_path,
                progress_callback=on_dir_progress,
                stop_check=dir_stop_event.is_set
            )
            dir_scrape_state["status"] = "completed"
        except Exception as exc:
            logging.getLogger("pipeline").error(f"Universal scrape error: {exc}", exc_info=True)
            dir_scrape_state["status"] = "error"
            dir_scrape_state["error"] = str(exc)
        finally:
            dir_scrape_state["is_running"] = False
            broadcast_event({"type": "directory_status", **dir_scrape_state})

    t = threading.Thread(target=run_worker, daemon=True)
    t.start()
    return {"status": "started", "message": f"Universal scraping started for {req.url}", "target_file": output_filename}


@app.post("/api/pipeline/stop-directory")
async def stop_directory_scrape():
    """Stop active directory scrape cleanly."""
    if not dir_scrape_state["is_running"]:
        return JSONResponse(status_code=400, content={"error": "No directory scrape is running"})
    dir_stop_event.set()
    dir_scrape_state["status"] = "stopping"
    return {"status": "stopping", "message": "Stop signal sent to directory scraper"}


@app.get("/api/competitions")
async def get_competitions():
    """Return all stored competition opportunities from SQLite database."""
    try:
        from internatlas.competitions.schema import init_db
        from internatlas.competitions.processing.dedupe import fetch_all
        conn = init_db()
        records = fetch_all(conn)
        conn.close()
        return records
    except Exception as e:
        logging.getLogger("pipeline").warning(f"Error reading competitions DB: {e}")
        return []


@app.get("/api/competitions/status")
async def get_competitions_status():
    """Return status of competition scraping operation."""
    return competitions_state


@app.post("/api/competitions/run")
async def trigger_competitions_run(req: CompetitionRunRequest):
    """Trigger InternAtlas competitions scraping pipeline (Unstop, Devfolio, static hackathons)."""
    if competitions_state["is_running"]:
        return JSONResponse(status_code=409, content={"error": "Competitions pipeline is already running"})

    competitions_state["is_running"] = True
    competitions_state["status"] = "running"
    competitions_state["error"] = None

    def run_worker():
        from internatlas.competitions.pipeline import run_competitions_pipeline
        from internatlas.competitions.main import demo_data
        from internatlas.competitions.schema import init_db
        from internatlas.competitions.processing.dedupe import fetch_all

        try:
            broadcast_event({"type": "competitions_start", "message": "Competitions pipeline started"})
            raw = demo_data() if req.demo else None
            excel_path = run_competitions_pipeline(
                verbose=True,
                linkcheck=not req.no_linkcheck,
                only=req.only,
                raw_override=raw
            )
            conn = init_db()
            all_records = fetch_all(conn)
            conn.close()

            competitions_state["total"] = len(all_records)
            competitions_state["live"] = len([r for r in all_records if r.get("status") == "live"])
            competitions_state["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
            competitions_state["status"] = "completed"
            competitions_state["summary"] = {
                "excel_path": str(excel_path),
                "excel_file": os.path.basename(str(excel_path)),
                "total": len(all_records),
                "live": len([r for r in all_records if r.get("status") == "live"])
            }
            broadcast_event({"type": "competitions_complete", **competitions_state})
        except Exception as exc:
            logging.getLogger("pipeline").error(f"Competitions pipeline error: {exc}", exc_info=True)
            competitions_state["status"] = "error"
            competitions_state["error"] = str(exc)
            broadcast_event({"type": "competitions_error", "error": str(exc)})
        finally:
            competitions_state["is_running"] = False

    t = threading.Thread(target=run_worker, daemon=True)
    t.start()
    return {"status": "started", "message": "Competitions pipeline started in background"}


@app.get("/api/competitions/download")
async def download_competitions_excel():
    """Download latest exported competitions Excel file."""
    try:
        from internatlas.competitions import config as comp_config
        export_dir = comp_config.EXPORT_DIR
        files = sorted(list(export_dir.glob("*.xlsx")), key=lambda f: f.stat().st_mtime, reverse=True)
        if not files:
            return JSONResponse(status_code=404, content={"error": "No competition Excel files found. Run the pipeline first."})
        latest_file = files[0]
        return FileResponse(
            latest_file,
            filename=latest_file.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ── Substack Early Career & Internships Endpoints ─────────────────────

@app.get("/api/substack/jobs")
async def get_substack_jobs():
    """Return all stored Substack internship listings, grouped sections, and Substack Markdown preview."""
    try:
        from internatlas.substack.schema import init_db, fetch_all_jobs, upsert_jobs
        from internatlas.substack.scrapers import get_verified_seed_roles
        from internatlas.substack.processor import organize_for_substack
        from internatlas.substack.exporter import (
            build_substack_metadata,
            generate_substack_markdown,
            export_substack_docx,
            export_substack_xlsx,
        )

        conn = init_db()
        jobs = fetch_all_jobs(conn)
        if not jobs:
            # Auto-seed initial verified direct career portal listings on first load
            seeded = organize_for_substack(get_verified_seed_roles())
            upsert_jobs(conn, seeded)
            jobs = fetch_all_jobs(conn)
            export_substack_docx(jobs)
            export_substack_xlsx(jobs)
        conn.close()

        meta = build_substack_metadata(jobs)
        markdown_text = generate_substack_markdown(jobs)
        return {
            "jobs": jobs,
            "title": meta["title"],
            "subtitle": meta["subtitle"],
            "date_str": meta["date_str"],
            "total": len(jobs),
            "sections": meta["sections"],
            "markdown": markdown_text,
        }
    except Exception as e:
        logging.getLogger("pipeline").warning(f"Error reading Substack DB: {e}")
        return {"jobs": [], "sections": {}, "markdown": "", "total": 0, "error": str(e)}


@app.get("/api/substack/status")
async def get_substack_status():
    """Return status of Substack ATS scraper."""
    return substack_state


@app.post("/api/substack/run")
async def trigger_substack_run(req: SubstackRunRequest):
    """Trigger live multi-ATS scraping (Greenhouse, Lever, Ashby, SmartRecruiters, Workday) + Word (.docx) export."""
    if substack_state["is_running"]:
        return JSONResponse(status_code=409, content={"error": "Substack pipeline is already running"})

    substack_state["is_running"] = True
    substack_state["status"] = "running"
    substack_state["error"] = None
    substack_state["completed_boards"] = 0
    substack_state["total_boards"] = 0

    def run_worker():
        from internatlas.substack.pipeline import run_substack_pipeline

        def on_progress(ev):
            substack_state["completed_boards"] = ev.get("completed", 0)
            substack_state["total_boards"] = ev.get("total", 0)
            substack_state["last_company"] = ev.get("last_company")
            broadcast_event({"type": "substack_progress", **substack_state})

        try:
            broadcast_event({"type": "substack_start", "message": "Substack ATS scraper started"})
            summary = run_substack_pipeline(
                include_seed=req.include_seed,
                progress_cb=on_progress,
                verbose=True,
            )
            substack_state["total"] = summary["total"]
            substack_state["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
            substack_state["status"] = "completed"
            substack_state["summary"] = {
                "total": summary["total"],
                "docx_file": summary["docx_file"],
                "xlsx_file": summary["xlsx_file"],
                "title": summary["title"],
            }
            broadcast_event({"type": "substack_complete", **substack_state})
        except Exception as exc:
            logging.getLogger("pipeline").error(f"Substack pipeline error: {exc}", exc_info=True)
            substack_state["status"] = "error"
            substack_state["error"] = str(exc)
            broadcast_event({"type": "substack_error", "error": str(exc)})
        finally:
            substack_state["is_running"] = False

    t = threading.Thread(target=run_worker, daemon=True)
    t.start()
    return {"status": "started", "message": "Substack multi-ATS scraper started in background"}


@app.get("/api/substack/download-docx")
async def download_substack_docx():
    """Download latest formatted Substack Word (.docx) document."""
    try:
        from internatlas.substack import config as sub_config
        from internatlas.substack.schema import init_db, fetch_all_jobs
        from internatlas.substack.exporter import export_substack_docx

        export_dir = sub_config.EXPORT_DIR
        files = sorted(list(export_dir.glob("*.docx")), key=lambda f: f.stat().st_mtime, reverse=True)
        if not files:
            conn = init_db()
            jobs = fetch_all_jobs(conn)
            conn.close()
            latest_file = export_substack_docx(jobs)
        else:
            latest_file = files[0]

        return FileResponse(
            latest_file,
            filename=latest_file.name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/substack/download-xlsx")
async def download_substack_xlsx():
    """Download latest exported Substack Excel (.xlsx) file."""
    try:
        from internatlas.substack import config as sub_config
        from internatlas.substack.schema import init_db, fetch_all_jobs
        from internatlas.substack.exporter import export_substack_xlsx

        export_dir = sub_config.EXPORT_DIR
        files = sorted(list(export_dir.glob("*.xlsx")), key=lambda f: f.stat().st_mtime, reverse=True)
        if not files:
            conn = init_db()
            jobs = fetch_all_jobs(conn)
            conn.close()
            latest_file = export_substack_xlsx(jobs)
        else:
            latest_file = files[0]

        return FileResponse(
            latest_file,
            filename=latest_file.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/pipeline/download")
async def download_file(file: str):
    """Download an exported Excel or CSV file directly."""
    safe_name = os.path.basename(file)
    file_path = os.path.join("data", "export", safe_name)
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": f"File '{safe_name}' not found"})
    media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if safe_name.endswith(".xlsx")
        else "text/csv"
    )
    return FileResponse(file_path, filename=safe_name, media_type=media_type)


# ─────────────────────────────────────────────
# Flerken Studio Bot Module Endpoints
# ─────────────────────────────────────────────
import sys
from pathlib import Path
from typing import Any, Dict

FLERKEN_BOT_ROOT = Path(__file__).resolve().parent / "flerken-studio-bot"
FLERKEN_BOT_SRC = str(FLERKEN_BOT_ROOT / "src")
if FLERKEN_BOT_SRC not in sys.path:
    sys.path.insert(0, FLERKEN_BOT_SRC)

FLERKEN_CONFIG_PATH = FLERKEN_BOT_ROOT / "config" / "sources.yaml"
FLERKEN_OUTPUT_DIR = FLERKEN_BOT_ROOT / "output"
FLERKEN_STATE_DB = FLERKEN_BOT_ROOT / "state" / "seen.sqlite3"

flerken_bot_state = {
    "is_running": False,
    "status": "idle",
    "last_run": None,
    "error": None,
    "verified_count": 0,
    "review_count": 0,
    "latest_file": None,
}


class FlerkenRunRequest(BaseModel):
    ignore_seen: bool = False
    max_jobs: int = 60
    early_career_only: bool = True
    create_draft: bool = False


class FlerkenSourceActionRequest(BaseModel):
    action: str  # "toggle", "add", "delete", "update_settings"
    index: Optional[int] = None
    enabled: Optional[bool] = None
    source: Optional[Dict[str, Any]] = None
    collection: Optional[Dict[str, Any]] = None
    publication: Optional[Dict[str, Any]] = None


def _read_flerken_state() -> Dict[str, Any]:
    import yaml
    from flerken_bot.quality import SeenStore

    FLERKEN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = {}
    if FLERKEN_CONFIG_PATH.exists():
        cfg = yaml.safe_load(FLERKEN_CONFIG_PATH.read_text(encoding="utf-8")) or {}

    store = SeenStore(FLERKEN_STATE_DB)
    seen_count = store.count()

    md_files = sorted(
        [f for f in FLERKEN_OUTPUT_DIR.glob("*.md") if f.name != "latest_issue.md"],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    latest_canonical = FLERKEN_OUTPUT_DIR / "latest_issue.md"
    if latest_canonical.exists() and latest_canonical.stat().st_size > 0:
        latest_md_path = latest_canonical
    else:
        latest_md_path = md_files[0] if md_files else None

    latest_markdown = ""
    latest_filename = None
    if latest_md_path and latest_md_path.exists():
        latest_markdown = latest_md_path.read_text(encoding="utf-8")
        latest_filename = latest_md_path.name

    verified_jobs = []
    verified_path = FLERKEN_OUTPUT_DIR / "verified_jobs.json"
    if verified_path.exists():
        try:
            verified_jobs = json.loads(verified_path.read_text(encoding="utf-8"))
        except Exception:
            verified_jobs = []

    review_queue = []
    review_path = FLERKEN_OUTPUT_DIR / "review_queue.json"
    if review_path.exists():
        try:
            review_queue = json.loads(review_path.read_text(encoding="utf-8"))
        except Exception:
            review_queue = []

    return {
        "bot_status": flerken_bot_state,
        "config": cfg,
        "seen_count": seen_count,
        "latest_markdown": latest_markdown,
        "latest_filename": latest_filename,
        "verified_jobs": verified_jobs,
        "review_queue": review_queue,
        "issues": [
            {
                "name": f.name,
                "size_kb": round(f.stat().st_size / 1024, 1),
                "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.stat().st_mtime)),
            }
            for f in md_files[:15]
        ],
    }


@app.get("/api/flerken-bot/state")
async def get_flerken_bot_state():
    """Return full Flerken Studio Bot state, latest Markdown issue, verified jobs, review queue, and sources."""
    try:
        return _read_flerken_state()
    except Exception as exc:
        logging.getLogger("pipeline").error(f"Flerken bot state error: {exc}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.post("/api/flerken-bot/run")
async def trigger_flerken_bot_run(req: FlerkenRunRequest):
    """Trigger Flerken Studio Bot collection, HTTP link verification, categorization, and Markdown/Word issue generation."""
    if flerken_bot_state["is_running"]:
        return JSONResponse(status_code=409, content={"error": "Flerken Studio Bot is already running"})

    flerken_bot_state["is_running"] = True
    flerken_bot_state["status"] = "running"
    flerken_bot_state["error"] = None

    def worker():
        import importlib
        import flerken_bot.models
        import flerken_bot.sources
        import flerken_bot.quality
        import flerken_bot.render
        import flerken_bot.cli

        importlib.reload(flerken_bot.models)
        importlib.reload(flerken_bot.sources)
        importlib.reload(flerken_bot.quality)
        importlib.reload(flerken_bot.render)
        importlib.reload(flerken_bot.cli)

        flerken_run = flerken_bot.cli.run
        create_substack_draft = flerken_bot.cli.create_substack_draft
        load_config = flerken_bot.cli.load_config

        try:
            broadcast_event({"type": "flerken_start", "message": "Flerken Studio Bot started"})
            md_path = flerken_run(
                config_path=str(FLERKEN_CONFIG_PATH),
                output_dir=str(FLERKEN_OUTPUT_DIR),
                state_db=str(FLERKEN_STATE_DB),
                dry_run=not req.create_draft,
                ignore_seen=req.ignore_seen,
                max_jobs_override=req.max_jobs,
                early_career_only=req.early_career_only,
            )
            state_snapshot = _read_flerken_state()
            flerken_bot_state["verified_count"] = len(state_snapshot["verified_jobs"])
            flerken_bot_state["review_count"] = len(state_snapshot["review_queue"])
            flerken_bot_state["latest_file"] = md_path.name if md_path else state_snapshot["latest_filename"]
            flerken_bot_state["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
            flerken_bot_state["status"] = "completed"

            if md_path and req.create_draft:
                cfg = load_config(FLERKEN_CONFIG_PATH)
                pub_url = os.getenv(
                    "PUBLICATION_URL",
                    str(cfg.get("publication", {}).get("url", "https://flerkenstudio.substack.com/")),
                )
                create_substack_draft(md_path, pub_url)

            broadcast_event({"type": "flerken_complete", **flerken_bot_state})
        except Exception as exc:
            logging.getLogger("pipeline").error(f"Flerken Studio Bot error: {exc}", exc_info=True)
            flerken_bot_state["status"] = "error"
            flerken_bot_state["error"] = str(exc)
            broadcast_event({"type": "flerken_error", "error": str(exc)})
        finally:
            flerken_bot_state["is_running"] = False

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return {"status": "started", "message": "Flerken Studio Bot started in background"}


@app.post("/api/flerken-bot/sources")
async def update_flerken_sources(req: FlerkenSourceActionRequest):
    """Toggle, add, or delete sources or update collection settings in flerken-studio-bot/config/sources.yaml."""
    import yaml

    try:
        cfg = yaml.safe_load(FLERKEN_CONFIG_PATH.read_text(encoding="utf-8")) or {}
        sources = cfg.get("sources", [])

        if req.action == "toggle" and req.index is not None and 0 <= req.index < len(sources):
            sources[req.index]["enabled"] = bool(
                req.enabled if req.enabled is not None else not sources[req.index].get("enabled", False)
            )
        elif req.action == "add" and req.source:
            new_src = dict(req.source)
            new_src.setdefault("enabled", True)
            sources.insert(0, new_src)
        elif req.action == "delete" and req.index is not None and 0 <= req.index < len(sources):
            sources.pop(req.index)
        elif req.action == "update_settings":
            if req.collection:
                cfg.setdefault("collection", {}).update(req.collection)
            if req.publication:
                cfg.setdefault("publication", {}).update(req.publication)
        else:
            return JSONResponse(status_code=400, content={"error": "Invalid source action or parameters"})

        cfg["sources"] = sources
        FLERKEN_CONFIG_PATH.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return {"status": "ok", "config": cfg}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.post("/api/flerken-bot/reset-seen")
async def reset_flerken_seen():
    """Clear the SQLite SeenStore ledger so previously drafted roles can be drafted again."""
    try:
        from flerken_bot.quality import SeenStore

        store = SeenStore(FLERKEN_STATE_DB)
        store.clear()
        return {"status": "ok", "seen_count": store.count()}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


class FlerkenDraftRequest(BaseModel):
    cookies_string: Optional[str] = None


@app.post("/api/flerken-bot/create-draft")
async def create_flerken_substack_draft(req: Optional[FlerkenDraftRequest] = None):
    """Create an unpublished Substack draft from the latest generated Markdown issue."""
    try:
        from flerken_bot.cli import create_substack_draft, load_config

        cookies_str = req.cookies_string.strip() if (req and req.cookies_string) else None
        if cookies_str:
            env_file = FLERKEN_BOT_ROOT / ".env"
            lines = []
            if env_file.exists():
                lines = [
                    ln for ln in env_file.read_text(encoding="utf-8").splitlines()
                    if not ln.startswith("COOKIES_STRING=")
                ]
            lines.append(f'COOKIES_STRING="{cookies_str}"')
            env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        latest_canonical = FLERKEN_OUTPUT_DIR / "latest_issue.md"
        if latest_canonical.exists() and latest_canonical.stat().st_size > 0:
            target = latest_canonical
        else:
            md_files = sorted(
                [f for f in FLERKEN_OUTPUT_DIR.glob("*.md") if f.name != "latest_issue.md"],
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            target = md_files[0] if md_files else None

        if not target or not target.exists():
            return JSONResponse(status_code=404, content={"error": "No Markdown issue generated yet. Run the bot first."})

        cfg = load_config(FLERKEN_CONFIG_PATH)
        pub_url = os.getenv(
            "PUBLICATION_URL",
            str(cfg.get("publication", {}).get("url", "https://flerkenstudio.substack.com/")),
        )
        create_substack_draft(target, pub_url, cookies_string=cookies_str)
        return {"status": "ok", "message": f"Created unpublished Substack draft for {pub_url} from {target.name}"}
    except Exception as exc:
        err_msg = str(exc)
        return JSONResponse(
            status_code=400,
            content={
                "error": err_msg,
                "auth_required": "AUTH_REQUIRED" in err_msg,
            },
        )


@app.get("/api/flerken-bot/download/{fmt}")
async def download_flerken_bot_output(fmt: str):
    """Download the latest Flerken Studio Bot output (.md, .docx, or review_queue.json)."""
    FLERKEN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if fmt == "md":
        md_files = sorted(
            [f for f in FLERKEN_OUTPUT_DIR.glob("*.md") if f.name != "latest_issue.md"],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        target = md_files[0] if md_files else (FLERKEN_OUTPUT_DIR / "latest_issue.md")
        if not target.exists():
            return JSONResponse(status_code=404, content={"error": "No Markdown issue found. Run the bot first."})
        return FileResponse(target, filename=target.name, media_type="text/markdown; charset=utf-8")

    if fmt == "docx":
        docx_files = sorted(
            [f for f in FLERKEN_OUTPUT_DIR.glob("*.docx") if f.name != "latest_issue.docx"],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        target = docx_files[0] if docx_files else (FLERKEN_OUTPUT_DIR / "latest_issue.docx")
        if not target.exists():
            return JSONResponse(status_code=404, content={"error": "No Word (.docx) issue found. Run the bot first."})
        return FileResponse(
            target,
            filename=target.name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    if fmt == "review":
        target = FLERKEN_OUTPUT_DIR / "review_queue.json"
        if not target.exists():
            return JSONResponse(status_code=404, content={"error": "No review_queue.json found."})
        return FileResponse(target, filename="review_queue.json", media_type="application/json")

    return JSONResponse(status_code=400, content={"error": f"Unsupported format: {fmt}"})


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)





