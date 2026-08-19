"""
PortfolioAgent - Gerenciamento e otimizacao inteligente de portfolio.

Responsabilidades:
- Analisar e organizar fotos/videos do portfolio
- Sugerir melhores fotos para cada tipo de casting
- Calcular score de diversidade do portfolio
- Identificar gaps (falta de fotos de perfil, corpo inteiro, etc.)
- Gerar PDF do portfolio otimizado
- Acompanhar metricas de visualizacao
"""

import random
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.agents.base import VisionAgent, AgentContext, AgentResult, AgentCapability


class PortfolioAgent(VisionAgent):
    """Agente especializado em gerenciamento e otimizacao de portfolio."""

    # Tipos de foto essenciais para um portfolio completo
    ESSENTIAL_SHOT_TYPES = [
        "headshot",
        "profile",
        "full_body",
        "half_body",
        "close_up",
        "smiling",
        "serious",
        "casual",
        "formal",
        "editorial",
        "commercial",
        "lifestyle",
        "action",
        "beauty",
        "fashion",
    ]

    # Criterios de avaliacao de fotos
    QUALITY_CRITERIA = {
        "lighting": {"weight": 0.25, "description": "Iluminacao adequada"},
        "focus": {"weight": 0.20, "description": "Foco nitido"},
        "composition": {"weight": 0.20, "description": "Composicao equilibrada"},
        "expression": {"weight": 0.15, "description": "Expressao natural"},
        "background": {"weight": 0.10, "description": "Fundo limpo"},
        "color": {"weight": 0.10, "description": "Correcao de cor"},
    }

    # Templates de portfolio por objetivo
    PORTFOLIO_TEMPLATES = {
        "modeling": {
            "essential_shots": [
                "headshot",
                "full_body",
                "half_body",
                "profile",
                "editorial",
                "commercial",
            ],
            "recommended_count": (12, 20),
            "diversity_requirements": ["studio", "outdoor", "black_white", "color"],
        },
        "acting": {
            "essential_shots": [
                "headshot",
                "close_up",
                "smiling",
                "serious",
                "action",
                "character",
            ],
            "recommended_count": (8, 15),
            "diversity_requirements": ["dramatic", "comedic", "neutral", "intense"],
        },
        "influencer": {
            "essential_shots": [
                "lifestyle",
                "casual",
                "product",
                "selfie_style",
                "behind_scenes",
            ],
            "recommended_count": (15, 30),
            "diversity_requirements": ["indoor", "outdoor", "brand_collab", "personal"],
        },
        "commercial": {
            "essential_shots": [
                "headshot",
                "smiling",
                "product_holding",
                "lifestyle",
                "family_style",
            ],
            "recommended_count": (10, 18),
            "diversity_requirements": ["friendly", "professional", "approachable"],
        },
    }

    def __init__(self):
        super().__init__(
            name="PortfolioAgent",
            description="Gerenciamento e otimizacao inteligente de portfolio",
            capabilities=[
                AgentCapability.PORTFOLIO_MANAGEMENT,
                AgentCapability.PORTFOLIO_OPTIMIZATION,
            ],
        )

    def can_handle(self, context: AgentContext) -> bool:
        return context.intent in [
            "UPDATE_PORTFOLIO",
            "OPTIMIZE_PORTFOLIO",
            "ANALYZE_PORTFOLIO",
            "SUGGEST_SHOTS",
            "GENERATE_PORTFOLIO_PDF",
            "PORTFOLIO_GAP_ANALYSIS",
            "SELECT_BEST_PHOTOS",
        ]

    async def execute(self, context: AgentContext) -> AgentResult:
        self._increment_execution()

        intent = context.intent
        input_data = context.input_data

        try:
            if intent == "UPDATE_PORTFOLIO":
                result = await self._update_portfolio(input_data)
            elif intent == "OPTIMIZE_PORTFOLIO":
                result = await self._optimize_portfolio(input_data)
            elif intent == "ANALYZE_PORTFOLIO":
                result = await self._analyze_portfolio(input_data)
            elif intent == "SUGGEST_SHOTS":
                result = await self._suggest_shots(input_data)
            elif intent == "GENERATE_PORTFOLIO_PDF":
                result = await self._generate_pdf(input_data)
            elif intent == "PORTFOLIO_GAP_ANALYSIS":
                result = await self._gap_analysis(input_data)
            elif intent == "SELECT_BEST_PHOTOS":
                result = await self._select_best_photos(input_data)
            else:
                return AgentResult(
                    success=False,
                    error=f"Intencao '{intent}' nao suportada pelo PortfolioAgent",
                )

            return AgentResult(
                success=True,
                data=result,
                message=f"PortfolioAgent executou '{intent}' com sucesso",
            )

        except Exception as e:
            self._increment_error()
            return AgentResult(
                success=False,
                error=f"Erro no PortfolioAgent: {str(e)}",
            )

    def validate(self, result: AgentResult) -> bool:
        if not result.success:
            return False
        data = result.data or {}
        if "portfolio_score" in data and not (0 <= data["portfolio_score"] <= 100):
            return False
        return True

    # ========== IMPLEMENTACOES ==========

    async def _update_portfolio(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza portfolio com novas fotos."""
        photos = data.get("photos", [])
        portfolio_type = data.get("portfolio_type", "modeling")

        # Analisar cada foto
        analyzed_photos = []
        for photo in photos:
            analyzed = self._analyze_photo(photo)
            analyzed_photos.append(analyzed)

        # Calcular score geral
        overall_score = self._calculate_portfolio_score(analyzed_photos, portfolio_type)

        return {
            "photos_added": len(photos),
            "analyzed_photos": analyzed_photos,
            "portfolio_score": overall_score,
            "portfolio_type": portfolio_type,
            "updated_at": datetime.utcnow().isoformat(),
        }

    async def _optimize_portfolio(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Otimiza portfolio removendo fotos fracas e sugerindo melhorias."""
        photos = data.get("photos", [])
        portfolio_type = data.get("portfolio_type", "modeling")
        target_count = data.get("target_count", 15)

        # Analisar todas as fotos
        analyzed = [self._analyze_photo(p) for p in photos]

        # Ordenar por score
        analyzed.sort(key=lambda x: x["overall_score"], reverse=True)

        # Selecionar as melhores
        best_photos = analyzed[:target_count]

        # Verificar diversidade
        diversity_score = self._calculate_diversity(best_photos)

        # Fotos removidas
        removed = analyzed[target_count:]

        return {
            "optimized_photos": best_photos,
            "photos_removed": len(removed),
            "removed_reasons": [
                f"{p['id']}: score {p['overall_score']}" for p in removed
            ],
            "diversity_score": diversity_score,
            "portfolio_score": self._calculate_portfolio_score(
                best_photos, portfolio_type
            ),
            "recommendations": self._optimization_recommendations(
                best_photos, portfolio_type
            ),
        }

    async def _analyze_portfolio(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analise completa do portfolio."""
        photos = data.get("photos", [])
        portfolio_type = data.get("portfolio_type", "modeling")

        if not photos:
            return {
                "portfolio_score": 0,
                "status": "empty",
                "message": "Portfolio vazio. Adicione fotos para analise.",
            }

        analyzed = [self._analyze_photo(p) for p in photos]

        # Estatisticas
        scores = [p["overall_score"] for p in analyzed]
        avg_score = sum(scores) / len(scores)
        best_photo = max(analyzed, key=lambda x: x["overall_score"])
        worst_photo = min(analyzed, key=lambda x: x["overall_score"])

        # Diversidade
        diversity = self._calculate_diversity(analyzed)

        # Gaps
        gaps = self._identify_gaps(analyzed, portfolio_type)

        return {
            "portfolio_score": self._calculate_portfolio_score(
                analyzed, portfolio_type
            ),
            "total_photos": len(photos),
            "average_photo_score": round(avg_score, 1),
            "best_photo": best_photo["id"],
            "best_photo_score": best_photo["overall_score"],
            "worst_photo": worst_photo["id"],
            "worst_photo_score": worst_photo["overall_score"],
            "diversity_score": diversity,
            "gaps": gaps,
            "strengths": self._identify_strengths(analyzed),
            "status": self._portfolio_status(
                self._calculate_portfolio_score(analyzed, portfolio_type)
            ),
        }

    async def _suggest_shots(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sugere tipos de fotos que faltam no portfolio."""
        portfolio_type = data.get("portfolio_type", "modeling")
        existing_photos = data.get("existing_photos", [])

        template = self.PORTFOLIO_TEMPLATES.get(
            portfolio_type, self.PORTFOLIO_TEMPLATES["modeling"]
        )
        essential = template["essential_shots"]

        # Identificar quais tipos ja existem
        existing_types = set()
        for photo in existing_photos:
            photo_type = photo.get("type", "")
            if photo_type in essential:
                existing_types.add(photo_type)

        # Tipos faltantes
        missing = [t for t in essential if t not in existing_types]

        # Sugerir fotos especificas
        suggestions = []
        for shot_type in missing:
            suggestions.append(
                {
                    "shot_type": shot_type,
                    "priority": "high" if shot_type in essential[:4] else "medium",
                    "description": self._shot_description(shot_type),
                    "tips": self._shot_tips(shot_type),
                    "estimated_cost": random.choice(["low", "medium", "high"]),
                }
            )

        return {
            "portfolio_type": portfolio_type,
            "missing_shots": missing,
            "suggestions": suggestions,
            "completion_rate": len(existing_types) / len(essential) if essential else 0,
            "priority": "high" if len(missing) > 3 else "medium" if missing else "low",
        }

    async def _generate_pdf(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Gera especificacoes para PDF do portfolio."""
        photos = data.get("photos", [])
        portfolio_type = data.get("portfolio_type", "modeling")
        layout = data.get("layout", "grid")

        # Selecionar melhores fotos
        analyzed = [self._analyze_photo(p) for p in photos]
        analyzed.sort(key=lambda x: x["overall_score"], reverse=True)
        best = analyzed[: min(15, len(analyzed))]

        return {
            "pdf_specifications": {
                "page_count": len(best),
                "layout": layout,
                "page_size": "A4",
                "orientation": "portrait",
                "color_mode": "RGB",
                "resolution_dpi": 300,
            },
            "photo_order": [p["id"] for p in best],
            "cover_photo": best[0]["id"] if best else None,
            "back_cover_text": self._generate_back_cover(portfolio_type),
            "estimated_file_size_mb": round(len(best) * 2.5, 1),
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _gap_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analise detalhada de gaps no portfolio."""
        photos = data.get("photos", [])
        portfolio_type = data.get("portfolio_type", "modeling")

        analyzed = [self._analyze_photo(p) for p in photos]
        template = self.PORTFOLIO_TEMPLATES.get(
            portfolio_type, self.PORTFOLIO_TEMPLATES["modeling"]
        )

        gaps = []

        # Gap: tipos de foto faltantes
        existing_types = {p.get("type", "") for p in photos}
        for essential in template["essential_shots"]:
            if essential not in existing_types:
                gaps.append(
                    {
                        "type": "missing_shot_type",
                        "severity": "high",
                        "description": f"Falta foto tipo '{essential}'",
                        "impact": "Reduz chances em castings especificos",
                    }
                )

        # Gap: pouca diversidade
        diversity = self._calculate_diversity(analyzed)
        if diversity < 0.5:
            gaps.append(
                {
                    "type": "low_diversity",
                    "severity": "medium",
                    "description": "Portfolio com pouca variedade de estilos",
                    "impact": "Pode parecer repetitivo para clientes",
                }
            )

        # Gap: poucas fotos
        min_count, _ = template["recommended_count"]
        if len(photos) < min_count:
            gaps.append(
                {
                    "type": "insufficient_photos",
                    "severity": "medium",
                    "description": f"Portfolio tem {len(photos)} fotos (minimo recomendado: {min_count})",
                    "impact": "Portfolio pode parecer incompleto",
                }
            )

        # Gap: qualidade baixa
        low_quality = [p for p in analyzed if p["overall_score"] < 50]
        if len(low_quality) > len(analyzed) * 0.3:
            gaps.append(
                {
                    "type": "low_quality_photos",
                    "severity": "high",
                    "description": f"{len(low_quality)} fotos com qualidade abaixo do ideal",
                    "impact": "Reduz percepcao profissional",
                }
            )

        return {
            "total_gaps": len(gaps),
            "gaps": gaps,
            "critical_gaps": len([g for g in gaps if g["severity"] == "high"]),
            "action_plan": self._generate_action_plan(gaps),
        }

    async def _select_best_photos(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Seleciona as melhores fotos para um objetivo especifico."""
        photos = data.get("photos", [])
        objective = data.get("objective", "general")
        count = data.get("count", 5)

        analyzed = [self._analyze_photo(p) for p in photos]

        # Ajustar score baseado no objetivo
        for photo in analyzed:
            photo["objective_score"] = self._calculate_objective_score(photo, objective)

        # Ordenar por objective_score
        analyzed.sort(key=lambda x: x["objective_score"], reverse=True)
        selected = analyzed[:count]

        return {
            "objective": objective,
            "selected_photos": [p["id"] for p in selected],
            "selection_criteria": f"Otimizado para {objective}",
            "confidence": (
                "high" if selected and selected[0]["objective_score"] > 80 else "medium"
            ),
        }

    # ========== HELPERS ==========

    def _analyze_photo(self, photo: Dict[str, Any]) -> Dict[str, Any]:
        """Analisa uma foto individual."""
        photo_id = photo.get("id", f"photo_{random.randint(1000, 9999)}")
        photo_type = photo.get("type", "unknown")

        # Simular analise de qualidade (em producao, usaria IA de analise de imagem)
        scores = {}
        for criterion, info in self.QUALITY_CRITERIA.items():
            scores[criterion] = round(random.uniform(60, 98), 1)

        overall = sum(
            scores[c] * info["weight"] for c, info in self.QUALITY_CRITERIA.items()
        )

        return {
            "id": photo_id,
            "type": photo_type,
            "scores": scores,
            "overall_score": round(overall, 1),
            "quality_level": self._quality_level(overall),
            "tags": photo.get("tags", []),
        }

    def _calculate_portfolio_score(
        self, photos: List[Dict], portfolio_type: str
    ) -> int:
        """Calcula score geral do portfolio (0-100)."""
        if not photos:
            return 0

        # Media dos scores
        avg_score = sum(p["overall_score"] for p in photos) / len(photos)

        # Bonus por diversidade
        diversity = self._calculate_diversity(photos)

        # Bonus por quantidade
        template = self.PORTFOLIO_TEMPLATES.get(
            portfolio_type, self.PORTFOLIO_TEMPLATES["modeling"]
        )
        min_count, max_count = template["recommended_count"]
        count_score = min(1.0, len(photos) / min_count) if min_count > 0 else 1.0

        # Score final
        final = (avg_score * 0.5) + (diversity * 25) + (count_score * 25)
        return min(100, int(final))

    def _calculate_diversity(self, photos: List[Dict]) -> float:
        """Calcula score de diversidade (0-1)."""
        if not photos:
            return 0.0

        types = [p.get("type", "unknown") for p in photos]
        unique_types = set(types)

        # Razao de tipos unicos vs total
        type_ratio = len(unique_types) / max(len(self.ESSENTIAL_SHOT_TYPES), len(types))

        # Verificar variedade de tags/estilos
        all_tags = []
        for p in photos:
            all_tags.extend(p.get("tags", []))
        unique_tags = set(all_tags)
        tag_ratio = len(unique_tags) / max(len(all_tags), 1)

        return round((type_ratio * 0.6 + tag_ratio * 0.4), 2)

    def _identify_gaps(self, photos: List[Dict], portfolio_type: str) -> List[Dict]:
        """Identifica gaps no portfolio."""
        template = self.PORTFOLIO_TEMPLATES.get(
            portfolio_type, self.PORTFOLIO_TEMPLATES["modeling"]
        )
        existing_types = {p.get("type", "") for p in photos}

        gaps = []
        for essential in template["essential_shots"]:
            if essential not in existing_types:
                gaps.append(
                    {
                        "type": "missing",
                        "shot_type": essential,
                        "priority": "high",
                    }
                )

        return gaps

    def _identify_strengths(self, photos: List[Dict]) -> List[str]:
        """Identifica pontos fortes do portfolio."""
        strengths = []

        avg_score = (
            sum(p["overall_score"] for p in photos) / len(photos) if photos else 0
        )
        if avg_score > 80:
            strengths.append("Alta qualidade geral das fotos")

        types = {p.get("type", "") for p in photos}
        if len(types) >= 8:
            strengths.append("Boa diversidade de tipos de foto")

        if len(photos) >= 12:
            strengths.append("Portfolio bem completo em quantidade")

        best_criteria = {}
        for p in photos:
            for criterion, score in p.get("scores", {}).items():
                if criterion not in best_criteria or score > best_criteria[criterion]:
                    best_criteria[criterion] = score

        for criterion, score in best_criteria.items():
            if score > 90:
                strengths.append(f"Excelente em {criterion}")

        return strengths if strengths else ["Portfolio em desenvolvimento"]

    def _portfolio_status(self, score: int) -> str:
        if score >= 85:
            return "excellent"
        elif score >= 70:
            return "good"
        elif score >= 50:
            return "average"
        elif score >= 30:
            return "below_average"
        return "needs_work"

    def _quality_level(self, score: float) -> str:
        if score >= 90:
            return "excellent"
        elif score >= 75:
            return "very_good"
        elif score >= 60:
            return "good"
        elif score >= 45:
            return "average"
        return "below_average"

    def _shot_description(self, shot_type: str) -> str:
        descriptions = {
            "headshot": "Foco no rosto, ombros levemente visiveis. Expressao neutra ou sutil.",
            "full_body": "Corpo inteiro, mostrando proporcao e postura.",
            "half_body": "Do pe para cima, equilibrio entre rosto e corpo.",
            "profile": "Vista lateral do rosto, destacando estrutura ossea.",
            "close_up": "Muito proximo do rosto, destacando olhos e textura da pele.",
            "smiling": "Sorriso natural e autentico, transmite acessibilidade.",
            "serious": "Expressao seria/intensa, para papeis dramaticos.",
            "editorial": "Estilo revista, pose artistica e conceitual.",
            "commercial": "Acessivel e amigavel, ideal para publicidade.",
        }
        return descriptions.get(shot_type, f"Foto tipo {shot_type}")

    def _shot_tips(self, shot_type: str) -> List[str]:
        tips = {
            "headshot": ["Usar luz suave frontal", "Fundo neutro", "Foco nos olhos"],
            "full_body": [
                "Roupa que valorize silhueta",
                "Postura ereta",
                "Angulo levemente baixo",
            ],
            "profile": ["Lateral limpa", "Destacar linha do maxilar", "Luz de lado"],
            "editorial": ["Pose dinamica", "Expressao intensa", "Locacao interessante"],
        }
        return tips.get(
            shot_type, ["Consultar fotografo profissional", "Preparar referencias"]
        )

    def _optimization_recommendations(
        self, photos: List[Dict], portfolio_type: str
    ) -> List[str]:
        recs = []
        types = {p.get("type", "") for p in photos}

        if "headshot" not in types:
            recs.append(
                "Adicionar headshot profissional - essencial para todos os portfoliios"
            )
        if "full_body" not in types:
            recs.append("Incluir foto de corpo inteiro - importante para modelos")
        if len(photos) < 10:
            recs.append("Aumentar numero de fotos para pelo menos 12")

        avg = sum(p["overall_score"] for p in photos) / len(photos) if photos else 0
        if avg < 70:
            recs.append("Considerar substituir fotos com score abaixo de 70 por novas")

        return recs if recs else ["Portfolio bem otimizado!"]

    def _generate_action_plan(self, gaps: List[Dict]) -> List[Dict]:
        """Gera plano de acao para resolver gaps."""
        plan = []
        for gap in gaps:
            if gap["type"] == "missing_shot_type":
                plan.append(
                    {
                        "action": f"Agendar ensaio para foto tipo '{gap.get('shot_type', '')}'",
                        "priority": gap["severity"],
                        "timeline": "1-2 semanas",
                    }
                )
            elif gap["type"] == "low_diversity":
                plan.append(
                    {
                        "action": "Planejar ensaio com diferentes estilos e locacoes",
                        "priority": gap["severity"],
                        "timeline": "2-4 semanas",
                    }
                )
            elif gap["type"] == "insufficient_photos":
                plan.append(
                    {
                        "action": "Realizar ensaio completo para aumentar quantidade",
                        "priority": gap["severity"],
                        "timeline": "1-3 semanas",
                    }
                )
        return plan

    def _calculate_objective_score(self, photo: Dict, objective: str) -> float:
        """Ajusta score da foto baseado no objetivo."""
        base_score = photo.get("overall_score", 50)
        photo_type = photo.get("type", "")

        # Multiplicadores por objetivo
        multipliers = {
            "commercial": {"commercial": 1.3, "smiling": 1.2, "lifestyle": 1.1},
            "editorial": {"editorial": 1.3, "fashion": 1.2, "artistic": 1.1},
            "casting": {"headshot": 1.2, "full_body": 1.2, "profile": 1.1},
            "social_media": {"lifestyle": 1.2, "casual": 1.1, "behind_scenes": 1.1},
        }

        obj_mult = multipliers.get(objective, {})
        mult = obj_mult.get(photo_type, 1.0)

        return min(100, base_score * mult)

    def _generate_back_cover(self, portfolio_type: str) -> str:
        texts = {
            "modeling": "Modelo profissional disponivel para trabalhos editoriais, comerciais e desfiles.",
            "acting": "Ator/Atriz versatil com experiencia em teatro, cinema e publicidade.",
            "influencer": "Criador de conteudo especializado em lifestyle, moda e beleza.",
        }
        return texts.get(portfolio_type, "Profissional disponivel para oportunidades.")
