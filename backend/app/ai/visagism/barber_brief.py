"""Grounded barber brief for any persisted recommended haircut."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .interpretation import _barber_guidance, _clean_text, _face_shape_label


def build_barber_brief_for_haircut(
    analysis: Dict[str, Any], haircut_name: str
) -> Optional[Dict[str, Any]]:
    source: Dict[str, Any] = analysis if isinstance(analysis, dict) else {}
    hairstyles = [
        item.strip()
        for item in source.get("recommended_hairstyles", [])
        if isinstance(item, str) and item.strip()
    ]
    if haircut_name not in hairstyles:
        return None

    measured_value = source.get("measured_data_used")
    current_hair_value = source.get("current_hair")
    measured: Dict[str, Any] = (
        dict(measured_value) if isinstance(measured_value, dict) else {}
    )
    current_hair: Dict[str, Any] = (
        dict(current_hair_value) if isinstance(current_hair_value, dict) else {}
    )
    guidance = _barber_guidance(haircut_name, current_hair)

    grounded_in: List[str] = []
    face_shape = _face_shape_label(
        _clean_text(measured.get("face_shape"))
        or _clean_text(source.get("face_shape_category"))
    )
    density = _clean_text(measured.get("hair_density")) or _clean_text(
        current_hair.get("density")
    )
    hairline = _clean_text(measured.get("hairline")) or _clean_text(
        current_hair.get("hairline")
    )
    if face_shape:
        grounded_in.append(f"formato facial: {face_shape}")
    if density:
        grounded_in.append(f"densidade do cabelo: {density}")
    if hairline:
        grounded_in.append(f"linha frontal: {hairline}")

    return {
        "recommendation_name": haircut_name,
        "grounded_in": grounded_in,
        "top": guidance["top"],
        "sides": guidance["sides"],
        "back": guidance["back"],
        "fringe": guidance["fringe"],
        "texture": guidance["texture"],
        "finish": guidance["finish"],
        "avoid": guidance["avoid"],
        "note": (
            "As orientações descrevem o efeito visual do corte sem inventar "
            "comprimentos em cm/mm; o ajuste final deve ser feito no cabelo real."
        ),
    }
