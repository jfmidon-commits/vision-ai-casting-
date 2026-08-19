import json
from typing import Dict, List
import openai
from app.config import settings

class VisagismAnalyzer:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def analyze(self, photos: List[Dict], context: Dict = None) -> Dict:
        # Use first photo for visagism analysis
        photo = photos[0] if photos else None
        if not photo:
            return {"error": "No photos provided"}

        return await self.analyze_single(photo)

    async def analyze_single(self, photo: Dict) -> Dict:
        prompt = """Voce e um visagista senior com 20 anos de experiencia em moda editorial, cinema, TV e publicidade.
Analise esta fotografia profissional e forneca recomendacoes especificas de visagismo.

FORMATO JSON:
{
  "face_shape_category": "oval|redondo|quadrado|coracao|diamante|oblongo|triangular",
  "face_shape_description": "Descricao tecnica detalhada",
  "recommended_hairstyles": ["Corte 1", "Corte 2"],
  "recommended_eyebrow_shapes": ["Formato 1", "Formato 2"],
  "recommended_makeup_styles": ["Estilo 1", "Estilo 2"],
  "contouring_tips": ["Dica 1", "Dica 2"],
  "highlighting_tips": ["Dica 1", "Dica 2"],
  "color_recommendations": {
    "hair_colors": ["Cor 1", "Cor 2"],
    "avoid_colors": ["Cor a evitar"],
    "reasoning": "Explicacao colorimetrica"
  },
  "overall_recommendation": "Recomendacao geral de 2-3 paragrafos",
  "confidence": 0.85
}"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Voce e um visagista senior especializado em imagem profissional para entretenimento."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=2000,
                temperature=0.3,
            )
            result = json.loads(response.choices[0].message.content)
            result["confidence"] = result.get("confidence", 0.8)
            return result
        except Exception as e:
            return self._fallback_response(str(e))

    def _fallback_response(self, error_msg: str) -> Dict:
        return {
            "face_shape_category": "oval",
            "face_shape_description": "Analise indisponivel no momento. Forma facial oval e a mais comum e versatil.",
            "recommended_hairstyles": ["Corte em camadas", "Long bob"],
            "recommended_eyebrow_shapes": ["Arco suave", "Reto levemente arqueado"],
            "recommended_makeup_styles": ["Natural glow", "Contorno suave"],
            "contouring_tips": ["Usar tons matte para definir", "Iluminar pontos altos do rosto"],
            "highlighting_tips": ["Aplicar no topo das maças", "Iluminar arco do cupido"],
            "color_recommendations": {
                "hair_colors": ["Castanho natural", "Chocolate quente"],
                "avoid_colors": ["Loiro muito claro sem manutencao"],
                "reasoning": "Tons neutros realçam a maioria dos tons de pele"
            },
            "overall_recommendation": "Consulte um visagista profissional para analise personalizada detalhada.",
            "confidence": 0.5,
            "error": error_msg
        }
