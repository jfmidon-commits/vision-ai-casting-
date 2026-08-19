"""Compatibility layer for the current visagism proportion schema.

The original rule engine was written against legacy proportion names. The
measurement engine now emits height_to_width_ratio, jaw_to_face_ratio and
forehead_to_face_ratio with below/within/above ideal classifications. This
subclass preserves all ranking/style rules and only modernizes proportion
interpretation.
"""

from typing import Any, Dict, List

from app.ai.visagism.rule_engine import VisagismRuleEngine


class CompatibleVisagismRuleEngine(VisagismRuleEngine):
    """Rule engine using both current and legacy proportion contracts."""

    def _analyze_proportions(
        self, proportions: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        adjustments: List[Dict[str, Any]] = []

        for prop_name, prop_data in proportions.items():
            value = prop_data.get("value", 0.5)
            classification = prop_data.get("classification", "unknown")

            if prop_name in {"forehead_height_ratio", "forehead_to_face_ratio"}:
                if classification in {"below_ideal", "low"}:
                    adjustments.append(
                        {
                            "description": (
                                "Regiao frontal proporcionalmente estreita/baixa: "
                                "valorizar abertura e volume frontal"
                            ),
                            "value": value,
                            "confidence": 0.8,
                        }
                    )
                elif classification in {"above_ideal", "high"}:
                    adjustments.append(
                        {
                            "description": (
                                "Regiao frontal proporcionalmente ampla/alta: "
                                "evitar excesso de altura frontal"
                            ),
                            "value": value,
                            "confidence": 0.8,
                        }
                    )

            elif prop_name in {"face_width_ratio", "height_to_width_ratio"}:
                if prop_name == "height_to_width_ratio":
                    if classification == "below_ideal":
                        description = (
                            "Rosto relativamente mais largo: criar altura visual controlada"
                        )
                    elif classification == "above_ideal":
                        description = (
                            "Rosto relativamente alongado: evitar altura excessiva e "
                            "preservar equilibrio lateral"
                        )
                    else:
                        continue
                else:
                    if classification == "wide" or value > 0.75:
                        description = "Rosto largo: alongar visualmente"
                    elif classification == "narrow" or value < 0.65:
                        description = "Rosto estreito: adicionar largura visual"
                    else:
                        continue

                adjustments.append(
                    {
                        "description": description,
                        "value": value,
                        "confidence": 0.8,
                    }
                )

            elif prop_name in {"jaw_width_ratio", "jaw_to_face_ratio"}:
                if classification in {"above_ideal", "strong"}:
                    description = "Mandibula proporcionalmente forte: suavizar e evitar peso lateral"
                elif classification in {"below_ideal", "delicate"}:
                    description = "Mandibula proporcionalmente delicada: preservar estrutura"
                else:
                    continue

                adjustments.append(
                    {
                        "description": description,
                        "value": value,
                        "confidence": 0.8,
                    }
                )

        return adjustments
