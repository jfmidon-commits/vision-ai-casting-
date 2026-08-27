"""Small JSONB metadata cache for approved visagism simulations.

Generated image bytes live in S3. Analysis.visagism stores only stable metadata
and object keys, so no migration or large base64 payload is required.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

CACHE_FIELD = "simulation_cache_v1"
PIPELINE_VERSION = "hair-p1-v1"


def cache_key(
    *, haircut_name: str, source_photo_id: str, provider: str, model: str
) -> str:
    raw = "|".join(
        (
            PIPELINE_VERSION,
            haircut_name.strip(),
            source_photo_id,
            provider.strip(),
            model.strip(),
        )
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def object_key(*, tenant_id: str, analysis_id: str, key: str) -> str:
    return f"visagism-simulations/{tenant_id}/{analysis_id}/{key}.png"


def entries(visagism: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(visagism, dict):
        return {}
    raw = visagism.get(CACHE_FIELD)
    if not isinstance(raw, dict):
        return {}
    return {str(k): dict(v) for k, v in raw.items() if isinstance(v, dict)}


def find_ready(
    visagism: Dict[str, Any],
    *,
    haircut_name: str,
    source_photo_id: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    matches = []
    for item in entries(visagism).values():
        if item.get("status") != "ready":
            continue
        if item.get("pipeline_version") != PIPELINE_VERSION:
            continue
        if item.get("haircut_name") != haircut_name:
            continue
        if item.get("source_photo_id") != source_photo_id:
            continue
        if provider is not None and item.get("provider") != provider:
            continue
        if model is not None and item.get("model") != model:
            continue
        if not item.get("object_key"):
            continue
        matches.append(item)
    if not matches:
        return None
    return sorted(
        matches,
        key=lambda item: str(item.get("created_at") or ""),
        reverse=True,
    )[0]


def ready_for_source(
    visagism: Dict[str, Any], *, source_photo_id: str
) -> Iterable[Dict[str, Any]]:
    items = [
        item
        for item in entries(visagism).values()
        if item.get("status") == "ready"
        and item.get("pipeline_version") == PIPELINE_VERSION
        and item.get("source_photo_id") == source_photo_id
        and item.get("object_key")
    ]
    return sorted(
        items,
        key=lambda item: str(item.get("created_at") or ""),
        reverse=True,
    )


def with_ready_entry(
    visagism: Dict[str, Any],
    *,
    key: str,
    haircut_name: str,
    source_photo_id: str,
    provider: str,
    model: str,
    stored_object_key: str,
    identity_score_min: float,
    mask_kind: Optional[str] = None,
) -> Dict[str, Any]:
    updated = dict(visagism) if isinstance(visagism, dict) else {}
    cache = entries(updated)
    cache[key] = {
        "status": "ready",
        "pipeline_version": PIPELINE_VERSION,
        "haircut_name": haircut_name,
        "source_photo_id": source_photo_id,
        "provider": provider,
        "model": model,
        "object_key": stored_object_key,
        "identity_score_min": float(identity_score_min),
        "mask_kind": mask_kind,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    updated[CACHE_FIELD] = cache
    return updated
