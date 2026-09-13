"""Deterministic UUIDv5 generation so re-runs keep the same entity IDs."""
import uuid


def stable_uuid(entity_type: str, canonical_url: str) -> str:
    key = f"{entity_type}:{canonical_url}".lower()
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))
