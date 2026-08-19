"""
ColorimetryAnalyzer - Analise real de colorimetria pessoal usando OpenCV.
Detecta subtom de pele, profundidade e estacao do ano usando analise
de clusters de cor na regiao facial.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple
from sklearn.cluster import KMeans


class ColorimetryAnalyzer:
    """
    Analisa colorimetria pessoal extraindo cores dominantes da pele
    e classificando em estacoes (Primavera, Verao, Outono, Inverno).
    """

    def __init__(self):
        self._face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'
        )

    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analisa colorimetria pessoal em uma imagem facial.

        Args:
            image_bytes: Bytes da imagem (JPEG/PNG)

        Returns:
            Dict com analise completa de colorimetria
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return self._error_result("Nao foi possivel carregar a imagem")

        # Converter para RGB para analise de cor
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detectar face
        faces = self._face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100)
        )

        if len(faces) == 0:
            return self._error_result("Nenhum rosto detectado")

        # Usar a maior face
        largest_face = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = largest_face

        # Extrair regioes especificas da pele (evitar olhos, sobrancelhas, boca)
        skin_regions = self._extract_skin_regions(img_rgb, x, y, w, h)

        if not skin_regions:
            return self._error_result("Nao foi possivel extrair regioes de pele")

        # Analisar cores dominantes
        dominant_colors = self._extract_dominant_colors(skin_regions)

        # Determinar subtom (warm, cool, neutral)
        undertone = self._determine_undertone(dominant_colors)

        # Determinar profundidade (light, medium, deep)
        depth = self._determine_depth(dominant_colors)

        # Determinar intensidade (soft, medium, bright)
        intensity = self._determine_intensity(dominant_colors)

        # Classificar estacao
        season, season_subtype = self._classify_season(undertone, depth, intensity)

        # Gerar paleta de cores
        color_palette = self._generate_palette(undertone, depth, intensity)

        # Recomendacoes
        wardrobe = self._generate_wardrobe_recommendations(undertone, depth, season)
        makeup = self._generate_makeup_recommendations(undertone, depth, season)

        # Calcular confianca
        confidence = self._calculate_confidence(skin_regions, dominant_colors)

        return {
            "skin_undertone": undertone,
            "skin_depth": depth,
            "skin_intensity": intensity,
            "season": season,
            "season_subtype": season_subtype,
            "dominant_skin_colors": dominant_colors,
            "color_palette": color_palette,
            "wardrobe_recommendations": wardrobe,
            "makeup_colors": makeup,
            "confidence": confidence,
            "face_detected": True,
            "face_position": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
            "analysis_details": {
                "skin_regions_extracted": len(skin_regions),
                "color_clusters": len(dominant_colors),
            },
        }

    def _extract_skin_regions(
        self, img_rgb: np.ndarray, x: int, y: int, w: int, h: int
    ) -> List[np.ndarray]:
        """
        Extrai regioes de pele pura, evitando olhos, sobrancelhas e boca.
        """
        regions = []

        # Regiao da testa (superior, evitando sobrancelhas)
        forehead = img_rgb[y + int(h*0.05):y + int(h*0.25), x + int(w*0.2):x + int(w*0.8)]
        if forehead.size > 0:
            regions.append(forehead)

        # Regiao das bochechas (laterais, evitando olhos)
        left_cheek = img_rgb[y + int(h*0.35):y + int(h*0.65), x + int(w*0.05):x + int(w*0.35)]
        if left_cheek.size > 0:
            regions.append(left_cheek)

        right_cheek = img_rgb[y + int(h*0.35):y + int(h*0.65), x + int(w*0.65):x + int(w*0.95)]
        if right_cheek.size > 0:
            regions.append(right_cheek)

        # Regiao do queixo (inferior, evitando boca)
        chin = img_rgb[y + int(h*0.75):y + int(h*0.95), x + int(w*0.3):x + int(w*0.7)]
        if chin.size > 0:
            regions.append(chin)

        return regions

    def _extract_dominant_colors(self, skin_regions: List[np.ndarray]) -> List[Dict[str, Any]]:
        """
        Extrai cores dominantes das regioes de pele usando K-Means clustering.
        """
        # Combinar todas as regioes
        all_pixels = np.vstack([region.reshape(-1, 3) for region in skin_regions])

        # Filtrar pixels muito escuros (sombra) ou muito claros (brilho)
        mask = (
            (all_pixels[:, 0] > 40) & (all_pixels[:, 0] < 250) &
            (all_pixels[:, 1] > 40) & (all_pixels[:, 1] < 250) &
            (all_pixels[:, 2] > 40) & (all_pixels[:, 2] < 250)
        )
        filtered_pixels = all_pixels[mask]

        if len(filtered_pixels) < 100:
            filtered_pixels = all_pixels

        # K-Means para encontrar 3 cores dominantes
        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        kmeans.fit(filtered_pixels)

        colors = []
        for center in kmeans.cluster_centers_:
            r, g, b = int(center[0]), int(center[1]), int(center[2])
            hex_color = f"#{r:02x}{g:02x}{b:02x}"

            # Converter para HSV para analise
            hsv = cv2.cvtColor(np.uint8([[center]]), cv2.COLOR_RGB2HSV)[0][0]

            colors.append({
                "rgb": [r, g, b],
                "hex": hex_color,
                "hsv": {
                    "h": int(hsv[0] * 2),  # OpenCV H: 0-179 -> 0-358
                    "s": int(hsv[1] / 255 * 100),
                    "v": int(hsv[2] / 255 * 100),
                },
            })

        # Ordenar por valor (V) - do mais claro ao mais escuro
        colors.sort(key=lambda c: c["hsv"]["v"], reverse=True)

        return colors

    def _determine_undertone(self, dominant_colors: List[Dict]) -> str:
        """
        Determina subtom de pele (warm, cool, neutral) baseado nas cores dominantes.
        """
        warm_score = 0
        cool_score = 0

        for color in dominant_colors:
            h, s, v = color["hsv"]["h"], color["hsv"]["s"], color["hsv"]["v"]
            r, g, b = color["rgb"]

            # Analise de temperatura de cor
            # Warm: mais amarelo/dourado (H: 30-90, R > B)
            # Cool: mais rosa/azulado (H: 300-30 ou B > R)

            if 20 <= h <= 80:  # Amarelo/dourado
                warm_score += 1.5
            elif 300 <= h or h <= 20:  # Rosa/vermelho
                cool_score += 1.0

            # Razao R/B
            if r > b + 15:
                warm_score += 1.0
            elif b > r + 15:
                cool_score += 1.0

            # Saturacao
            if s > 30:
                if h > 300 or h < 60:
                    warm_score += 0.5
                elif 120 < h < 240:
                    cool_score += 0.5

        if warm_score > cool_score * 1.3:
            return "warm"
        elif cool_score > warm_score * 1.3:
            return "cool"
        return "neutral"

    def _determine_depth(self, dominant_colors: List[Dict]) -> str:
        """
        Determina profundidade da pele (light, medium, deep).
        """
        avg_value = np.mean([c["hsv"]["v"] for c in dominant_colors])

        if avg_value > 75:
            return "light"
        elif avg_value > 50:
            return "medium"
        return "deep"

    def _determine_intensity(self, dominant_colors: List[Dict]) -> str:
        """
        Determina intensidade da pele (soft, medium, bright).
        """
        avg_saturation = np.mean([c["hsv"]["s"] for c in dominant_colors])
        avg_value = np.mean([c["hsv"]["v"] for c in dominant_colors])

        # Contraste (diferenca entre cores mais claras e mais escuras)
        values = [c["hsv"]["v"] for c in dominant_colors]
        contrast = max(values) - min(values)

        if avg_saturation < 20 and contrast < 20:
            return "soft"
        elif avg_saturation > 40 or contrast > 35:
            return "bright"
        return "medium"

    def _classify_season(
        self, undertone: str, depth: str, intensity: str
    ) -> Tuple[str, str]:
        """
        Classifica em estacao do ano baseado no subtom, profundidade e intensidade.
        """
        # Mapeamento de combinacoes para estacoes
        season_map = {
            # Primavera (warm, light, bright/soft)
            ("warm", "light", "bright"): ("Spring", "Bright Spring"),
            ("warm", "light", "medium"): ("Spring", "Warm Spring"),
            ("warm", "light", "soft"): ("Spring", "Light Spring"),

            # Verao (cool, light, soft/medium)
            ("cool", "light", "soft"): ("Summer", "Soft Summer"),
            ("cool", "light", "medium"): ("Summer", "Light Summer"),
            ("cool", "medium", "soft"): ("Summer", "Cool Summer"),

            # Outono (warm, medium/deep, soft/medium)
            ("warm", "medium", "soft"): ("Autumn", "Soft Autumn"),
            ("warm", "medium", "medium"): ("Autumn", "Warm Autumn"),
            ("warm", "deep", "medium"): ("Autumn", "Deep Autumn"),
            ("warm", "deep", "soft"): ("Autumn", "Deep Autumn"),

            # Inverno (cool, medium/deep, bright)
            ("cool", "medium", "bright"): ("Winter", "Cool Winter"),
            ("cool", "deep", "bright"): ("Winter", "Deep Winter"),
            ("cool", "deep", "medium"): ("Winter", "Deep Winter"),
            ("cool", "medium", "medium"): ("Winter", "Cool Winter"),
        }

        key = (undertone, depth, intensity)
        if key in season_map:
            return season_map[key]

        # Fallback: encontrar a combinacao mais proxima
        if undertone == "warm":
            if depth == "light":
                return ("Spring", "Light Spring")
            else:
                return ("Autumn", "Warm Autumn")
        else:
            if depth == "light":
                return ("Summer", "Light Summer")
            else:
                return ("Winter", "Cool Winter")

    def _generate_palette(
        self, undertone: str, depth: str, intensity: str
    ) -> Dict[str, List[str]]:
        """
        Gera paleta de cores personalizada baseada na colorimetria.
        """
        palettes = {
            "Spring": {
                "best_colors": ["#FFD700", "#FF8C00", "#32CD32", "#FF6347", "#F0E68C", "#FFA500", "#98FB98", "#FFDAB9"],
                "good_colors": ["#87CEEB", "#DDA0DD", "#F4A460", "#90EE90"],
                "avoid_colors": ["#4B0082", "#000080", "#808080", "#2F4F4F", "#FF69B4"],
                "neutrals": ["#F5F5DC", "#DEB887", "#D2B48C", "#FFF8DC"],
            },
            "Summer": {
                "best_colors": ["#87CEEB", "#DDA0DD", "#98FB98", "#B0C4DE", "#D8BFD8", "#ADD8E6", "#E6E6FA", "#C0C0C0"],
                "good_colors": ["#FFB6C1", "#20B2AA", "#778899", "#9370DB"],
                "avoid_colors": ["#FF4500", "#8B4513", "#FFD700", "#FF8C00", "#FFA500"],
                "neutrals": ["#E0E0E0", "#C0C0C0", "#D3D3D3", "#B0C4DE"],
            },
            "Autumn": {
                "best_colors": ["#8B4513", "#D2691E", "#CD853F", "#A0522D", "#DEB887", "#556B2F", "#6B8E23", "#B8860B"],
                "good_colors": ["#F4A460", "#BC8F8F", "#808000", "#A0522D"],
                "avoid_colors": ["#FF69B4", "#00CED1", "#87CEEB", "#E6E6FA", "#DDA0DD"],
                "neutrals": ["#F5F5DC", "#D2B48C", "#8B7355", "#C2B280"],
            },
            "Winter": {
                "best_colors": ["#000080", "#4B0082", "#8B008B", "#DC143C", "#00CED1", "#191970", "#FF1493", "#00FA9A"],
                "good_colors": ["#4169E1", "#9400D3", "#FF4500", "#00FF7F"],
                "avoid_colors": ["#D2691E", "#CD853F", "#DEB887", "#F5F5DC", "#808000"],
                "neutrals": ["#000000", "#2F4F4F", "#696969", "#A9A9A9"],
            },
        }

        season, _ = self._classify_season(undertone, depth, intensity)
        return palettes.get(season, palettes["Autumn"])

    def _generate_wardrobe_recommendations(
        self, undertone: str, depth: str, season: str
    ) -> Dict[str, List[str]]:
        """
        Gera recomendacoes de guarda-roupa.
        """
        recommendations = {
            "Spring": {
                "formal": ["Tons quentes claros", "Bege dourado", "Creme", "Azul claro quente"],
                "casual": ["Coral", "Pessego", "Verde menta", "Amarelo claro"],
                "camera": ["Evitar branco puro", "Preferir tons quentes neutros", "Iluminadores dourados"],
            },
            "Summer": {
                "formal": ["Azul acinzentado", "Rosa antigo", "Lavanda", "Cinza claro"],
                "casual": ["Rosa bebe", "Azul celeste", "Verde agua", "Lilas"],
                "camera": ["Evitar laranja e dourado", "Preferir tons frios suaves", "Iluminadores perolados"],
            },
            "Autumn": {
                "formal": ["Tons terrosos escuros", "Marrom chocolate", "Verde oliva", "Bordô"],
                "casual": ["Oliva", "Mostarda", "Caramelo", "Telha", "Cobre"],
                "camera": ["Tons quentes neutros", "Evitar branco puro", "Iluminadores bronze"],
            },
            "Winter": {
                "formal": ["Preto", "Azul marinho", "Vinho", "Roxo profundo", "Branco puro"],
                "casual": ["Fucsia", "Turquesa", "Verde esmeralda", "Vermelho vivo"],
                "camera": ["Cores vivas e contrastantes", "Evitar tons terrosos", "Iluminadores prateados"],
            },
        }

        return recommendations.get(season, recommendations["Autumn"])

    def _generate_makeup_recommendations(
        self, undertone: str, depth: str, season: str
    ) -> Dict[str, Any]:
        """
        Gera recomendacoes de maquiagem.
        """
        makeup = {
            "Spring": {
                "foundation": "Bege dourado ou amarelado claro",
                "blush": "Pessego, coral ou salmao",
                "lipstick": ["Coral", "Pessego", "Nude quente", "Rosa salmao"],
                "eyeshadow": ["Dourado", "Bronze claro", "Verde menta", "Coral"],
                "highlighter": "Dourado champagne",
            },
            "Summer": {
                "foundation": "Bege rosado ou neutro claro",
                "blush": "Rosa bebe, lilas ou malva",
                "lipstick": ["Rosa bebe", "Malva", "Nude rosado", "Beringela clara"],
                "eyeshadow": ["Prata", "Cinza perola", "Lavanda", "Rosa antigo"],
                "highlighter": "Perola ou prateado",
            },
            "Autumn": {
                "foundation": "Bege medio quente ou avela",
                "blush": "Pessego ou bronze",
                "lipstick": ["Terra", "Caramelo", "Nude quente", "Bordô leve"],
                "eyeshadow": ["Bronze", "Dourado suave", "Verde oliva", "Marrom quente"],
                "highlighter": "Bronze ou ouro rosado",
            },
            "Winter": {
                "foundation": "Bege neutro ou rosado medio a profundo",
                "blush": "Rosa fucsia ou ameixa",
                "lipstick": ["Vermelho vivo", "Fucsia", "Bordô", "Ameixa", "Rosa choque"],
                "eyeshadow": ["Prata", "Grafite", "Roxo profundo", "Azul marinho", "Preto esfumado"],
                "highlighter": "Prata ou diamante",
            },
        }

        return makeup.get(season, makeup["Autumn"])

    def _calculate_confidence(
        self, skin_regions: List[np.ndarray], dominant_colors: List[Dict]
    ) -> float:
        """
        Calcula confianca da analise.
        """
        confidence = 0.5

        # Mais regioes = mais confianca
        confidence += min(0.2, len(skin_regions) * 0.05)

        # Cores bem distribuidas = mais confianca
        if len(dominant_colors) >= 3:
            confidence += 0.15

        # Variacao de valor entre cores (deve haver alguma variacao)
        values = [c["hsv"]["v"] for c in dominant_colors]
        if len(values) > 1:
            value_std = np.std(values)
            if 5 < value_std < 40:
                confidence += 0.15

        return round(min(0.95, confidence), 2)

    def _error_result(self, message: str) -> Dict[str, Any]:
        """Retorna resultado de erro."""
        return {
            "skin_undertone": "unknown",
            "skin_depth": "unknown",
            "skin_intensity": "unknown",
            "season": "unknown",
            "season_subtype": "unknown",
            "color_palette": {},
            "wardrobe_recommendations": {},
            "makeup_colors": {},
            "confidence": 0.0,
            "face_detected": False,
            "error": message,
        }
