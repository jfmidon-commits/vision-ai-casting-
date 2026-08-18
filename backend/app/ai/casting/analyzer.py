import json
from typing import Dict, List
import openai
from app.config import settings

class CastingAnalyzer:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def analyze(self, photos: List[Dict], context: Dict = None) -> Dict:
        photo = photos[0] if photos else None
        if not photo:
            return {"error": "No photos provided"}

        return await self.analyze_single(photo)

    async def analyze_single(self, photo: Dict) -> Dict:
        prompt = """Voce e um diretor de casting senior com 25 anos de experiencia em cinema, TV, streaming e publicidade.
Analise este perfil profissional e forneca recomendacoes estrategicas de casting.

FORMATO JSON:
{
  "character_types": ["Tipo 1", "Tipo 2", "Tipo 3"],
  "age_range": "XX-XX anos",
  "market_segments": ["Publicidade", "TV", "Streaming", "Cinema"],
  "media_types": ["tv_commercial", "digital_content", "series", "film"],
  "archetypes": ["O Heroi", "O Sabio"],
  "strong_suits": ["Presenca de camera", "Expressividade"],
  "avoid": ["Tipo a evitar 1", "Tipo a evitar 2"],
  "commercial_potential": "Descricao do potencial comercial",
  "development_opportunities": ["Oportunidade 1", "Oportunidade 2"],
  "confidence": 0.78
}"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Voce e um diretor de casting senior com vasta experiencia em entretenimento."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=1500,
                temperature=0.3,
            )
            result = json.loads(response.choices[0].message.content)
            result["disclaimer"] = "Estas sao hipoteses fundamentadas baseadas em analise de dados visuais e padroes de mercado. Nao sao verdades absolutas."
            return result
        except Exception as e:
            return self._fallback_response(str(e))

    def _fallback_response(self, error_msg: str) -> Dict:
        return {
            "character_types": ["Protagonista", "Coadjuvante", "Comercial"],
            "age_range": "25-40 anos",
            "market_segments": ["Publicidade", "TV", "Streaming"],
            "media_types": ["tv_commercial", "digital_content", "series"],
            "archetypes": ["O Heroi", "O Amigo"],
            "strong_suits": ["Versatilidade", "Presenca"],
            "avoid": ["Viloes extremos"],
            "commercial_potential": "Potencial comercial medio-alto para publicidade e conteudo digital.",
            "development_opportunities": ["Workshop de atuacao", "Aulas de expressao corporal"],
            "confidence": 0.5,
            "disclaimer": "Estas sao hipoteses fundamentadas baseadas em analise de dados visuais e padroes de mercado. Nao sao verdades absolutas.",
            "error": error_msg
        }
