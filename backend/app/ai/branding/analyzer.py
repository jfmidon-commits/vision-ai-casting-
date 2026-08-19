import json
from typing import Dict, List
import openai
from app.config import settings

class BrandingAnalyzer:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def analyze(self, photos: List[Dict], context: Dict = None) -> Dict:
        photo = photos[0] if photos else None
        if not photo:
            return {"error": "No photos provided"}

        return await self.analyze_single(photo)

    async def analyze_single(self, photo: Dict) -> Dict:
        prompt = """Voce e um consultor de branding pessoal especializado em artistas e modelos.
Analise este perfil e forneca uma estrategia de marca pessoal.

FORMATO JSON:
{
  "archetypes": [{"name": "Nome", "description": "Descricao", "strengths": ["Forca 1"], "positioning": "Posicionamento"}],
  "brand_positioning": {
    "tagline_suggestions": ["Slogan 1", "Slogan 2"],
    "unique_selling_point": "Diferencial",
    "target_audience": "Publico-alvo",
    "brand_voice": "Tom de voz"
  },
  "social_media_strategy": {
    "platforms": ["Instagram", "TikTok"],
    "content_pillars": ["Pilar 1", "Pilar 2"],
    "posting_frequency": "3x por semana",
    "engagement_tips": ["Dica 1", "Dica 2"]
  },
  "portfolio_recommendations": {
    "must_have_shots": ["Foto 1", "Foto 2"],
    "style_consistency": "Como manter consistencia",
    "update_frequency": "A cada 6 meses"
  },
  "networking_strategy": ["Estrategia 1", "Estrategia 2"],
  "confidence": 0.8
}"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Voce e um consultor de branding pessoal especializado em entretenimento."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=2000,
                temperature=0.4,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {
                "archetypes": [{"name": "O Profissional", "description": "Perfil versatil e confiavel", "strengths": ["Versatilidade"], "positioning": "Profissional completo"}],
                "brand_positioning": {"tagline_suggestions": ["Sua marca, sua historia"], "unique_selling_point": "Versatilidade", "target_audience": "Agencias e produtoras", "brand_voice": "Profissional e autentico"},
                "social_media_strategy": {"platforms": ["Instagram"], "content_pillars": ["Portfolio"], "posting_frequency": "3x/semana", "engagement_tips": ["Interaja com seguidores"]},
                "portfolio_recommendations": {"must_have_shots": ["Headshot", "Corpo inteiro"], "style_consistency": "Manter paleta de cores", "update_frequency": "6 meses"},
                "networking_strategy": ["Eventos do setor", "LinkedIn"],
                "confidence": 0.5,
                "error": str(e)
            }
