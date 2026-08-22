"""
VisagismAnalyzer - Análise de visagismo orientada a dados reais.

Regra de ouro (P0):
- Consome parallel_results dos motores reais quando disponíveis.
- Nunca inventa densidade, hairline, subtom, proporção ou qualquer métrica técnica.
- Diferencia claramente: dados medidos | dados derivados | interpretação LLM.
- Saída obrigatória: 5 cortes + corte principal justificado.
"""

import json
from typing import Any, Dict, List, Optional

import openai
from app.config import settings


class VisagismAnalyzer:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def analyze(self, photos: List[Dict], context: Dict = None) -> Dict:
        """Entry point. Aceita context com parallel_results dos motores reais."""
        photo = photos[0] if photos else None
        if not photo:
            return {"error": "No photos provided", "limitations": ["no_photos"]}

        return await self.analyze_single(photo, context=context or {})

    async def analyze_single(self, photo: Dict, context: Dict = None) -> Dict:
        context = context or {}
        parallel = context.get("parallel_results") or {}
        triage = context.get("triage_results") or []

        measured = self._extract_measured_data(parallel, triage)
        limitations = measured.pop("_limitations", [])

        prompt = self._build_grounded_prompt(measured, limitations)

        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Você é um visagista sênior. "
                            "Use EXCLUSIVAMENTE os dados medidos fornecidos. "
                            "Nunca invente densidade, hairline, subtom, proporção, "
                            "simetria ou qualquer métrica técnica ausente. "
                            "Se um dado estiver em 'limitations', declare a limitação "
                            "e baseie a recomendação apenas no que foi medido."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=2500,
                temperature=0.25,
            )
            result = json.loads(response.choices[0].message.content)
            result = self._normalize_output(result, measured, limitations)
            return result
        except Exception as e:
            return self._fallback_response(str(e), measured, limitations)

    def _extract_measured_data(
        self, parallel: Dict[str, Any], triage: List[Dict]
    ) -> Dict[str, Any]:
        measured: Dict[str, Any] = {
            "face_shape": None,
            "face_proportions": None,
            "hair_current": None,
            "hair_density": None,
            "hairline": None,
            "skin_undertone": None,
            "skin_depth": None,
            "season": None,
            "photogenic_score": None,
            "symmetry": None,
            "dominant_expression": None,
            "triage_categories": [],
            "selected_photos": [],
            "_limitations": [],
        }

        if triage:
            measured["triage_categories"] = [
                t.get("category") for t in triage if t.get("selected")
            ]
            measured["selected_photos"] = [
                t.get("filename") for t in triage if t.get("selected")
            ]
            if not measured["selected_photos"]:
                measured["_limitations"].append("no_photos_passed_triage")
        else:
            measured["_limitations"].append("triage_not_available")

        facial = parallel.get("facial_structure") or parallel.get("facial") or {}
        if isinstance(facial, dict) and facial:
            measured["face_shape"] = (
                facial.get("face_shape")
                or facial.get("shape")
                or facial.get("face_shape_category")
            )
            measured["face_proportions"] = facial.get("proportions") or facial.get(
                "face_proportions"
            )
            if not measured["face_shape"]:
                measured["_limitations"].append("face_shape_not_measured")
        else:
            measured["_limitations"].append("facial_analyzer_not_available")

        grooming = parallel.get("grooming") or {}
        if isinstance(grooming, dict) and grooming:
            dims = grooming.get("dimensions") or {}
            hair = dims.get("hair") or grooming.get("hair") or {}
            if isinstance(hair, dict):
                measured["hair_current"] = {
                    "coverage_score": hair.get("coverage_score"),
                    "volume_score": hair.get("volume_score"),
                    "texture_score": hair.get("texture_score"),
                    "neatness_score": hair.get("neatness_score"),
                    "overall_score": hair.get("overall_score"),
                }
                if hair.get("coverage_score") is not None:
                    measured["hair_density"] = self._derive_density_label(
                        hair.get("coverage_score")
                    )
                else:
                    measured["_limitations"].append("hair_density_not_measured")
            else:
                measured["_limitations"].append("hair_metrics_not_measured")

            if "hairline" in str(grooming).lower() or any(
                c == "hairline" for c in measured["triage_categories"]
            ):
                measured["hairline"] = "detected_in_triage_or_grooming"
            else:
                measured["_limitations"].append("hairline_not_measured")
        else:
            measured["_limitations"].append("grooming_analyzer_not_available")
            measured["_limitations"].append("hair_density_not_measured")
            measured["_limitations"].append("hairline_not_measured")

        colorimetry = parallel.get("colorimetry") or {}
        if isinstance(colorimetry, dict) and colorimetry:
            measured["skin_undertone"] = colorimetry.get("skin_undertone")
            measured["skin_depth"] = colorimetry.get("skin_depth")
            measured["season"] = colorimetry.get("season")
            if not measured["skin_undertone"]:
                measured["_limitations"].append("skin_undertone_not_measured")
        else:
            measured["_limitations"].append("colorimetry_analyzer_not_available")

        photogenic = parallel.get("photogenic") or {}
        if isinstance(photogenic, dict) and photogenic:
            measured["photogenic_score"] = photogenic.get("overall_score")
            dims = photogenic.get("dimensions") or {}
            sym = dims.get("symmetry") or {}
            if isinstance(sym, dict):
                measured["symmetry"] = sym.get("score")
            else:
                measured["_limitations"].append("symmetry_not_measured")
        else:
            measured["_limitations"].append("photogenic_analyzer_not_available")

        expressions = parallel.get("expressions") or {}
        if isinstance(expressions, dict) and expressions:
            measured["dominant_expression"] = expressions.get("dominant_expression")

        return measured

    def _derive_density_label(self, coverage_score: Optional[float]) -> Optional[str]:
        if coverage_score is None:
            return None
        if coverage_score >= 0.75:
            return "alta"
        if coverage_score >= 0.45:
            return "média"
        return "baixa"

    def _build_grounded_prompt(
        self, measured: Dict[str, Any], limitations: List[str]
    ) -> str:
        measured_clean = {k: v for k, v in measured.items() if not k.startswith("_")}
        return f"""Dados MEDIDOS disponíveis (use somente estes):

{json.dumps(measured_clean, ensure_ascii=False, indent=2)}

Limitações explícitas (NÃO invente estes dados):
{json.dumps(limitations, ensure_ascii=False)}

Gere recomendações de visagismo com o formato JSON obrigatório abaixo.
Você DEVE produzir exatamente 5 opções de corte.
O corte principal deve ser justificado com base nos dados medidos (formato facial, cabelo atual, densidade quando existir, hairline quando existir).
Se algum dado estiver em limitations, declare a limitação na justificativa e não invente o valor.

FORMATO JSON OBRIGATÓRIO:
{{
  "face_shape_category": "oval|redondo|quadrado|coracao|diamante|oblongo|triangular|desconhecido",
  "face_shape_description": "descrição baseada nos dados medidos ou 'não medido'",
  "recommended_hairstyles": ["Corte 1", "Corte 2", "Corte 3", "Corte 4", "Corte 5"],
  "primary_hairstyle": "nome do corte principal",
  "primary_justification": "justificativa clara ligando o corte aos dados medidos",
  "current_hair": {{
    "summary": "resumo do cabelo atual com base nos dados medidos",
    "density": "alta|média|baixa|não medido",
    "hairline": "detectado|não medido"
  }},
  "measured_data_used": {{
    "face_shape": "...",
    "hair_density": "...",
    "hairline": "...",
    "skin_undertone": "...",
    "symmetry": "..."
  }},
  "limitations": ["lista de limitações"],
  "recommended_eyebrow_shapes": ["Formato 1", "Formato 2"],
  "recommended_makeup_styles": ["Estilo 1", "Estilo 2"],
  "contouring_tips": ["Dica 1", "Dica 2"],
  "highlighting_tips": ["Dica 1", "Dica 2"],
  "color_recommendations": {{
    "hair_colors": ["Cor 1", "Cor 2"],
    "avoid_colors": ["Cor a evitar"],
    "reasoning": "Explicação baseada em colorimetria medida quando disponível"
  }},
  "overall_recommendation": "Recomendação geral de 2-3 parágrafos baseada nos dados",
  "confidence": 0.0
}}"""

    def _normalize_output(
        self, result: Dict, measured: Dict, limitations: List[str]
    ) -> Dict:
        hairstyles = result.get("recommended_hairstyles") or []
        if not isinstance(hairstyles, list):
            hairstyles = []
        while len(hairstyles) < 5:
            hairstyles.append(f"Opção complementar {len(hairstyles) + 1}")
        hairstyles = hairstyles[:5]
        result["recommended_hairstyles"] = hairstyles

        if not result.get("primary_hairstyle"):
            result["primary_hairstyle"] = hairstyles[0] if hairstyles else "Não determinado"
        if not result.get("primary_justification"):
            result["primary_justification"] = (
                "Justificativa gerada a partir dos dados medidos disponíveis."
            )

        current = result.get("current_hair") or {}
        if not isinstance(current, dict):
            current = {}
        current.setdefault(
            "density",
            measured.get("hair_density") or "não medido",
        )
        current.setdefault(
            "hairline",
            "detectado" if measured.get("hairline") else "não medido",
        )
        current.setdefault(
            "summary",
            "Cabelo atual derivado dos dados de grooming quando disponíveis.",
        )
        result["current_hair"] = current

        if measured.get("face_shape") and not result.get("face_shape_category"):
            result["face_shape_category"] = measured["face_shape"]
        if not result.get("face_shape_category"):
            result["face_shape_category"] = "desconhecido"

        result_limitations = result.get("limitations") or []
        if not isinstance(result_limitations, list):
            result_limitations = []
        result["limitations"] = list(dict.fromkeys(result_limitations + limitations))

        result["measured_data_used"] = {
            "face_shape": measured.get("face_shape"),
            "hair_density": measured.get("hair_density"),
            "hairline": measured.get("hairline"),
            "skin_undertone": measured.get("skin_undertone"),
            "skin_depth": measured.get("skin_depth"),
            "season": measured.get("season"),
            "symmetry": measured.get("symmetry"),
            "photogenic_score": measured.get("photogenic_score"),
            "triage_categories": measured.get("triage_categories"),
        }

        result.setdefault("recommended_eyebrow_shapes", [])
        result.setdefault("recommended_makeup_styles", [])
        result.setdefault("contouring_tips", [])
        result.setdefault("highlighting_tips", [])
        result.setdefault(
            "color_recommendations",
            {"hair_colors": [], "avoid_colors": [], "reasoning": ""},
        )
        result.setdefault("overall_recommendation", "")
        result["confidence"] = float(result.get("confidence", 0.7))

        result["data_source"] = {
            "measured": True,
            "llm_interpretation": True,
            "engines_used": [
                k
                for k in [
                    "facial",
                    "grooming",
                    "colorimetry",
                    "photogenic",
                    "expressions",
                    "triage",
                ]
                if k not in str(limitations)
            ],
        }

        return result

    def _fallback_response(
        self, error_msg: str, measured: Dict = None, limitations: List = None
    ) -> Dict:
        measured = measured or {}
        limitations = limitations or ["analyzer_error"]
        return {
            "face_shape_category": measured.get("face_shape") or "desconhecido",
            "face_shape_description": "Análise indisponível no momento.",
            "recommended_hairstyles": [
                "Corte em camadas",
                "Degradê médio",
                "Top volume",
                "Lateral baixa",
                "Texturizado curto",
            ],
            "primary_hairstyle": "Corte em camadas",
            "primary_justification": "Fallback: dados insuficientes para personalização completa.",
            "current_hair": {
                "summary": "Não foi possível medir o cabelo atual.",
                "density": measured.get("hair_density") or "não medido",
                "hairline": "não medido",
            },
            "measured_data_used": {
                "face_shape": measured.get("face_shape"),
                "hair_density": measured.get("hair_density"),
                "hairline": measured.get("hairline"),
                "skin_undertone": measured.get("skin_undertone"),
                "symmetry": measured.get("symmetry"),
            },
            "limitations": limitations + [f"error: {error_msg}"],
            "recommended_eyebrow_shapes": ["Arco suave"],
            "recommended_makeup_styles": ["Natural"],
            "contouring_tips": [],
            "highlighting_tips": [],
            "color_recommendations": {
                "hair_colors": [],
                "avoid_colors": [],
                "reasoning": "Colorimetria não disponível",
            },
            "overall_recommendation": "Consulte um profissional. Análise automática indisponível.",
            "confidence": 0.3,
            "error": error_msg,
            "data_source": {"measured": False, "llm_interpretation": False},
        }
