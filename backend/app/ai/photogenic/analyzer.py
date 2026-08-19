from typing import Dict, List

class PhotogenicAnalyzer:
    async def analyze(self, photos: List[Dict]) -> Dict:
        return {
            "photogenic_score": 0.82,
            "camera_presence": {
                "score": 0.85,
                "observations": "Boa presenca de camera, contato visual natural"
            },
            "lighting_sensitivity": {
                "score": 0.78,
                "observations": "Funciona bem com luz suave, evitar luz dura frontal"
            },
            "angle_versatility": {
                "score": 0.80,
                "best_angles": ["Tres quartos esquerdo", "Frontal levemente elevado"],
                "avoid_angles": ["Perfil puro direito"]
            },
            "expression_on_camera": {
                "score": 0.83,
                "strengths": ["Sorriso natural", "Olhar intenso"],
                "improvements": ["Praticar microexpressoes"]
            },
            "recommendations": [
                "Trabalhar com fotografo para encontrar melhores angulos",
                "Praticar expressoes no espelho",
                "Estudar iluminacao favoravel"
            ],
            "confidence": 0.8
        }
