"""Grounded prompt builder for haircut-only image editing."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _clean(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or text.lower() in {"none", "null", "não medido", "nao medido"}:
        return None
    return text


def build_haircut_edit_instruction(haircut_name: str, visagism: Dict[str, Any]) -> str:
    source: Dict[str, Any] = visagism if isinstance(visagism, dict) else {}
    measured_value = source.get("measured_data_used")
    current_hair_value = source.get("current_hair")
    measured: Dict[str, Any] = (
        dict(measured_value) if isinstance(measured_value, dict) else {}
    )
    current_hair: Dict[str, Any] = (
        dict(current_hair_value) if isinstance(current_hair_value, dict) else {}
    )

    grounded_details: List[str] = []
    density = _clean(measured.get("hair_density")) or _clean(
        current_hair.get("density")
    )
    texture = _clean(measured.get("hair_texture")) or _clean(
        current_hair.get("texture")
    )
    hair_color = _clean(measured.get("hair_color")) or _clean(current_hair.get("color"))

    if density:
        grounded_details.append(f"visible measured hair density: {density}")
    if texture:
        grounded_details.append(f"visible measured hair texture: {texture}")
    if hair_color:
        grounded_details.append(f"confirmed current hair color: {hair_color}")

    details = (
        " Use only these confirmed hair observations: "
        + "; ".join(grounded_details)
        + "."
        if grounded_details
        else (
            " Do not invent hair density, texture, color, hairline, or length "
            "that cannot be inferred from the source image."
        )
    )

    return (
        "Edit only the hair inside the supplied hair mask. "
        "Keep every unmasked pixel unchanged. Preserve the exact person's "
        "identity and face geometry, expression, eyes, eyebrows, nose, mouth, "
        "teeth, ears, skin, beard, neck, body, clothing, and background. "
        f"Create a photorealistic haircut preview for: {haircut_name}. "
        "Respect the visible natural hairline, natural age cues, current hair "
        "tone, and the source photo. Never infer hair color from beard or "
        "eyebrows unless hair color was explicitly measured. Do not beautify, "
        "de-age, age, reshape, recolor skin, or modify the beard. The result is "
        "a haircut preview, not a new portrait." + details
    )
