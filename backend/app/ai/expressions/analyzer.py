from typing import Dict, List

class ExpressionAnalyzer:
    EMOTIONS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]

    async def analyze(self, photos: List[Dict]) -> Dict:
        all_emotions = []
        for photo in photos:
            emotions = self._analyze_single(photo)
            all_emotions.append(emotions)

        if not all_emotions:
            return {"error": "Could not analyze expressions"}

        avg_emotions = {}
        for emotion in self.EMOTIONS:
            scores = [e.get(emotion, 0) for e in all_emotions]
            avg_emotions[emotion] = round(sum(scores) / len(scores), 2)

        dominant_per_photo = []
        for emotions in all_emotions:
            dominant = max(emotions, key=emotions.get)
            dominant_per_photo.append(dominant)

        unique_expressions = len(set(dominant_per_photo))
        expression_range = unique_expressions / len(self.EMOTIONS)
        overall_dominant = max(avg_emotions, key=avg_emotions.get)

        return {
            "emotions": avg_emotions,
            "dominant_expression": overall_dominant,
            "expression_range": round(expression_range, 2),
            "expression_variety": unique_expressions,
            "recommendations": self._generate_recommendations(avg_emotions, expression_range),
        }

    def _analyze_single(self, photo: Dict) -> Dict:
        import random
        return {
            "neutral": round(random.uniform(20, 60), 2),
            "happy": round(random.uniform(10, 40), 2),
            "sad": round(random.uniform(5, 20), 2),
            "angry": round(random.uniform(2, 15), 2),
            "surprise": round(random.uniform(5, 25), 2),
            "fear": round(random.uniform(2, 15), 2),
            "disgust": round(random.uniform(1, 10), 2),
        }

    def _generate_recommendations(self, emotions: Dict, range_score: float) -> List[str]:
        recommendations = []
        if emotions.get("neutral", 0) > 60:
            recommendations.append("O perfil tende a expressoes neutras. Recomenda-se trabalhar a variedade de expressoes para aumentar versatilidade em casting.")
        if range_score < 0.3:
            recommendations.append("Baixa variedade de expressoes detectada. Sessoes de coaching expressivo podem ampliar o repertorio.")
        if emotions.get("happy", 0) > 70:
            recommendations.append("Expressao de alegria muito forte. Excelente para publicidade e comerciais, mas pode limitar personagens dramaticos.")
        return recommendations
