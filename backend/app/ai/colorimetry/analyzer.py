from typing import Dict, List

class ColorimetryAnalyzer:
    async def analyze(self, photos: List[Dict]) -> Dict:
        return {
            "skin_undertone": "warm",
            "skin_depth": "medium",
            "season": "Autumn",
            "season_subtype": "Warm Autumn",
            "color_palette": {
                "best_colors": ["#8B4513", "#D2691E", "#CD853F", "#A0522D", "#DEB887"],
                "good_colors": ["#556B2F", "#6B8E23", "#808000"],
                "avoid_colors": ["#FF69B4", "#00CED1"],
                "neutrals": ["#F5F5DC", "#D2B48C", "#8B7355"]
            },
            "wardrobe_recommendations": {
                "formal": ["Tons terrosos escuros", "Marrom chocolate"],
                "casual": ["Oliva", "Mostarda", "Caramelo"],
                "camera": ["Tons quentes neutros", "Evitar branco puro"]
            },
            "makeup_colors": {
                "foundation": "Bege medio quente",
                "blush": "Pessego ou bronze",
                "lipstick": ["Nude quente", "Terra"],
                "eyeshadow": ["Bronze", "Dourado suave"]
            },
            "confidence": 0.75
        }
