from typing import Dict, List

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

        confidence_scores = []
        for module in consolidated["modules"].values():
            if module["status"] == "completed" and isinstance(module.get("data"), dict):
                if "confidence" in module["data"]:
                    confidence_scores.append(module["data"]["confidence"])

        consolidated["confidence_score"] = round(
            sum(confidence_scores) / len(confidence_scores), 2
        ) if confidence_scores else 0.5

        consolidated["overall_assessment"] = self._generate_overall_assessment(results)
        consolidated["development_plan"] = self._generate_development_plan(results)

        return consolidated

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
