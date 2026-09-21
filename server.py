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
from fastapi.responses import StreamingResponse, JSONResponse
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


app = FastAPI(title="AI Orbit Pipeline API")

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


@app.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()


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


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
