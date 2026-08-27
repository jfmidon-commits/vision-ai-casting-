import math
from typing import Dict, List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

class ResultConsolidator:
    async def consolidate(self, photos: List[Dict], results: Dict, tenant_id: str) -> Dict:
        consolidated = {
            "status": "completed",
            "photos_analyzed": len(photos),
            "modules": {},
            "confidence_score": 0.0,
            "overall_assessment": {},
        }

        for module_name, module_result in results.items():
            if isinstance(module_result, dict) and "error" in module_result:
                consolidated["modules"][module_name] = {
                    "status": "failed",
                    "error": module_result["error"],
                }
            else:
                consolidated["modules"][module_name] = {
                    "status": "completed",
                    "data": module_result,
                }

        confidence_scores: List[float] = []
        for module_name, module in consolidated["modules"].items():
            if module["status"] == "completed" and isinstance(module.get("data"), dict):
                if "confidence" not in module["data"]:
                    continue
                raw_confidence = module["data"]["confidence"]
                normalized = self._normalize_confidence(raw_confidence)
                if normalized is None:
                    # Confidence presente mas inválido (ex: analyzers de
                    # grooming/photogenic/expressions retornam categorias
                    # como "high"/"medium"/"low" por design em vez de um
                    # score numérico). Registrado para diagnóstico, nunca
                    # interrompe a consolidação.
                    logger.info(
                        "[CONSOLIDATOR] confidence inválido ignorado module=%s value=%r type=%s",
                        module_name,
                        raw_confidence,
                        type(raw_confidence).__name__,
                    )
                    continue
                confidence_scores.append(normalized)

        consolidated["confidence_score"] = round(
            sum(confidence_scores) / len(confidence_scores), 2
        ) if confidence_scores else 0.5

        consolidated["overall_assessment"] = self._generate_overall_assessment(results)
        consolidated["development_plan"] = self._generate_development_plan(results)

        return consolidated

    @staticmethod
    def _normalize_confidence(value) -> Optional[float]:
        """
        Normaliza um valor de confidence heterogêneo para float em [0, 1],
        ou None se o valor não puder ser interpretado com segurança.

        Aceita: int, float, strings numéricas ("0.85"), strings percentuais
        ("85%" -> 0.85), None (-> None). Rejeita: bool (subclasse de int em
        Python, mas não é um confidence válido), strings não numéricas
        ("high"/"low"/etc -- usadas por alguns analyzers como categoria em
        vez de score), NaN e infinito.

        Valores numéricos fora de [0, 1] são limitados (clamped) para essa
        faixa em vez de descartados -- preserva o sinal em vez de jogar
        fora um valor real só por estar levemente fora do intervalo (ex:
        1.0 vindo de arredondamento upstream). Uma string categórica NUNCA
        vira 0: isso distorceria a média para baixo de forma artificial;
        o valor correto nesse caso é simplesmente ignorar a entrada.
        """
        if isinstance(value, bool):
            return None

        if isinstance(value, (int, float)):
            numeric = float(value)
        elif isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            try:
                if text.endswith("%"):
                    numeric = float(text[:-1].strip()) / 100.0
                else:
                    numeric = float(text)
            except ValueError:
                return None
        else:
            return None

        if not math.isfinite(numeric):
            return None

        if numeric < 0.0:
            return 0.0
        if numeric > 1.0:
            return 1.0
        return numeric

    def _generate_overall_assessment(self, results: Dict) -> Dict:
        assessment = {"strengths": [], "areas_for_improvement": [], "key_opportunities": []}

        casting = results.get("casting", {})
        if isinstance(casting, dict) and "strong_suits" in casting:
            assessment["strengths"].extend(casting["strong_suits"])

        facial = results.get("facial_structure", {})
        if isinstance(facial, dict) and facial.get("symmetry_score", 0) > 0.8:
            assessment["strengths"].append("Excelente simetria facial")

        if isinstance(casting, dict) and "development_opportunities" in casting:
            assessment["areas_for_improvement"].extend(casting["development_opportunities"])

        expressions = results.get("expressions", {})
        if isinstance(expressions, dict) and expressions.get("expression_range", 1) < 0.4:
            assessment["areas_for_improvement"].append("Ampliar repertorio expressivo")

        return assessment

    def _generate_development_plan(self, results: Dict) -> Dict:
        plan = {"immediate_actions": [], "short_term": [], "medium_term": [], "long_term": []}

        visagism = results.get("visagism", {})
        casting = results.get("casting", {})

        if isinstance(visagism, dict) and visagism.get("recommended_hairstyles"):
            plan["immediate_actions"].append(f"Agendar sessao com cabeleireiro: {visagism['recommended_hairstyles'][0]}")

        if isinstance(casting, dict) and casting.get("character_types"):
            plan["immediate_actions"].append(f"Preparar self-tape para personagem tipo: {casting['character_types'][0]}")

        plan["short_term"].append("Atualizar portfolio com novas fotos seguindo recomendacoes de visagismo")
        plan["short_term"].append("Participar de workshop de expressao corporal")
        plan["medium_term"].append("Desenvolver reel com cenas dos personagens sugeridos")
        plan["medium_term"].append("Ampliar networking nos segmentos recomendados")
        plan["long_term"].append("Reavaliacao completa em 6 meses para medir evolucao")

        return plan
