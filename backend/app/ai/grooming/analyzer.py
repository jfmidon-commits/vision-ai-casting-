from typing import Dict, List

class GroomingAnalyzer:
    async def analyze(self, photos: List[Dict]) -> Dict:
        return {
            "skin_analysis": {
                "type": "Normal a mista",
                "concerns": ["Brilho na zona T"],
                "recommendations": ["Limpeza diaria", "Hidratacao"]
            },
            "beard_analysis": {
                "style": "Barba curta bem cuidada",
                "maintenance": "Aparar a cada 3 dias",
                "products": ["Oleo de barba", "Balsamo"]
            },
            "eyebrow_analysis": {
                "shape": "Arco natural",
                "recommendation": "Manter formato natural com limpeza",
                "frequency": "A cada 15 dias"
            },
            "overall_grooming_plan": [
                "Rotina diaria de skincare",
                "Barba aparada regularmente",
                "Sobrancelhas bem cuidadas",
                "Unhas limpas e aparadas"
            ],
            "confidence": 0.7
        }
