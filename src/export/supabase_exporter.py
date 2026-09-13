"""Export pipeline results to Supabase (ai_tools + ai_relationships tables)."""
import logging
from datetime import datetime, timezone

from supabase import create_client

from src.config import SUPABASE_URL, SUPABASE_ANON_KEY

log = logging.getLogger("pipeline")


def _get_client():
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        log.warning("Supabase credentials missing — skipping Supabase export")
        return None
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def export_to_supabase(entities, relationships, report):
    """Push entities and relationships to Supabase. Returns run ID or None."""
    client = _get_client()
    if client is None:
        return None

    log.info("Exporting to Supabase (%d entities, %d relationships)...",
             len(entities), len(relationships))

    # 1. Create a pipeline run record
    run_data = {
        "status": "running",
        "entities_count": len(entities),
        "relationships_count": len(relationships),
        "validation_passed": report.get("passed", 0),
        "validation_failed": report.get("failed", 0),
        "report": report,
    }
    run_result = client.table("pipeline_runs").insert(run_data).execute()
    run_id = run_result.data[0]["id"] if run_result.data else None

    # 2. Clear old data and insert fresh entities
    try:
        client.table("ai_tools").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    except Exception as e:
        log.warning("Could not clear old ai_tools: %s", e)

    rows = []
    for e in entities:
        rows.append({
            "id": e.id,
            "entity_type": e.entity_type,
            "name": e.name,
            "description": e.description,
            "url": e.url,
            "logo_url": e.logo_url,
            "categories": e.categories,
            "aliases": sorted(e.aliases),
            "source_name": e.source.get("name", ""),
            "source_url": e.source.get("url", ""),
            "verified": e.verified,
            "http_status": e.http_status,
            "last_verified": e.last_verified or None,
        })

    # Insert in batches of 50
    batch_size = 50
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        try:
            client.table("ai_tools").upsert(batch, on_conflict="id").execute()
            log.info("  Upserted ai_tools batch %d-%d", i, i + len(batch))
        except Exception as exc:
            log.error("  Failed ai_tools batch %d: %s", i, exc)

    # 3. Clear old relationships and insert new ones
    try:
        client.table("ai_relationships").delete().neq("id", 0).execute()
    except Exception as e:
        log.warning("Could not clear old ai_relationships: %s", e)

    if relationships:
        rel_rows = [{"subject": r["subject"], "predicate": r["predicate"],
                     "object": r["object"]} for r in relationships]
        for i in range(0, len(rel_rows), batch_size):
            batch = rel_rows[i:i + batch_size]
            try:
                client.table("ai_relationships").insert(batch).execute()
                log.info("  Inserted ai_relationships batch %d-%d", i, i + len(batch))
            except Exception as exc:
                log.error("  Failed ai_relationships batch %d: %s", i, exc)

    # 4. Mark pipeline run as completed
    if run_id:
        client.table("pipeline_runs").update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", run_id).execute()

    log.info("Supabase export complete (run_id=%s)", run_id)
    return run_id
