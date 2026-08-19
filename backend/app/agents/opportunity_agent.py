"""
OpportunityAgent - Busca e matching inteligente de oportunidades.

Responsabilidades:
- Buscar castings e oportunidades em multiplas fontes
- Fazer matching entre perfil do talento e requisitos do casting
- Alertar sobre novas oportunidades relevantes
- Analisar taxa de sucesso por tipo de oportunidade
- Rastrear aplicacoes e follow-ups
"""

import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.agents.base import VisionAgent, AgentContext, AgentResult, AgentCapability


class OpportunityAgent(VisionAgent):
    """Agente especializado em busca e matching de oportunidades."""

    # Categorias de oportunidades
    OPPORTUNITY_TYPES = [
        "casting",
        "editorial",
        "commercial",
        "runway",
        "tv_commercial",
        "film",
        "theater",
        "digital_content",
        "brand_collaboration",
        "event",
        "workshop",
    ]

    # Requisitos comuns por tipo
    REQUIREMENTS_BY_TYPE = {
        "casting": ["headshot", "full_body", "age_range", "height", "experience"],
        "editorial": ["portfolio", "editorial_photos", "versatility", "expressions"],
        "commercial": ["smiling_photos", "approachable", "age_range", "ethnicity"],
        "runway": ["height", "measurements", "walk_experience", "runway_photos"],
        "tv_commercial": ["acting_reel", "camera_presence", "speaking_ability"],
        "film": ["acting_reel", "credits", "training", "availability"],
        "digital_content": ["social_media", "engagement_rate", "content_quality"],
        "brand_collaboration": [
            "followers",
            "engagement",
            "niche_match",
            "previous_collabs",
        ],
    }

    # Fontes de oportunidades (simuladas - em producao seriam APIs reais)
    SOURCES = [
        {"name": "Casting Networks", "type": "platform", "reliability": 0.9},
        {"name": "Backstage", "type": "platform", "reliability": 0.85},
        {"name": "Instagram", "type": "social", "reliability": 0.6},
        {"name": "Agente Pessoal", "type": "direct", "reliability": 0.95},
        {"name": "Site da Agencia", "type": "direct", "reliability": 0.9},
        {"name": "Indicacao", "type": "network", "reliability": 0.8},
        {"name": "Newsletter", "type": "platform", "reliability": 0.7},
    ]

    def __init__(self):
        super().__init__(
            name="OpportunityAgent",
            description="Busca e matching inteligente de oportunidades",
            capabilities=[
                AgentCapability.OPPORTUNITY_SEARCH,
                AgentCapability.OPPORTUNITY_MATCHING,
            ],
        )

    def can_handle(self, context: AgentContext) -> bool:
        return context.intent in [
            "SEARCH_OPPORTUNITIES",
            "FIND_MATCHES",
            "ALERT_NEW_OPPORTUNITIES",
            "ANALYZE_APPLICATION_HISTORY",
            "TRACK_APPLICATION",
            "OPPORTUNITY_MATCHING_SCORE",
            "SUGEST_OPPORTUNITIES",
        ]

    async def execute(self, context: AgentContext) -> AgentResult:
        self._increment_execution()

        intent = context.intent
        input_data = context.input_data

        try:
            if intent == "SEARCH_OPPORTUNITIES":
                result = await self._search_opportunities(input_data)
            elif intent == "FIND_MATCHES":
                result = await self._find_matches(input_data)
            elif intent == "ALERT_NEW_OPPORTUNITIES":
                result = await self._alert_new_opportunities(input_data)
            elif intent == "ANALYZE_APPLICATION_HISTORY":
                result = await self._analyze_history(input_data)
            elif intent == "TRACK_APPLICATION":
                result = await self._track_application(input_data)
            elif intent == "OPPORTUNITY_MATCHING_SCORE":
                result = await self._matching_score(input_data)
            elif intent == "SUGEST_OPPORTUNITIES":
                result = await self._suggest_opportunities(input_data)
            else:
                return AgentResult(
                    success=False,
                    error=f"Intencao '{intent}' nao suportada pelo OpportunityAgent",
                )

            return AgentResult(
                success=True,
                data=result,
                message=f"OpportunityAgent executou '{intent}' com sucesso",
            )

        except Exception as e:
            self._increment_error()
            return AgentResult(
                success=False,
                error=f"Erro no OpportunityAgent: {str(e)}",
            )

    def validate(self, result: AgentResult) -> bool:
        if not result.success:
            return False
        data = result.data or {}
        if "opportunities" in data and not isinstance(data["opportunities"], list):
            return False
        return True

    # ========== IMPLEMENTACOES ==========

    async def _search_opportunities(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Busca oportunidades em multiplas fontes."""
        profile = data.get("profile", {})
        filters = data.get("filters", {})
        location = data.get("location", "Sao Paulo")

        # Buscar em todas as fontes
        all_opportunities = []
        for source in self.SOURCES:
            ops = self._fetch_from_source(source, profile, filters, location)
            all_opportunities.extend(ops)

        # Ordenar por relevancia
        all_opportunities.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Aplicar filtros
        filtered = self._apply_filters(all_opportunities, filters)

        return {
            "opportunities": filtered[:20],
            "total_found": len(all_opportunities),
            "total_filtered": len(filtered),
            "sources_checked": len(self.SOURCES),
            "search_location": location,
            "search_date": datetime.utcnow().isoformat(),
        }

    async def _find_matches(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Encontra melhores matches entre perfil e oportunidades."""
        profile = data.get("profile", {})
        opportunities = data.get("opportunities", [])

        matches = []
        for opp in opportunities:
            match_score = self._calculate_match_score(profile, opp)
            if match_score["overall"] >= 60:  # So retornar matches decentes
                matches.append(
                    {
                        "opportunity": opp,
                        "match_score": match_score,
                        "recommendation": self._match_recommendation(match_score),
                    }
                )

        # Ordenar por score
        matches.sort(key=lambda x: x["match_score"]["overall"], reverse=True)

        return {
            "matches": matches[:10],
            "total_matches": len(matches),
            "high_confidence_matches": len(
                [m for m in matches if m["match_score"]["overall"] >= 80]
            ),
            "profile_summary": self._profile_summary(profile),
        }

    async def _alert_new_opportunities(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Configura alertas para novas oportunidades."""
        profile = data.get("profile", {})
        alert_criteria = data.get("criteria", {})

        # Simular novas oportunidades que surgiram
        new_opportunities = self._generate_new_opportunities(profile, alert_criteria)

        # Filtrar as mais relevantes
        relevant = [opp for opp in new_opportunities if opp["relevance_score"] >= 70]

        return {
            "new_opportunities": relevant,
            "alert_config": {
                "frequency": alert_criteria.get("frequency", "daily"),
                "channels": alert_criteria.get("channels", ["email", "push"]),
                "min_relevance": alert_criteria.get("min_relevance", 70),
            },
            "next_check": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            "total_new": len(new_opportunities),
            "high_relevance": len(relevant),
        }

    async def _analyze_history(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analisa historico de aplicacoes."""
        applications = data.get("applications", [])

        if not applications:
            return {
                "message": "Nenhuma aplicacao encontrada",
                "total_applications": 0,
            }

        total = len(applications)
        approved = len([a for a in applications if a.get("status") == "approved"])
        rejected = len([a for a in applications if a.get("status") == "rejected"])
        pending = len([a for a in applications if a.get("status") == "pending"])

        # Taxa de sucesso
        success_rate = (approved / total * 100) if total > 0 else 0

        # Por tipo
        by_type = {}
        for app in applications:
            opp_type = app.get("opportunity_type", "unknown")
            if opp_type not in by_type:
                by_type[opp_type] = {"total": 0, "approved": 0}
            by_type[opp_type]["total"] += 1
            if app.get("status") == "approved":
                by_type[opp_type]["approved"] += 1

        # Melhores tipos
        best_types = sorted(
            by_type.items(),
            key=lambda x: x[1]["approved"] / max(x[1]["total"], 1),
            reverse=True,
        )

        return {
            "total_applications": total,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
            "success_rate": round(success_rate, 1),
            "by_type": {
                k: {
                    "total": v["total"],
                    "approved": v["approved"],
                    "rate": round(v["approved"] / max(v["total"], 1) * 100, 1),
                }
                for k, v in by_type.items()
            },
            "best_performing_types": [t[0] for t in best_types[:3]],
            "recommendations": self._history_recommendations(success_rate, by_type),
        }

    async def _track_application(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Rastreia status de uma aplicacao especifica."""
        application_id = data.get("application_id", "")
        current_status = data.get("current_status", "submitted")

        # Timeline simulada
        timeline = [
            {
                "status": "submitted",
                "date": (datetime.utcnow() - timedelta(days=5)).isoformat(),
                "note": "Aplicacao enviada com sucesso",
            },
            {
                "status": "under_review",
                "date": (datetime.utcnow() - timedelta(days=3)).isoformat(),
                "note": "Perfil em analise pelo time de casting",
            },
        ]

        if current_status in ["approved", "rejected", "shortlisted"]:
            timeline.append(
                {
                    "status": current_status,
                    "date": datetime.utcnow().isoformat(),
                    "note": self._status_note(current_status),
                }
            )

        # Proximos passos
        next_steps = self._next_steps(current_status)

        return {
            "application_id": application_id,
            "current_status": current_status,
            "timeline": timeline,
            "next_steps": next_steps,
            "estimated_response": self._estimated_response(current_status),
        }

    async def _matching_score(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula score de matching detalhado."""
        profile = data.get("profile", {})
        opportunity = data.get("opportunity", {})

        score = self._calculate_match_score(profile, opportunity)

        return {
            "overall_score": score["overall"],
            "breakdown": score["breakdown"],
            "strengths": score["strengths"],
            "weaknesses": score["weaknesses"],
            "recommendation": score["recommendation"],
            "confidence": score["confidence"],
        }

    async def _suggest_opportunities(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sugere oportunidades baseadas no perfil e historico."""
        profile = data.get("profile", {})
        history = data.get("history", [])

        # Identificar tipos com melhor performance
        best_types = self._best_types_from_history(history)

        # Gerar sugestoes personalizadas
        suggestions = []
        for opp_type in best_types[:3]:
            suggestions.append(
                {
                    "type": opp_type,
                    "reason": f"Baseado no seu historico de sucesso em {opp_type}",
                    "suggested_platforms": self._suggested_platforms(opp_type),
                    "preparation_tips": self._preparation_tips(opp_type),
                    "estimated_success_rate": random.randint(60, 90),
                }
            )

        # Adicionar oportunidades fora da zona de conforto
        unexplored = [t for t in self.OPPORTUNITY_TYPES if t not in best_types]
        if unexplored:
            suggestions.append(
                {
                    "type": random.choice(unexplored),
                    "reason": "Oportunidade fora da sua zona de conforto para diversificar",
                    "suggested_platforms": self._suggested_platforms(
                        random.choice(unexplored)
                    ),
                    "preparation_tips": [
                        "Atualizar portfolio",
                        "Praticar para casting",
                    ],
                    "estimated_success_rate": random.randint(30, 55),
                    "risk_level": "medium",
                }
            )

        return {
            "suggestions": suggestions,
            "based_on_history": len(history) > 0,
            "profile_strengths": self._profile_strengths(profile),
        }

    # ========== HELPERS ==========

    def _fetch_from_source(
        self, source: Dict, profile: Dict, filters: Dict, location: str
    ) -> List[Dict]:
        """Simula busca em uma fonte de oportunidades."""
        opportunities = []
        count = random.randint(2, 8)

        for i in range(count):
            opp_type = random.choice(self.OPPORTUNITY_TYPES)
            opp = {
                "id": f"{source['name']}_{random.randint(10000, 99999)}",
                "title": self._generate_opportunity_title(opp_type),
                "type": opp_type,
                "source": source["name"],
                "source_reliability": source["reliability"],
                "location": location,
                "date": (
                    datetime.utcnow() + timedelta(days=random.randint(7, 60))
                ).isoformat(),
                "deadline": (
                    datetime.utcnow() + timedelta(days=random.randint(3, 30))
                ).isoformat(),
                "requirements": self.REQUIREMENTS_BY_TYPE.get(opp_type, []),
                "compensation": self._generate_compensation(opp_type),
                "relevance_score": random.randint(40, 95),
                "status": "open",
                "posted_at": (
                    datetime.utcnow() - timedelta(days=random.randint(0, 7))
                ).isoformat(),
            }
            opportunities.append(opp)

        return opportunities

    def _generate_opportunity_title(self, opp_type: str) -> str:
        titles = {
            "casting": [
                "Casting para Campanha de Moda",
                "Casting para Comercial de TV",
                "Casting para Editorial de Revista",
            ],
            "editorial": [
                "Editorial de Moda Primavera",
                "Editorial de Beleza",
                "Editorial Conceitual para Revista",
            ],
            "commercial": [
                "Comercial para Marca de Cosmeticos",
                "Campanha Publicitaria",
                "Spot para Redes Sociais",
            ],
            "runway": ["Desfile de Moda", "Fashion Week", "Showroom de Lançamento"],
            "film": ["Curta-Metragem", "Webserie", "Filme Independente"],
            "digital_content": [
                "Campanha de Influencers",
                "Conteudo para Marca",
                "Colaboracao Digital",
            ],
        }
        return random.choice(titles.get(opp_type, ["Oportunidade de Trabalho"]))

    def _generate_compensation(self, opp_type: str) -> Dict:
        ranges = {
            "casting": (500, 2000),
            "editorial": (800, 5000),
            "commercial": (2000, 15000),
            "runway": (1000, 8000),
            "tv_commercial": (3000, 20000),
            "film": (1000, 10000),
            "digital_content": (500, 5000),
            "brand_collaboration": (1000, 10000),
        }
        min_val, max_val = ranges.get(opp_type, (500, 3000))
        return {
            "min": min_val,
            "max": max_val,
            "currency": "BRL",
            "type": random.choice(["fixed", "per_day", "per_hour"]),
        }

    def _apply_filters(self, opportunities: List[Dict], filters: Dict) -> List[Dict]:
        """Aplica filtros as oportunidades."""
        filtered = opportunities

        if filters.get("type"):
            filtered = [o for o in filtered if o["type"] == filters["type"]]
        if filters.get("min_compensation"):
            filtered = [
                o
                for o in filtered
                if o["compensation"]["min"] >= filters["min_compensation"]
            ]
        if filters.get("location"):
            filtered = [
                o
                for o in filtered
                if filters["location"].lower() in o["location"].lower()
            ]
        if filters.get("min_relevance"):
            filtered = [
                o for o in filtered if o["relevance_score"] >= filters["min_relevance"]
            ]

        return filtered

    def _calculate_match_score(
        self, profile: Dict, opportunity: Dict
    ) -> Dict[str, Any]:
        """Calcula score detalhado de matching."""
        breakdown = {}
        strengths = []
        weaknesses = []

        # Matching por altura (para modelos)
        if "height" in opportunity.get("requirements", []):
            profile_height = profile.get("height_cm", 0)
            if 170 <= profile_height <= 185:
                breakdown["height"] = 95
                strengths.append("Altura dentro do range ideal")
            elif 165 <= profile_height <= 190:
                breakdown["height"] = 75
            else:
                breakdown["height"] = 40
                weaknesses.append("Altura fora do range comum")

        # Matching por experiencia
        if "experience" in opportunity.get("requirements", []):
            years = profile.get("experience_years", 0)
            if years >= 5:
                breakdown["experience"] = 90
                strengths.append("Experiencia solida")
            elif years >= 2:
                breakdown["experience"] = 70
            else:
                breakdown["experience"] = 50
                weaknesses.append("Pouca experiencia documentada")

        # Matching por portfolio
        if "portfolio" in opportunity.get("requirements", []):
            portfolio_count = len(profile.get("portfolio_photos", []))
            if portfolio_count >= 15:
                breakdown["portfolio"] = 90
                strengths.append("Portfolio completo")
            elif portfolio_count >= 8:
                breakdown["portfolio"] = 70
            else:
                breakdown["portfolio"] = 45
                weaknesses.append("Portfolio incompleto")

        # Matching por tipo de oportunidade vs perfil
        opp_type = opportunity.get("type", "")
        profile_types = profile.get("specialties", [])
        if opp_type in profile_types:
            breakdown["specialty_match"] = 95
            strengths.append(f"Especialidade direta em {opp_type}")
        elif any(t in opp_type for t in profile_types):
            breakdown["specialty_match"] = 70
        else:
            breakdown["specialty_match"] = 50
            weaknesses.append("Tipo de oportunidade fora da especialidade principal")

        # Score geral
        if breakdown:
            overall = sum(breakdown.values()) / len(breakdown)
        else:
            overall = 60

        return {
            "overall": round(overall),
            "breakdown": breakdown,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendation": self._match_recommendation_from_score(overall),
            "confidence": "high" if len(breakdown) >= 3 else "medium",
        }

    def _match_recommendation(self, match: Dict) -> str:
        score = match["match_score"]["overall"]
        if score >= 85:
            return "Match excelente! Aplicar imediatamente."
        elif score >= 70:
            return "Bom match. Aplicar com portfolio atualizado."
        elif score >= 55:
            return "Match razoavel. Considerar se houver tempo."
        return "Match fraco. Focar em outras oportunidades."

    def _match_recommendation_from_score(self, score: float) -> str:
        if score >= 85:
            return "Match excelente"
        elif score >= 70:
            return "Bom match"
        elif score >= 55:
            return "Match razoavel"
        return "Match fraco"

    def _generate_new_opportunities(self, profile: Dict, criteria: Dict) -> List[Dict]:
        """Gera novas oportunidades simuladas."""
        opportunities = []
        count = random.randint(3, 10)

        for i in range(count):
            opp_type = random.choice(self.OPPORTUNITY_TYPES)
            opportunities.append(
                {
                    "id": f"new_{random.randint(10000, 99999)}",
                    "title": self._generate_opportunity_title(opp_type),
                    "type": opp_type,
                    "source": random.choice([s["name"] for s in self.SOURCES]),
                    "posted_date": datetime.utcnow().isoformat(),
                    "deadline": (
                        datetime.utcnow() + timedelta(days=random.randint(3, 21))
                    ).isoformat(),
                    "relevance_score": random.randint(50, 98),
                    "is_new": True,
                }
            )

        return opportunities

    def _profile_summary(self, profile: Dict) -> Dict:
        return {
            "name": profile.get("name", "N/A"),
            "specialties": profile.get("specialties", []),
            "experience_years": profile.get("experience_years", 0),
            "location": profile.get("location", "N/A"),
            "portfolio_size": len(profile.get("portfolio_photos", [])),
        }

    def _status_note(self, status: str) -> str:
        notes = {
            "approved": "Parabens! Voce foi selecionado para esta oportunidade.",
            "rejected": "Nao foi desta vez. Continue aplicando!",
            "shortlisted": "Voce esta na lista restrita. Aguarde contato.",
        }
        return notes.get(status, "Status atualizado.")

    def _next_steps(self, status: str) -> List[str]:
        steps = {
            "submitted": [
                "Aguardar resposta do casting",
                "Preparar material caso seja chamado",
            ],
            "under_review": [
                "Manter portfolio atualizado",
                "Verificar email regularmente",
            ],
            "shortlisted": ["Preparar para callback", "Revisar contrato e termos"],
            "approved": [
                "Confirmar disponibilidade",
                "Preparar documentacao",
                "Assinar contrato",
            ],
            "rejected": [
                "Solicitar feedback",
                "Atualizar portfolio",
                "Aplicar em novas oportunidades",
            ],
        }
        return steps.get(status, ["Acompanhar status regularmente"])

    def _estimated_response(self, status: str) -> str:
        if status in ["approved", "rejected"]:
            return "Finalizado"
        return f"{random.randint(3, 14)} dias"

    def _history_recommendations(self, success_rate: float, by_type: Dict) -> List[str]:
        recs = []
        if success_rate < 20:
            recs.append(
                "Taxa de sucesso baixa. Considerar workshop de preparacao para casting."
            )
            recs.append("Revisar portfolio com fotografo profissional.")
        elif success_rate < 40:
            recs.append("Boa taxa de sucesso. Focar nos tipos com melhor performance.")
        else:
            recs.append("Excelente taxa de sucesso! Aumentar volume de aplicacoes.")

        # Recomendar tipos com melhor performance
        if by_type:
            best = max(
                by_type.items(), key=lambda x: x[1]["approved"] / max(x[1]["total"], 1)
            )
            recs.append(
                f"Focar em oportunidades do tipo '{best[0]}' - seu melhor desempenho."
            )

        return recs

    def _best_types_from_history(self, history: List[Dict]) -> List[str]:
        if not history:
            return random.sample(self.OPPORTUNITY_TYPES, 3)

        type_scores = {}
        for app in history:
            opp_type = app.get("opportunity_type", "unknown")
            if opp_type not in type_scores:
                type_scores[opp_type] = {"total": 0, "approved": 0}
            type_scores[opp_type]["total"] += 1
            if app.get("status") == "approved":
                type_scores[opp_type]["approved"] += 1

        sorted_types = sorted(
            type_scores.items(),
            key=lambda x: x[1]["approved"] / max(x[1]["total"], 1),
            reverse=True,
        )
        return [t[0] for t in sorted_types]

    def _suggested_platforms(self, opp_type: str) -> List[str]:
        platforms = {
            "casting": ["Casting Networks", "Backstage", "Site da agencia"],
            "editorial": ["Instagram", "Model Mayhem", "Direct contact"],
            "commercial": ["Casting Networks", "Agente", "Indicacoes"],
            "digital_content": ["Instagram", "TikTok", "YouTube"],
        }
        return platforms.get(opp_type, ["Multiplas plataformas"])

    def _preparation_tips(self, opp_type: str) -> List[str]:
        tips = {
            "casting": [
                "Preparar 2 looks diferentes",
                "Levar composite atualizado",
                "Chegar 15min antes",
            ],
            "editorial": [
                "Cuidados com a pele",
                "Manicure/feet done",
                "Levar lingerie nude",
            ],
            "commercial": [
                "Sorriso natural",
                "Postura amigavel",
                "Praticar pitch pessoal",
            ],
            "runway": ["Praticar walk", "Levar sapatos de salto", "Postura ereta"],
        }
        return tips.get(opp_type, ["Atualizar portfolio", "Pesquisar a marca/cliente"])

    def _profile_strengths(self, profile: Dict) -> List[str]:
        strengths = []
        if profile.get("experience_years", 0) >= 3:
            strengths.append("Experiencia consolidada")
        if len(profile.get("portfolio_photos", [])) >= 10:
            strengths.append("Portfolio robusto")
        if profile.get("languages"):
            strengths.append(f"Multilingue: {', '.join(profile['languages'])}")
        if profile.get("social_media_followers", 0) > 10000:
            strengths.append("Boa presenca digital")
        return strengths if strengths else ["Perfil em desenvolvimento"]
