"""Grounded prompt builder for haircut-only image editing."""

from __future__ import annotations

from typing import Any, Dict, List


def _clean(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or text.lower() in {"none", "null", "não medido", "nao medido"}:
        return None
    return text


def build_haircut_edit_instruction(haircut_name: str, visagism: Dict[str, Any]) -> str:
    source = visagism if isinstance(visagism, dict) else {}
    measured = (
        source.get("measured_data_used")
        if isinstance(source.get("measured_data_used"), dict)
        else {}
    )
    current_hair = (
        source.get("current_hair")
        if isinstance(source.get("current_hair"), dict)
        else {}
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
        "Respect the visible natural hairline and the source photo. Do not "
        "beautify, de-age, age, reshape, recolor skin, or modify the beard. "
        "The result is a haircut preview, not a new portrait."
        + details
    )
