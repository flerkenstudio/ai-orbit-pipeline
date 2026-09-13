"""Build relationships.json — Tool solves Task (and Company develops Tool when known)."""
from src.utils.uuid_generator import stable_uuid


def build_relationships(entities: list) -> list:
    rels = []
    for e in entities:
        # Tool -> solves -> Task (one task per primary category)
        for cat in e.get("categories", [])[:1]:
            if cat and cat != "Other":
                task_id = stable_uuid("Task", f"task:{cat.lower()}")
                rels.append({"subject": e["id"], "predicate": "solves",
                             "object": task_id})
        # Company inference: populated when a source explicitly names one
        org = e.get("_org")
        if org:
            rels.append({"subject": org, "predicate": "develops",
                         "object": e["id"]})
    return rels
