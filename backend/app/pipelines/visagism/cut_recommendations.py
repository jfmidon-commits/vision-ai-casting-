"""Deterministic haircut recommendations for the reproducible visagism pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


@dataclass(frozen=True)
class CutTemplate:
    key: str
    name: str
    compatible_faces: Tuple[str, ...]
    preferred_densities: Tuple[str, ...]
    top_cm: Tuple[float, float]
    sides_mm: Tuple[int, int]
    fade: str
    connection: str
    direction: str
    finish: str
    maintenance: str
    avoid: str


class CutRecommendationEngine:
    """Rank short-hair cuts from traceable facial and hair evidence."""

    CATALOG: Sequence[CutTemplate] = (
        CutTemplate(
            key="classic_scissor_taper",
            name="Classic Scissor Taper",
            compatible_faces=("oval", "oblong", "square", "mixed", "round"),
            preferred_densities=(
                "high_visual_density",
                "medium_visual_density",
                "low_visual_density",
            ),
            top_cm=(5.0, 7.0),
            sides_mm=(12, 25),
            fade="low taper, soft and conservative",
            connection="scissor connection with no hard shelf",
            direction="natural side or slightly back",
            finish="matte, controlled texture",
            maintenance="3-5 weeks",
            avoid="very high fade or excessive removal at the temples",
        ),
        CutTemplate(
            key="ivy_league",
            name="Ivy League",
            compatible_faces=("oval", "square", "round", "mixed", "heart"),
            preferred_densities=("high_visual_density", "medium_visual_density"),
            top_cm=(4.0, 6.0),
            sides_mm=(6, 16),
            fade="low to mid taper",
            connection="graduated connection into the crown",
            direction="side-swept with restrained lift",
            finish="natural matte",
            maintenance="3-4 weeks",
            avoid="exposing recession with a high temple fade",
        ),
        CutTemplate(
            key="textured_crop",
            name="Textured Crop",
            compatible_faces=("oval", "oblong", "heart", "mixed", "square"),
            preferred_densities=("high_visual_density", "medium_visual_density"),
            top_cm=(3.5, 5.5),
            sides_mm=(4, 12),
            fade="low taper or low fade",
            connection="compact transition, preserving weight above temples",
            direction="forward with irregular texture",
            finish="dry matte texture",
            maintenance="3-4 weeks",
            avoid="over-thinning the frontal zone",
        ),
        CutTemplate(
            key="side_part_taper",
            name="Side Part Taper",
            compatible_faces=("oval", "square", "round", "mixed"),
            preferred_densities=("high_visual_density", "medium_visual_density"),
            top_cm=(6.0, 8.0),
            sides_mm=(8, 20),
            fade="low taper",
            connection="soft scissor-over-comb connection",
            direction="defined side direction without a shaved part",
            finish="natural or low-shine",
            maintenance="4-5 weeks",
            avoid="hard part lines or excessive height",
        ),
        CutTemplate(
            key="crew_cut_taper",
            name="Crew Cut Taper",
            compatible_faces=("oval", "square", "round", "mixed"),
            preferred_densities=(
                "high_visual_density",
                "medium_visual_density",
                "low_visual_density",
            ),
            top_cm=(2.5, 4.5),
            sides_mm=(3, 10),
            fade="low to mid taper",
            connection="short graduated connection",
            direction="slightly forward or natural",
            finish="clean matte",
            maintenance="2-4 weeks",
            avoid="taking the temples to skin when recession is uncertain",
        ),
        CutTemplate(
            key="soft_quiff_taper",
            name="Soft Quiff Taper",
            compatible_faces=("oval", "round", "square", "mixed"),
            preferred_densities=("high_visual_density", "medium_visual_density"),
            top_cm=(6.0, 9.0),
            sides_mm=(6, 16),
            fade="low taper",
            connection="preserve front-to-crown continuity",
            direction="up and slightly back, without extreme height",
            finish="matte flexible hold",
            maintenance="3-5 weeks",
            avoid="high volume on very elongated faces",
        ),
        CutTemplate(
            key="short_brush_back",
            name="Short Brush Back",
            compatible_faces=("oval", "square", "heart", "mixed"),
            preferred_densities=("high_visual_density", "medium_visual_density"),
            top_cm=(6.0, 8.0),
            sides_mm=(10, 22),
            fade="tapered, not disconnected",
            connection="full scissor connection",
            direction="back with natural separation",
            finish="low-shine or matte",
            maintenance="4-5 weeks",
            avoid="wet slick-back effect or strong scalp exposure",
        ),
    )

    def recommend(
        self,
        face_shape: str,
        hair_analysis: Mapping[str, Any],
        limit: int = 5,
    ) -> Dict[str, Any]:
        normalized_shape = (face_shape or "mixed").strip().lower()
        density = self._density(hair_analysis)
        limitations = list(hair_analysis.get("limitations", []))

        ranked: List[Dict[str, Any]] = []
        for template in self.CATALOG:
            score, reasons, risks = self._score(
                template,
                normalized_shape,
                density,
                limitations,
            )
            item = asdict(template)
            item.update(
                {
                    "compatibility_score": round(score, 3),
                    "reasons": reasons,
                    "risks": risks,
                    "evidence": {
                        "face_shape": normalized_shape,
                        "visual_density": density,
                    },
                }
            )
            ranked.append(item)

        ranked.sort(key=lambda item: (-item["compatibility_score"], item["name"]))
        options = ranked[: max(1, min(limit, len(ranked)))]
        return {
            "options": options,
            "primary": options[0] if options else None,
            "ranking_method": "deterministic_face_shape_and_visual_density_rules",
            "limitations": limitations,
        }

    @staticmethod
    def _density(hair_analysis: Mapping[str, Any]) -> str:
        estimated = hair_analysis.get("estimated", {})
        density = estimated.get("visual_density", {}) if isinstance(estimated, Mapping) else {}
        value = density.get("value") if isinstance(density, Mapping) else None
        if isinstance(value, str):
            return value
        return "unknown_visual_density"

    @staticmethod
    def _score(
        template: CutTemplate,
        face_shape: str,
        density: str,
        limitations: Iterable[str],
    ) -> Tuple[float, List[str], List[str]]:
        score = 0.45
        reasons: List[str] = []
        risks: List[str] = []

        if face_shape in template.compatible_faces:
            score += 0.32
            reasons.append(f"compatible with {face_shape} face geometry")
        else:
            risks.append(f"face-shape fit for {face_shape} is not preferred")

        if density in template.preferred_densities:
            score += 0.18
            reasons.append(f"supports {density}")
        elif density == "unknown_visual_density":
            risks.append("visual density is unavailable")
        else:
            score -= 0.08
            risks.append(f"may require more density than {density}")

        limitation_set = set(limitations)
        if "hairline_view_missing" in limitation_set:
            score -= 0.03
            risks.append("hairline view is missing; keep temple changes conservative")

        return max(0.0, min(1.0, score)), reasons, risks
