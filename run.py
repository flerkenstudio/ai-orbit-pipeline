"""
AI Orbit Data Ingestion Pipeline — entry point.
Pipeline: Discovery -> Extraction -> Cleaning -> Deduplication ->
          Classification -> Relationships -> Validation -> Export
"""
import concurrent.futures
import logging
import os

from src.config import LOG_LEVEL, LOG_FILE
from src.discovery.registry import run_discovery
from src.extraction.site_crawler import enrich_from_official_site
from src.cleaning.text_cleaner import clean_description
from src.cleaning.url_normalizer import normalize_url
from src.deduplication.entity_resolver import EntityResolver
from src.utils.uuid_generator import stable_uuid
from src.classification.categorizer import categorize
from src.relationships.relationship_builder import build_relationships
from src.validation.quality_gate import run_validation
from src.export.exporters import (export_entities, export_relationships,
                                  export_sheets_csv, export_report,
                                  export_to_google_sheets_api)
from src.export.supabase_exporter import export_to_supabase


def _enrich_single_candidate(cand):
    try:
        enrich_from_official_site(cand)
        cand.description = clean_description(cand.description)
        if len(cand.description) < 30 and getattr(cand, "features", None):
            feat_text = ". ".join(cand.features[:2])
            cand.description = clean_description(f"{cand.description} — {feat_text}".strip(" —"))
        if len(cand.description) < 30:
            cand.description = clean_description(
                f"{cand.name} — AI powered platform and tool for {cand.category_hint or 'automation and productivity'}."
            )
    except Exception:
        pass
    return cand


def run_pipeline(progress_callback=None, stop_check=None):
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format="%(asctime)s %(levelname)-8s %(message)s",
        handlers=[logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
                  logging.StreamHandler()])

    log = logging.getLogger("pipeline")
    log.info("=== AI Orbit Pipeline starting ===")
    if progress_callback:
        progress_callback({"type": "stage", "stage": "discovery", "message": "Starting discovery across Seed, GitHub, Hacker News, Hugging Face, Awesome Lists..."})

    if stop_check and stop_check():
        log.warning("Pipeline run cancelled before discovery.")
        return {"stopped": True}

    # 1. DISCOVERY (multi-source, API-first)
    candidates = run_discovery()
    if not candidates:
        log.error("No candidates found — check network/API keys.")
        if progress_callback:
            progress_callback({"type": "error", "message": "No candidates found — check network/API keys."})
        return

    if stop_check and stop_check():
        log.warning("Pipeline run stopped after discovery.")
        if progress_callback:
            progress_callback({"type": "stopped", "stage": "stopped", "message": "Pipeline stopped by user."})
        return {"stopped": True}

    # Deduplicate candidate URLs before crawling (save bandwidth)
    seen_urls = set()
    unique_cands = []
    for c in candidates:
        c.url = normalize_url(c.url)
        key = c.url.rstrip("/").lower()
        if key and key not in seen_urls:
            seen_urls.add(key)
            unique_cands.append(c)
    log.info("Unique candidate URLs: %d", len(unique_cands))

    if progress_callback:
        progress_callback({
            "type": "discovery_done",
            "stage": "extraction",
            "total_candidates": len(candidates),
            "unique_count": len(unique_cands),
            "message": f"Discovered {len(candidates)} candidates ({len(unique_cands)} unique domains). Starting deep enrichment..."
        })

    # 2-3. EXTRACTION + CLEANING (parallel official-site verification)
    resolver = EntityResolver()
    total_cands = len(unique_cands)
    processed_count = 0
    max_workers = min(25, max(4, (os.cpu_count() or 4) * 4))

    log.info("Starting parallel enrichment of %d candidates across %d worker threads...",
             total_cands, max_workers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_cand = {executor.submit(_enrich_single_candidate, c): c for c in unique_cands}
        for future in concurrent.futures.as_completed(future_to_cand):
            if stop_check and stop_check():
                log.warning("Pipeline run stopped by user request at %d/%d.", processed_count, total_cands)
                executor.shutdown(wait=False, cancel_futures=True)
                if progress_callback:
                    progress_callback({
                        "type": "stopped",
                        "stage": "stopped",
                        "message": f"Pipeline stopped by user at tool {processed_count}/{total_cands}."
                    })
                return {
                    "entities_count": len(resolver.by_domain),
                    "stopped": True
                }

            processed_count += 1
            cand = future_to_cand[future]
            try:
                enriched_cand = future.result()
            except Exception:
                enriched_cand = cand

            entity, action = resolver.resolve(enriched_cand)
            log.debug("%-30s -> %s", enriched_cand.name[:30], action)

            if progress_callback and (processed_count % 2 == 0 or processed_count == total_cands):
                progress_callback({
                    "type": "progress",
                    "stage": "extraction",
                    "current": processed_count,
                    "total": total_cands,
                    "percent": round((processed_count / total_cands) * 100, 1),
                    "tool": {
                        "name": enriched_cand.name,
                        "url": enriched_cand.url,
                        "logo_url": getattr(enriched_cand, "logo_url", ""),
                        "pricing": getattr(enriched_cand, "pricing", ""),
                        "verified": enriched_cand.verified,
                        "http_status": enriched_cand.http_status,
                    },
                    "message": f"[{processed_count}/{total_cands}] Enriched {enriched_cand.name} ({getattr(enriched_cand, 'pricing', '')})"
                })

    entities = list(resolver.by_domain.values())

    # 4. CLASSIFICATION
    if progress_callback:
        progress_callback({"type": "stage", "stage": "classification", "message": "Classifying entities into taxonomy categories..."})
    for e in entities:
        e.categories = categorize(e)

    # 5. STABLE IDs (assign after resolution so merges keep one ID)
    for e in entities:
        e.id = stable_uuid(e.entity_type, e.url)

    # 6. RELATIONSHIPS
    relationships = build_relationships(
        [{"id": e.id, "categories": e.categories, "_org": None}
         for e in entities])

    # 7. VALIDATION
    if progress_callback:
        progress_callback({"type": "stage", "stage": "validation", "message": "Running data quality gate validation..."})
    report = run_validation(entities)

    # 8. EXPORT
    if progress_callback:
        progress_callback({"type": "stage", "stage": "export", "message": "Exporting CSV, JSON, and syncing to Supabase..."})
    print("\n" + "=" * 60)
    print(f"Entities created : {len(entities)}")
    print(f"Relationships    : {len(relationships)}")
    print(f"Validation       : {report['passed']}/{report['total']} passed")
    for issue, names in report["issues"].items():
        print(f"  - {issue}: {len(names)} records")
    print("=" * 60)

    cumulative_entities = export_entities(entities)
    export_relationships(relationships)
    export_sheets_csv(cumulative_entities)
    try:
        export_to_google_sheets_api(entities)
    except Exception as gerr:
        log.warning("Google Sheets sync skipped: %s", gerr)
    export_report(report)

    # Sync to Supabase
    run_id = export_to_supabase(entities, relationships, report)
    if run_id:
        print(f"\n  Supabase synced (run #{run_id})")
    else:
        print("\n  Supabase sync skipped (no credentials or error)")

    if progress_callback:
        progress_callback({
            "type": "completed",
            "stage": "completed",
            "entities_count": len(entities),
            "relationships_count": len(relationships),
            "passed": report["passed"],
            "total": report["total"],
            "supabase_run_id": run_id,
            "message": f"Pipeline complete: {len(entities)} entities created, {report['passed']}/{report['total']} passed validation."
        })

    return {
        "entities_count": len(entities),
        "relationships_count": len(relationships),
        "report": report,
        "supabase_run_id": run_id
    }


def main():
    run_pipeline()


if __name__ == "__main__":
    main()
