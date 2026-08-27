from __future__ import annotations

from typing import Any, Dict, List, Sequence


_METRIC_LABELS = {
    "coverage_score": "cobertura",
    "volume_score": "volume",
    "texture_score": "textura visual",
    "neatness_score": "organização",
}

# Conservative compatibility targets. They do not infer hairstyle from
# demographics; they only rank haircut candidates against measurements
# produced from the current session.
_STYLE_PROFILES: Dict[str, Dict[str, float]] = {
    "Quiff texturizado": {
        "coverage_score": 0.75,
        "volume_score": 0.80,
        "texture_score": 0.80,
        "neatness_score": 0.55,
    },
    "Side Part com volume no topo": {
        "coverage_score": 0.70,
        "volume_score": 0.60,
        "texture_score": 0.45,
        "neatness_score": 0.80,
    },
    "Pompadour moderado": {
        "coverage_score": 0.85,
        "volume_score": 0.90,
        "texture_score": 0.35,
        "neatness_score": 0.70,
    },
    "Undercut com topo alongado": {
        "coverage_score": 0.80,
        "volume_score": 0.70,
        "texture_score": 0.65,
        "neatness_score": 0.55,
    },
    "Crew Cut com laterais mais baixas": {
        "coverage_score": 0.60,
        "volume_score": 0.35,
        "texture_score": 0.35,
        "neatness_score": 0.80,
    },
    "Taper baixo com topo texturizado": {
        "coverage_score": 0.70,
        "volume_score": 0.60,
        "texture_score": 0.75,
        "neatness_score": 0.65,
    },
    "French Crop texturizado": {
        "coverage_score": 0.65,
        "volume_score": 0.45,
        "texture_score": 0.75,
        "neatness_score": 0.65,
    },
    "Textured Crop": {
        "coverage_score": 0.65,
        "volume_score": 0.50,
        "texture_score": 0.80,
        "neatness_score": 0.55,
    },
    "Taper clássico": {
        "coverage_score": 0.60,
        "volume_score": 0.40,
        "texture_score": 0.40,
        "neatness_score": 0.85,
    },
    "Camadas médias com movimento": {
        "coverage_score": 0.75,
        "volume_score": 0.75,
        "texture_score": 0.80,
        "neatness_score": 0.50,
    },
    "Side Part clássico": {
        "coverage_score": 0.65,
        "volume_score": 0.50,
        "texture_score": 0.40,
        "neatness_score": 0.85,
    },
    "French Crop": {
        "coverage_score": 0.60,
        "volume_score": 0.40,
        "texture_score": 0.65,
        "neatness_score": 0.70,
    },
    "Crew Cut": {
        "coverage_score": 0.55,
        "volume_score": 0.30,
        "texture_score": 0.30,
        "neatness_score": 0.85,
    },
}

_EXTRA_CANDIDATES = [
    "Taper baixo com topo texturizado",
    "French Crop texturizado",
    "Textured Crop",
    "Taper clássico",
    "Camadas médias com movimento",
]


def _bounded_score(value: Any) -> float | None:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score < 0.0 or score > 1.0:
        return None
    return score


def _bucket(value: float) -> str:
    if value < 0.40:
        return "baixa"
    if value < 0.70:
        return "média"
    return "alta"


def rank_fallback_hairstyles(
    base_styles: Sequence[str], hair_current: Any
) -> Dict[str, Any]:
    """Rank grounded candidates using only current-session hair metrics.

    At least two numeric measurements are required. Otherwise the caller
    must fail closed instead of presenting a generic face-shape list as if
    it were individualized.
    """
    current = hair_current if isinstance(hair_current, dict) else {}
    metrics = {
        key: score
        for key in _METRIC_LABELS
        if (score := _bounded_score(current.get(key))) is not None
    }

    summary = ", ".join(
        f"{_METRIC_LABELS[key]} {_bucket(value)}" for key, value in metrics.items()
    )
    if len(metrics) < 2:
        return {
            "styles": [],
            "personalized": False,
            "metric_count": len(metrics),
            "measurement_summary": summary,
        }

    candidates: List[str] = []
    for name in [*base_styles, *_EXTRA_CANDIDATES]:
        if name and name not in candidates:
            candidates.append(name)

    base_index = {name: index for index, name in enumerate(base_styles)}
    scored = []
    for name in candidates:
        if name in base_index:
            base_bonus = max(0.40, 1.00 - (base_index[name] * 0.12))
        else:
            base_bonus = 0.15

        profile = _STYLE_PROFILES.get(name, {})
        similarities = [
            1.0 - abs(value - profile[key])
            for key, value in metrics.items()
            if key in profile
        ]
        fit = sum(similarities) / len(similarities) if similarities else 0.50
        scored.append((base_bonus + (fit * 1.20), name))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return {
        "styles": [name for _, name in scored[:5]],
        "personalized": True,
        "metric_count": len(metrics),
        "measurement_summary": summary,
    }
