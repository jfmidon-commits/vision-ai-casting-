from __future__ import annotations

from pathlib import Path
import re
from textwrap import dedent


HELPER = dedent(
    '''
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
            f"{_METRIC_LABELS[key]} {_bucket(value)}"
            for key, value in metrics.items()
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
    '''
).strip() + "\n"


FALLBACK_METHOD = dedent(
    '''
        def _fallback_response(
            self, error_msg: str, measured: Dict = None, limitations: List = None
        ) -> Dict:
            measured = measured or {}
            limitations = list(limitations or [])
            face_shape = measured.get("face_shape")
            density = measured.get("hair_density")
            hairline = measured.get("hairline")
            hair_current = measured.get("hair_current")

            base_styles = self._rule_based_hairstyles(face_shape)
            ranked = rank_fallback_hairstyles(base_styles, hair_current)
            hairstyles = ranked["styles"] if face_shape and base_styles else []
            primary = hairstyles[0] if hairstyles else None
            measurement_summary = ranked["measurement_summary"]
            metric_count = int(ranked["metric_count"])
            personalized = bool(ranked["personalized"] and hairstyles)

            if personalized:
                limitations.append(
                    "llm_unavailable_personalized_rule_based_recommendations"
                )
            else:
                limitations.append("llm_unavailable")
                if face_shape and base_styles:
                    limitations.append("fallback_insufficient_personalization")
                else:
                    limitations.append("fallback_no_grounded_face_shape")

            hair_summary_parts = []
            if density:
                hair_summary_parts.append(f"densidade {density}")
            if hairline:
                hair_summary_parts.append("linha frontal detectada")
            if measurement_summary:
                hair_summary_parts.append(measurement_summary)
            current_hair_summary = (
                "Cabelo atual com " + "; ".join(hair_summary_parts) + "."
                if hair_summary_parts
                else "Avaliação capilar parcial; algumas medidas não foram confirmadas."
            )

            primary_justification = None
            if primary and face_shape:
                details = (
                    f" Foram usadas {metric_count} medições capilares confirmadas: "
                    f"{measurement_summary}."
                    if measurement_summary
                    else ""
                )
                primary_justification = (
                    f"Recomendação de contingência personalizada para o formato facial "
                    f"{face_shape} medido nesta sessão.{details} A lista foi ranqueada "
                    "somente com dados desta análise, sem reutilizar resultado de outro perfil."
                )

            confidence = min(0.62, 0.48 + (metric_count * 0.03)) if primary else 0.30

            return {
                "face_shape_category": face_shape or "desconhecido",
                "face_shape_description": (
                    f"Formato facial {face_shape} medido pelos analisadores locais."
                    if face_shape
                    else "Formato facial não confirmado nesta sessão."
                ),
                "recommended_hairstyles": hairstyles,
                "primary_hairstyle": primary,
                "primary_justification": primary_justification,
                "current_hair": {
                    "summary": current_hair_summary,
                    "density": density or "não medido",
                    "hairline": "detectado" if hairline else "não medido",
                },
                "measured_data_used": {
                    "face_shape": face_shape,
                    "hair_density": density,
                    "hairline": hairline,
                    "hair_current": hair_current,
                    "skin_undertone": measured.get("skin_undertone"),
                    "skin_depth": measured.get("skin_depth"),
                    "season": measured.get("season"),
                    "symmetry": measured.get("symmetry"),
                    "photogenic_score": measured.get("photogenic_score"),
                    "triage_categories": measured.get("triage_categories"),
                },
                "limitations": list(dict.fromkeys(limitations)),
                "recommended_eyebrow_shapes": [],
                "recommended_makeup_styles": [],
                "contouring_tips": [],
                "highlighting_tips": [],
                "color_recommendations": {
                    "hair_colors": [],
                    "avoid_colors": [],
                    "reasoning": (
                        "A colorimetria medida foi preservada, mas a interpretação avançada estava indisponível."
                        if measured.get("skin_undertone")
                        else "Colorimetria não confirmada para recomendação de cor."
                    ),
                },
                "overall_recommendation": (
                    "Análise parcial personalizada pelas medições locais confirmadas; "
                    "a interpretação avançada estava indisponível."
                    if primary
                    else "As medições confirmadas não foram suficientes para diferenciar "
                    "cinco recomendações sem recorrer a uma lista genérica."
                ),
                "confidence": confidence,
                "error": error_msg,
                "data_source": {
                    "measured": bool(face_shape or density or hairline or hair_current),
                    "llm_interpretation": False,
                    "rule_based_interpretation": bool(primary),
                    "personalized_fallback": personalized,
                    "fallback_metric_count": metric_count,
                },
            }
    '''
).strip("\n")


TESTS = dedent(
    '''
    from app.ai.visagism.analyzer import VisagismAnalyzer
    from app.ai.visagism.interpretation import build_visagism_interpretation


    def _analyzer():
        # Private helpers under test do not need an OpenAI client.
        return VisagismAnalyzer.__new__(VisagismAnalyzer)


    def _round_measured(*, coverage, volume, texture, neatness):
        return {
            "face_shape": "round",
            "hair_density": "média",
            "hairline": None,
            "hair_current": {
                "coverage_score": coverage,
                "volume_score": volume,
                "texture_score": texture,
                "neatness_score": neatness,
            },
            "skin_undertone": "warm",
            "skin_depth": "medium",
            "season": "Autumn",
            "symmetry": 0.936,
            "photogenic_score": 0.82,
            "triage_categories": ["frontal"],
        }


    def test_extract_measured_data_accepts_grooming_coverage_alias():
        analyzer = _analyzer()
        measured = analyzer._extract_measured_data(
            {
                "facial_structure": {
                    "face_shape": "round",
                    "sources": {"combined": "aggregated"},
                },
                "grooming": {
                    "dimensions": {
                        "hair": {
                            "coverage": 0.531,
                            "volume": 0.516,
                            "texture": 1.0,
                            "neatness": 0.625,
                            "overall_score": 0.638,
                        }
                    }
                },
            },
            [{"selected": True, "category": "frontal", "filename": "photo-1"}],
        )

        assert measured["hair_density"] == "média"
        assert measured["hair_current"]["coverage_score"] == 0.531
        assert measured["hair_current"]["volume_score"] == 0.516
        assert "hair_density_not_measured" not in measured["_limitations"]


    def test_fallback_personalizes_same_face_shape_from_hair_metrics():
        analyzer = _analyzer()
        textured = analyzer._fallback_response(
            "Error code: 429 insufficient_quota",
            _round_measured(coverage=0.85, volume=0.85, texture=0.90, neatness=0.45),
            ["hairline_not_measured"],
        )
        controlled = analyzer._fallback_response(
            "Error code: 429 insufficient_quota",
            _round_measured(coverage=0.45, volume=0.25, texture=0.25, neatness=0.90),
            ["hairline_not_measured"],
        )

        assert len(textured["recommended_hairstyles"]) == 5
        assert len(controlled["recommended_hairstyles"]) == 5
        assert textured["recommended_hairstyles"] != controlled["recommended_hairstyles"]
        assert textured["primary_hairstyle"] != controlled["primary_hairstyle"]
        assert textured["data_source"]["personalized_fallback"] is True
        assert controlled["data_source"]["personalized_fallback"] is True
        assert textured["data_source"]["fallback_metric_count"] == 4
        assert (
            "llm_unavailable_personalized_rule_based_recommendations"
            in textured["limitations"]
        )


    def test_fallback_refuses_generic_face_shape_only_recommendations():
        analyzer = _analyzer()
        result = analyzer._fallback_response(
            "Error code: 429 insufficient_quota",
            {
                "face_shape": "round",
                "hair_density": "média",
                "hairline": None,
                "skin_undertone": "warm",
                "symmetry": 0.936,
            },
            ["hairline_not_measured"],
        )

        assert result["recommended_hairstyles"] == []
        assert result["primary_hairstyle"] is None
        assert result["data_source"]["personalized_fallback"] is False
        assert "fallback_insufficient_personalization" in result["limitations"]

        interpretation = build_visagism_interpretation(result)
        assert interpretation["status"] == "service_limited"


    def test_fallback_remains_fail_closed_without_measured_face_shape():
        analyzer = _analyzer()
        result = analyzer._fallback_response(
            "quota",
            {"face_shape": None, "hair_density": None, "hairline": None},
            ["face_shape_not_measured"],
        )

        assert result["recommended_hairstyles"] == []
        assert result["primary_hairstyle"] is None
        assert result["data_source"]["rule_based_interpretation"] is False
        assert "fallback_no_grounded_face_shape" in result["limitations"]


    def test_interpretation_marks_personalized_service_fallback_as_partial():
        analyzer = _analyzer()
        raw = analyzer._fallback_response(
            "Error code: 429 insufficient_quota",
            _round_measured(coverage=0.72, volume=0.64, texture=0.81, neatness=0.58),
            ["hairline_not_measured"],
        )

        interpretation = build_visagism_interpretation(raw)

        assert interpretation["status"] == "partial_grounded"
        assert interpretation["primary_recommendation"]["name"] == raw["primary_hairstyle"]
        assert "densidade do cabelo: média" in interpretation["executive_summary"]
        attention = interpretation["current_hair_assessment"]["attention_points"]
        assert any(
            "interpretação avançada" in item.lower() and "medições" in item.lower()
            for item in attention
        )
        assert (
            "A linha frontal do cabelo não pôde ser confirmada com confiança suficiente."
            in attention
        )
        assert "Uma parte da análise não pôde ser confirmada com segurança." not in attention
    '''
).strip() + "\n"


def require_replace(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"anchor not found: {label}")
    return text.replace(old, new, 1)


def main() -> None:
    Path("backend/app/ai/visagism/fallback_ranker.py").write_text(HELPER)

    analyzer_path = Path("backend/app/ai/visagism/analyzer.py")
    text = analyzer_path.read_text()
    text = require_replace(
        text,
        "import openai\nfrom app.config import settings\n",
        "import openai\n"
        "from app.ai.visagism.fallback_ranker import rank_fallback_hairstyles\n"
        "from app.config import settings\n",
        "analyzer import",
    )
    pattern = re.compile(r"\n    def _fallback_response\([\s\S]*\Z")
    if not pattern.search(text):
        raise RuntimeError("anchor not found: fallback method")
    text = pattern.sub(lambda _: "\n" + FALLBACK_METHOD + "\n", text, count=1)
    analyzer_path.write_text(text)

    interpretation_path = Path("backend/app/ai/visagism/interpretation.py")
    text = interpretation_path.read_text()
    old_limit = (
        '    "llm_unavailable_rule_based_recommendations": '
        '"A interpretação avançada não estava disponível; as recomendações foram montadas de forma conservadora a partir das medições confirmadas.",\n'
    )
    new_limit = old_limit + (
        '    "llm_unavailable_personalized_rule_based_recommendations": '
        '"A interpretação avançada não estava disponível; as recomendações foram personalizadas apenas com as medições faciais e capilares confirmadas desta sessão.",\n'
        '    "fallback_insufficient_personalization": '
        '"As medições confirmadas não foram suficientes para diferenciar recomendações com segurança; por isso nenhuma lista genérica foi exibida.",\n'
    )
    text = require_replace(text, old_limit, new_limit, "interpretation limitation")
    old_status = '    status = "ready" if primary else "insufficient_grounded_data"\n'
    new_status = dedent(
        '''
            if primary and rule_based:
                status = "partial_grounded"
            elif primary:
                status = "ready"
            elif data_source.get("llm_interpretation") is False and data_source.get("measured") is True:
                status = "service_limited"
            else:
                status = "insufficient_grounded_data"
        '''
    )
    text = require_replace(text, old_status, new_status, "interpretation status")
    interpretation_path.write_text(text)

    types_path = Path("frontend/types/index.ts")
    text = types_path.read_text()
    text = require_replace(
        text,
        '  status: "ready" | "insufficient_grounded_data";',
        '  status: "ready" | "partial_grounded" | "service_limited" | "insufficient_grounded_data";',
        "frontend interpretation status type",
    )
    types_path.write_text(text)

    component_path = Path("frontend/components/visagism/visagism-result.tsx")
    text = component_path.read_text()
    service_anchor = '  if (interpretation?.status === "insufficient_grounded_data") {\n'
    service_block = dedent(
        '''
          if (interpretation?.status === "service_limited") {
            return (
              <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col bg-background px-4 pb-8 pt-6">
                <p className="text-sm font-medium text-muted-foreground">Resultado</p>
                <h1 className="mt-1 text-2xl font-semibold">Interpretação avançada indisponível</h1>
                <p className="mt-4 text-sm leading-6 text-muted-foreground">
                  As medições desta sessão foram preservadas, mas não havia dados suficientes para diferenciar cinco recomendações sem recorrer a uma lista genérica.
                </p>
                {interpretation.current_hair_assessment.attention_points.length ? (
                  <div className="mt-6 rounded-2xl border bg-card p-4">
                    <h2 className="font-semibold">O que foi possível confirmar</h2>
                    <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                      {interpretation.current_hair_assessment.attention_points.map((item) => (
                        <li key={item}>• {item}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                <Button className="mt-auto h-12 w-full" onClick={onReset}>
                  Fazer nova análise
                </Button>
              </main>
            );
          }

        '''
    )
    text = require_replace(
        text,
        service_anchor,
        service_block + service_anchor,
        "frontend service-limited block",
    )
    text = require_replace(
        text,
        '      <h1 className="mt-1 text-2xl font-semibold">Sua análise foi concluída</h1>\n',
        dedent(
            '''
                  <h1 className="mt-1 text-2xl font-semibold">
                    {interpretation?.status === "partial_grounded"
                      ? "Análise parcial com dados confirmados"
                      : "Sua análise foi concluída"}
                  </h1>
            '''
        ),
        "frontend completed title",
    )
    component_path.write_text(text)

    Path("backend/app/tests/test_visagism_resilient_fallback.py").write_text(TESTS)


if __name__ == "__main__":
    main()
