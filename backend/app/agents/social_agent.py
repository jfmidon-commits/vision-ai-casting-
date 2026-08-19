"""
SocialAgent - Criacao e gestao de conteudo social inteligente.

Responsabilidades:
- Criar conteudo otimizado para redes sociais (Instagram, TikTok, LinkedIn)
- Analisar performance de conteudo existente
- Sugerir horarios ideais de postagem
- Gerar legendas, hashtags e copy
- Analisar engajamento e tendencias
"""

import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.agents.base import VisionAgent, AgentContext, AgentResult, AgentCapability


class SocialAgent(VisionAgent):
    """Agente especializado em criacao e gestao de conteudo social."""

    # Templates de conteudo por plataforma
    CONTENT_TEMPLATES = {
        "instagram": {
            "formats": ["carousel", "reels", "story", "single"],
            "optimal_times": ["11:00", "14:00", "19:00", "21:00"],
            "hashtag_count": (15, 30),
            "caption_length": (100, 2200),
        },
        "tiktok": {
            "formats": ["video", "duet", "stitch"],
            "optimal_times": ["09:00", "12:00", "19:00", "22:00"],
            "hashtag_count": (3, 5),
            "caption_length": (50, 300),
        },
        "linkedin": {
            "formats": ["article", "post", "document", "poll"],
            "optimal_times": ["08:00", "12:00", "17:00"],
            "hashtag_count": (3, 10),
            "caption_length": (200, 3000),
        },
    }

    # Banco de hashtags por nicho
    HASHTAG_BANK = {
        "modeling": [
            "#modelo",
            "#fashion",
            "#moda",
            "#editorial",
            "#runway",
            "#modeling",
            "#fashionmodel",
            "#portrait",
            "#style",
            "#beauty",
        ],
        "acting": [
            "#ator",
            "#atriz",
            "#cinema",
            "#teatro",
            "#casting",
            "#actress",
            "#actor",
            "#film",
            "#movie",
            "#performance",
        ],
        "influencer": [
            "#influencer",
            "#lifestyle",
            "#contentcreator",
            "#digital",
            "#creator",
            "#influenciador",
            "#brand",
            "#collab",
        ],
        "fitness": [
            "#fitness",
            "#saude",
            "#workout",
            "#gym",
            "#fit",
            "#health",
            "#training",
            "#wellness",
            "#active",
        ],
        "beauty": [
            "#beleza",
            "#makeup",
            "#maquiagem",
            "#skincare",
            "#beauty",
            "#glam",
            "#cosmetics",
            "#selfcare",
            "#glowup",
        ],
    }

    # Templates de legenda
    CAPTION_TEMPLATES = {
        "behind_the_scenes": [
            "Nos bastidores de {project}! {emoji} Cada detalhe conta quando voce ama o que faz. {cta}",
            "O que ninguem ve... {emoji} Gratidao por cada oportunidade de criar. {cta}",
        ],
        "portfolio": [
            "Novo trabalho com {team}! {emoji} Honrado em fazer parte deste projeto. {cta}",
            "Lancamento oficial! {emoji} {project} esta no ar. O que acharam? {cta}",
        ],
        "lifestyle": [
            "Dia de {activity} por aqui! {emoji} E voce, como esta cuidando de si hoje? {cta}",
            "{quote} {emoji} Lembrete diario: voce e mais capaz do que imagina. {cta}",
        ],
        "engagement": [
            "Conta pra mim: {question} {emoji} Quero saber a opiniao de voces! {cta}",
            "Qual dessas {options} voce prefere? {emoji} Comenta aqui! {cta}",
        ],
    }

    def __init__(self):
        super().__init__(
            name="SocialAgent",
            description="Criacao e gestao de conteudo social inteligente",
            capabilities=[
                AgentCapability.CONTENT_CREATION,
                AgentCapability.CONTENT_SCHEDULING,
                AgentCapability.SOCIAL_PUBLISHING,
            ],
        )

    def can_handle(self, context: AgentContext) -> bool:
        return context.intent in [
            "CREATE_CONTENT",
            "SCHEDULE_CONTENT",
            "PUBLISH_CONTENT",
            "ANALYZE_PERFORMANCE",
            "SUGGEST_HASHTAGS",
            "GENERATE_CAPTION",
            "OPTIMAL_POSTING_TIMES",
        ]

    async def execute(self, context: AgentContext) -> AgentResult:
        self._increment_execution()

        intent = context.intent
        input_data = context.input_data

        try:
            if intent == "CREATE_CONTENT":
                result = await self._create_content(input_data)
            elif intent == "SCHEDULE_CONTENT":
                result = await self._schedule_content(input_data)
            elif intent == "PUBLISH_CONTENT":
                result = await self._publish_content(input_data)
            elif intent == "ANALYZE_PERFORMANCE":
                result = await self._analyze_performance(input_data)
            elif intent == "SUGGEST_HASHTAGS":
                result = await self._suggest_hashtags(input_data)
            elif intent == "GENERATE_CAPTION":
                result = await self._generate_caption(input_data)
            elif intent == "OPTIMAL_POSTING_TIMES":
                result = await self._optimal_posting_times(input_data)
            else:
                return AgentResult(
                    success=False,
                    error=f"Intencao '{intent}' nao suportada pelo SocialAgent",
                )

            return AgentResult(
                success=True,
                data=result,
                message=f"SocialAgent executou '{intent}' com sucesso",
            )

        except Exception as e:
            self._increment_error()
            return AgentResult(
                success=False,
                error=f"Erro no SocialAgent: {str(e)}",
            )

    def validate(self, result: AgentResult) -> bool:
        if not result.success:
            return False
        data = result.data or {}
        # Validar estrutura minima
        if "content" in data and not data["content"]:
            return False
        return True

    # ========== IMPLEMENTACOES ==========

    async def _create_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Cria um plano de conteudo completo."""
        platform = data.get("platform", "instagram")
        content_type = data.get("content_type", "portfolio")
        niche = data.get("niche", "modeling")
        project_name = data.get("project_name", "novo projeto")
        team = data.get("team", "time incrível")

        template_info = self.CONTENT_TEMPLATES.get(
            platform, self.CONTENT_TEMPLATES["instagram"]
        )

        # Gerar legenda
        caption = self._generate_caption_text(content_type, project_name, team)

        # Gerar hashtags
        hashtags = self._generate_hashtags(niche, platform)

        # Sugerir horario
        optimal_time = random.choice(template_info["optimal_times"])

        # Sugerir formato
        suggested_format = random.choice(template_info["formats"])

        return {
            "platform": platform,
            "content_type": content_type,
            "caption": caption,
            "hashtags": hashtags,
            "hashtag_count": len(hashtags),
            "suggested_format": suggested_format,
            "optimal_posting_time": optimal_time,
            "estimated_reach": self._estimate_reach(platform, niche),
            "content_ideas": self._generate_content_ideas(niche, platform),
            "created_at": datetime.utcnow().isoformat(),
        }

    async def _schedule_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Agenda conteudo para publicacao."""
        contents = data.get("contents", [])
        timezone = data.get("timezone", "America/Sao_Paulo")

        schedule = []
        base_date = datetime.utcnow()

        for i, content in enumerate(contents):
            # Espacar posts a cada 6-12 horas
            hours_offset = i * random.randint(6, 12)
            post_time = base_date + timedelta(hours=hours_offset)

            schedule.append(
                {
                    "content_id": f"content_{i+1}",
                    "platform": content.get("platform", "instagram"),
                    "scheduled_at": post_time.isoformat(),
                    "status": "scheduled",
                    "timezone": timezone,
                }
            )

        return {
            "schedule": schedule,
            "total_scheduled": len(schedule),
            "timezone": timezone,
            "first_post": schedule[0]["scheduled_at"] if schedule else None,
        }

    async def _publish_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Simula publicacao de conteudo (integracao real com APIs sociais)."""
        content = data.get("content", {})
        platforms = data.get("platforms", ["instagram"])

        published = []
        for platform in platforms:
            published.append(
                {
                    "platform": platform,
                    "status": "published",
                    "published_at": datetime.utcnow().isoformat(),
                    "post_id": f"{platform}_{random.randint(10000, 99999)}",
                    "url": f"https://{platform}.com/p/{random.randint(100000, 999999)}",
                }
            )

        return {
            "published_posts": published,
            "total_published": len(published),
            "cross_platform": len(platforms) > 1,
        }

    async def _analyze_performance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analisa performance de conteudo existente."""
        posts = data.get("posts", [])

        if not posts:
            return {
                "message": "Nenhum post fornecido para analise",
                "overall_score": 0,
            }

        total_engagement = 0
        total_reach = 0
        best_post = None
        best_score = 0

        analyzed_posts = []
        for post in posts:
            likes = post.get("likes", 0)
            comments = post.get("comments", 0)
            shares = post.get("shares", 0)
            saves = post.get("saves", 0)
            reach = post.get("reach", 1)

            engagement_rate = (
                (likes + comments * 2 + shares * 3 + saves * 2) / max(reach, 1)
            ) * 100
            total_engagement += engagement_rate
            total_reach += reach

            score = engagement_rate
            if score > best_score:
                best_score = score
                best_post = post

            analyzed_posts.append(
                {
                    "post_id": post.get("id"),
                    "platform": post.get("platform"),
                    "engagement_rate": round(engagement_rate, 2),
                    "likes": likes,
                    "comments": comments,
                    "shares": shares,
                    "saves": saves,
                    "reach": reach,
                    "performance": self._rate_performance(engagement_rate),
                }
            )

        avg_engagement = total_engagement / len(posts) if posts else 0

        return {
            "analyzed_posts": analyzed_posts,
            "total_posts": len(posts),
            "average_engagement_rate": round(avg_engagement, 2),
            "total_reach": total_reach,
            "best_performing_post": best_post.get("id") if best_post else None,
            "best_engagement_rate": round(best_score, 2),
            "overall_performance": self._rate_performance(avg_engagement),
            "recommendations": self._performance_recommendations(avg_engagement),
        }

    async def _suggest_hashtags(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sugere hashtags otimizadas para o nicho."""
        niche = data.get("niche", "modeling")
        platform = data.get("platform", "instagram")
        count = data.get("count", 20)

        base_hashtags = self.HASHTAG_BANK.get(niche, self.HASHTAG_BANK["modeling"])

        # Adicionar hashtags genericas de engajamento
        generic = ["#instagood", "#photooftheday", "#love", "#beautiful", "#art"]

        # Adicionar hashtags de nicho relacionados
        related_niches = random.sample(
            list(self.HASHTAG_BANK.keys()), min(2, len(self.HASHTAG_BANK))
        )
        related_hashtags = []
        for rn in related_niches:
            if rn != niche:
                related_hashtags.extend(
                    random.sample(
                        self.HASHTAG_BANK[rn], min(3, len(self.HASHTAG_BANK[rn]))
                    )
                )

        all_hashtags = list(set(base_hashtags + generic + related_hashtags))
        random.shuffle(all_hashtags)

        # Limitar ao count solicitado
        suggested = all_hashtags[:count]

        # Categorizar
        categorized = {
            "niche": [
                h for h in suggested if any(n in h.lower() for n in [niche, niche[:4]])
            ],
            "generic": [h for h in suggested if h in generic],
            "related": [
                h
                for h in suggested
                if h not in categorized.get("niche", []) and h not in generic
            ],
        }

        return {
            "hashtags": suggested,
            "count": len(suggested),
            "categorized": categorized,
            "niche": niche,
            "platform": platform,
            "estimated_reach_boost": f"{random.randint(15, 45)}%",
        }

    async def _generate_caption(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Gera uma legenda personalizada."""
        content_type = data.get("content_type", "portfolio")
        tone = data.get("tone", "professional")
        language = data.get("language", "pt")
        project_name = data.get("project_name", "")
        team = data.get("team", "")

        caption = self._generate_caption_text(content_type, project_name, team, tone)

        # Adicionar CTA baseado no tom
        ctas = {
            "professional": [
                "Comenta o que achou!",
                "Compartilhe com quem precisa ver.",
                "O que voce faria diferente?",
            ],
            "casual": [
                "Me conta nos comentarios!",
                "Marca alguem que precisa ver isso.",
                "Curte ai se voce concorda!",
            ],
            "inspirational": [
                "Qual e o seu proximo passo?",
                "Compartilhe sua historia nos comentarios.",
                "Acredite em voce!",
            ],
        }

        cta = random.choice(ctas.get(tone, ctas["professional"]))

        return {
            "caption": f"{caption}\n\n{cta}",
            "tone": tone,
            "language": language,
            "content_type": content_type,
            "character_count": len(caption),
            "has_cta": True,
        }

    async def _optimal_posting_times(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna horarios otimos de postagem por plataforma."""
        platforms = data.get("platforms", ["instagram", "tiktok", "linkedin"])
        audience_timezone = data.get("audience_timezone", "America/Sao_Paulo")

        results = {}
        for platform in platforms:
            template = self.CONTENT_TEMPLATES.get(
                platform, self.CONTENT_TEMPLATES["instagram"]
            )
            results[platform] = {
                "optimal_times": template["optimal_times"],
                "best_days": ["Terca", "Quarta", "Quinta", "Sexta"],
                "worst_days": ["Domingo"],
                "peak_engagement_window": f"{template['optimal_times'][1]} - {template['optimal_times'][2]}",
                "timezone": audience_timezone,
            }

        return {
            "platforms": results,
            "general_recommendation": "Postar entre 11h e 21h para maior alcance",
            "audience_timezone": audience_timezone,
        }

    # ========== HELPERS ==========

    def _generate_caption_text(
        self,
        content_type: str,
        project_name: str,
        team: str,
        tone: str = "professional",
    ) -> str:
        """Gera texto de legenda usando templates."""
        templates = self.CAPTION_TEMPLATES.get(
            content_type, self.CAPTION_TEMPLATES["portfolio"]
        )
        template = random.choice(templates)

        emojis = ["✨", "🎬", "📸", "💫", "🔥", "🌟", "💎", "🎯", "🚀", "❤️"]
        quotes = [
            "O sucesso e a soma de pequenos esforcos repetidos diariamente.",
            "Crie oportunidades, nao espere por elas.",
            "A consistencia e a chave para a excelencia.",
            "Seja a mudanca que voce quer ver no mundo.",
        ]
        activities = ["ensaios", "reunioes", "estudos", "treinos", "leitura"]
        questions = [
            "qual foi seu maior aprendizado esse ano?",
            "o que te motiva a seguir em frente?",
            "qual seu sonho mais audacioso?",
            "o que voce esta construindo hoje?",
        ]

        caption = template.format(
            project=project_name,
            team=team,
            emoji=random.choice(emojis),
            cta="",
            quote=random.choice(quotes),
            activity=random.choice(activities),
            question=random.choice(questions),
            options="opcoes",
        )

        return caption.strip()

    def _generate_hashtags(self, niche: str, platform: str) -> List[str]:
        """Gera lista de hashtags."""
        template = self.CONTENT_TEMPLATES.get(
            platform, self.CONTENT_TEMPLATES["instagram"]
        )
        min_tags, max_tags = template["hashtag_count"]

        base = self.HASHTAG_BANK.get(niche, self.HASHTAG_BANK["modeling"])
        generic = ["#instagood", "#photooftheday", "#love"]

        all_tags = list(set(base + generic))
        random.shuffle(all_tags)

        return all_tags[: random.randint(min_tags, max_tags)]

    def _estimate_reach(self, platform: str, niche: str) -> Dict[str, Any]:
        """Estima alcance do conteudo."""
        base_reach = {
            "instagram": random.randint(500, 5000),
            "tiktok": random.randint(1000, 10000),
            "linkedin": random.randint(200, 2000),
        }

        reach = base_reach.get(platform, 1000)
        niche_multiplier = {
            "modeling": 1.2,
            "acting": 1.1,
            "influencer": 1.5,
            "fitness": 1.3,
            "beauty": 1.4,
        }
        reach = int(reach * niche_multiplier.get(niche, 1.0))

        return {
            "estimated_reach": reach,
            "estimated_impressions": int(reach * random.uniform(1.5, 3.0)),
            "estimated_engagement": int(reach * random.uniform(0.03, 0.12)),
            "confidence": random.choice(["high", "medium", "medium"]),
        }

    def _generate_content_ideas(
        self, niche: str, platform: str
    ) -> List[Dict[str, Any]]:
        """Gera ideias de conteudo."""
        ideas = [
            {
                "type": "behind_the_scenes",
                "title": "Bastidores do trabalho",
                "difficulty": "easy",
            },
            {
                "type": "tutorial",
                "title": f"Como me preparo para {niche}",
                "difficulty": "medium",
            },
            {"type": "q_and_a", "title": "Perguntas e respostas", "difficulty": "easy"},
            {
                "type": "transformation",
                "title": "Antes e depois",
                "difficulty": "medium",
            },
            {
                "type": "day_in_life",
                "title": "Um dia na minha vida",
                "difficulty": "easy",
            },
            {
                "type": "tips",
                "title": f"5 dicas para quem quer trabalhar com {niche}",
                "difficulty": "easy",
            },
        ]

        return random.sample(ideas, min(3, len(ideas)))

    def _rate_performance(self, engagement_rate: float) -> str:
        """Classifica performance baseada no engagement rate."""
        if engagement_rate >= 5.0:
            return "excellent"
        elif engagement_rate >= 3.0:
            return "very_good"
        elif engagement_rate >= 1.5:
            return "good"
        elif engagement_rate >= 0.5:
            return "average"
        return "below_average"

    def _performance_recommendations(self, avg_engagement: float) -> List[str]:
        """Gera recomendacoes baseadas na performance."""
        recs = []
        if avg_engagement < 1.0:
            recs.append("Aumentar frequencia de posts para 1x ao dia")
            recs.append("Usar mais Reels/Video - algoritmo favorece video")
            recs.append("Interagir mais nos comentarios nas primeiras 30 min")
        elif avg_engagement < 3.0:
            recs.append("Testar horarios diferentes de postagem")
            recs.append("Aumentar uso de stories para engajamento")
            recs.append("Colaborar com outros criadores do nicho")
        else:
            recs.append("Manter consistencia atual - performance boa")
            recs.append("Explorar parcerias pagas com marcas")
            recs.append("Criar serie de conteudo para fidelizar audiencia")
        return recs
