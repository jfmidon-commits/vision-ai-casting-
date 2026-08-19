"""
backend/app/agents/visagism_agent.py

VisagismAgent — implementacao real (v2.1.0).

Orquestra o pipeline de visagismo e entrega tanto o JSON canonico tecnico
quanto uma camada de apresentacao pronta para usuario/barbeiro.
"""

import logging
from typing import Any, Dict, List, Optional

from app.agents.base import AgentCapability, AgentContext, AgentResult, VisionAgent
from app.ai.visagism.compatible_rule_engine import CompatibleVisagismRuleEngine
from app.ai.visagism.pipeline import VisagismPipeline
from app.ai.visagism.recommendation_presenter import (
    present_recommendation,
    present_recommendations,
)
from app.ai.visagism.schemas import (
    PhotoAngle,
    PhotoInput,
    ProfileContext,
    VisagismAnalysisInput,
)
from app.core.event_bus import EventBus

logger = logging.getLogger(__name__)


class VisagismAgent(VisionAgent):
    """Agente real de visagismo capilar."""

    SUPPORTED_INTENTS = [
        "ANALYZE_VISAGISM",
        "STYLE_RECOMMENDATION",
        "HAIR_ANALYSIS",
    ]

    def __init__(self):
        super().__init__(
            name="VisagismAgent",
            description=(
                "Agente de analise de visagismo capilar com pipeline hibrido "
                "proprietario"
            ),
            capabilities=[
                AgentCapability.VISAGISM_ANALYSIS,
                AgentCapability.STYLE_RECOMMENDATION,
            ],
        )
        self.pipeline = VisagismPipeline()
        self.pipeline.rule_engine = CompatibleVisagismRuleEngine()
        self.event_bus = EventBus()

    def can_handle(self, context: AgentContext) -> bool:
        return context.intent in self.SUPPORTED_INTENTS

    def _validate_input(self, context: AgentContext) -> tuple[bool, Optional[str]]:
        input_data = context.input_data
        photos = input_data.get("photos", [])
        if not photos:
            return False, "Nenhuma foto fornecida para analise de visagismo"

        usable = [p for p in photos if p.get("is_usable", True)]
        if not usable:
            return False, "Nenhuma foto usavel para analise de visagismo"

        if not input_data.get("profile"):
            logger.warning("Analise de visagismo sem contexto de perfil — usando defaults")

        return True, None

    def validate(self, result: AgentResult) -> bool:
        if not result.success:
            return False

        data = result.data or {}
        visagism_result = data.get("visagism_result", {})
        if not visagism_result.get("face_shape_category"):
            return False

        if not visagism_result.get("primary_recommendation"):
            if not visagism_result.get("analysis_limitations"):
                return False

        if not (0.0 <= result.confidence <= 1.0):
            return False

        return True

    async def execute(self, context: AgentContext) -> AgentResult:
        logger.info("VisagismAgent executando intent: %s", context.intent)
        self._increment_execution()

        is_valid, error = self._validate_input(context)
        if not is_valid:
            logger.warning("Validacao de entrada falhou: %s", error)
            self._increment_error()
            return AgentResult(
                success=False,
                data={"error": error, "intent": context.intent},
                message=error,
                error=error,
                requires_approval=False,
                confidence=0.0,
            )

        try:
            pipeline_input = self._build_pipeline_input(context)
        except Exception as exc:
            logger.error("Erro ao construir input do pipeline: %s", exc)
            self._increment_error()
            return AgentResult(
                success=False,
                data={"error": str(exc)},
                message="Erro na preparacao da analise",
                error=str(exc),
                requires_approval=False,
                confidence=0.0,
            )

        try:
            result = await self.pipeline.execute(pipeline_input)
            agent_result = self._build_agent_result(result, context)

            if not self.validate(agent_result):
                logger.warning("Resultado da analise nao passou na validacao estrutural")
                agent_result.success = False
                agent_result.error = "Resultado estruturalmente invalido"

            if context.memory:
                await self._update_memory(context, result)

            logger.info(
                "VisagismAgent concluido. Success=%s, Confidence=%.2f",
                agent_result.success,
                agent_result.confidence,
            )
            return agent_result

        except Exception as exc:
            logger.error("Erro no pipeline de visagismo: %s", exc, exc_info=True)
            self._increment_error()
            return AgentResult(
                success=False,
                data={"error": str(exc), "intent": context.intent},
                message="Erro durante a analise de visagismo",
                error=str(exc),
                requires_approval=False,
                confidence=0.0,
            )

    def _build_pipeline_input(self, context: AgentContext) -> VisagismAnalysisInput:
        input_data = context.input_data

        photos = []
        for photo_data in input_data.get("photos", []):
            angle = self._map_angle(photo_data.get("angle", "front"))
            photos.append(
                PhotoInput(
                    photo_id=photo_data.get("id"),
                    url=photo_data.get("url", ""),
                    angle=angle,
                    quality_score=photo_data.get("quality_score"),
                    is_usable=photo_data.get("is_usable", True),
                    unusable_reason=photo_data.get("unusable_reason"),
                )
            )

        profile_data = input_data.get("profile", {})
        profile = ProfileContext(
            profile_id=profile_data.get("id"),
            gender=profile_data.get("gender"),
            age_estimate=profile_data.get("age_estimate"),
            current_hair_length=profile_data.get("current_hair_length"),
            current_hair_color=profile_data.get("current_hair_color"),
            current_hair_texture=profile_data.get("current_hair_texture"),
            facial_hair=profile_data.get("facial_hair"),
            style_preferences=profile_data.get("style_preferences", []),
            previous_visagism_analyses=profile_data.get(
                "previous_visagism_analyses", []
            ),
            approved_appearances=profile_data.get("approved_appearances", []),
        )

        metadata = context.metadata or {}
        return VisagismAnalysisInput(
            photos=photos,
            profile=profile,
            analysis_types=input_data.get("analysis_types", ["hair"]),
            include_report=True,
            include_visualization_data=True,
            correlation_id=metadata.get("correlation_id"),
        )

    def _map_angle(self, angle_str: str) -> PhotoAngle:
        mapping = {
            "front": PhotoAngle.FRONT_NEUTRAL,
            "front_neutral": PhotoAngle.FRONT_NEUTRAL,
            "left_profile": PhotoAngle.PROFILE_LEFT,
            "right_profile": PhotoAngle.PROFILE_RIGHT,
            "left_45": PhotoAngle.THREE_QUARTER_LEFT,
            "right_45": PhotoAngle.THREE_QUARTER_RIGHT,
            "three_quarter_left": PhotoAngle.THREE_QUARTER_LEFT,
            "three_quarter_right": PhotoAngle.THREE_QUARTER_RIGHT,
            "smiling": PhotoAngle.FRONT_SMILING,
            "front_smiling": PhotoAngle.FRONT_SMILING,
            "neutral": PhotoAngle.FRONT_NEUTRAL,
            "hairline": PhotoAngle.HAIRLINE,
            "posterior": PhotoAngle.POSTERIOR,
            "half_body": PhotoAngle.HALF_BODY,
        }
        return mapping.get(angle_str, PhotoAngle.FRONT_NEUTRAL)

    def _build_agent_result(self, result: Any, context: AgentContext) -> AgentResult:
        requires_approval = result.overall_confidence < 0.6

        primary_user = None
        alternatives_user: List[Dict[str, Any]] = []
        if result.primary_recommendation:
            primary_user = present_recommendation(result.primary_recommendation)
            alternatives_user = present_recommendations(
                result.alternative_recommendations
            )
            message = (
                "Analise de visagismo concluida. "
                f"Recomendacao principal: {primary_user['display_name']} "
                f"(confianca: {result.overall_confidence:.0%})"
            )
        else:
            message = (
                "Analise de visagismo concluida com limitacoes. "
                f"Confianca: {result.overall_confidence:.0%}"
            )

        user_facing = {
            "face_shape": getattr(
                result.face_shape_category,
                "value",
                result.face_shape_category,
            ),
            "face_shape_confidence": result.face_shape_confidence,
            "overall_confidence": result.overall_confidence,
            "primary_recommendation": primary_user,
            "alternative_recommendations": alternatives_user,
            "recommendations": (
                ([primary_user] if primary_user else []) + alternatives_user
            ),
            "hair_data_complete": (
                bool(primary_user) and primary_user.get("hair_data_complete", False)
            ),
            "hair_data_note": (
                primary_user.get("hair_data_note") if primary_user else None
            ),
            "analysis_limitations": list(result.analysis_limitations or []),
        }

        data = {
            "visagism_result": result.model_dump(),
            "user_facing_result": user_facing,
            "human_report": result.human_report,
            "visualization_data": result.visualization_data,
            "evidence_map": result.evidence_map,
            "intent": context.intent,
        }

        return AgentResult(
            success=result.overall_confidence > 0.3,
            data=data,
            message=message,
            error=None,
            requires_approval=requires_approval,
            confidence=result.overall_confidence,
        )

    async def _update_memory(self, context: AgentContext, result: Any) -> None:
        try:
            memory = context.memory
            if result.primary_recommendation:
                await memory.add_style_preference(
                    profile_id=context.input_data.get("profile", {}).get("id"),
                    preference={
                        "type": "visagism_recommendation",
                        "primary_cut": result.primary_recommendation.name,
                        "face_shape": getattr(
                            result.face_shape_category,
                            "value",
                            result.face_shape_category,
                        ),
                        "confidence": result.overall_confidence,
                        "timestamp": __import__(
                            "datetime"
                        ).datetime.utcnow().isoformat(),
                    },
                )

            await memory.add_appearance_record(
                profile_id=context.input_data.get("profile", {}).get("id"),
                appearance={
                    "type": "visagism_analysis",
                    "analysis_id": (
                        context.metadata.get("analysis_id")
                        if context.metadata
                        else None
                    ),
                    "result_summary": (
                        result.human_report[:500] if result.human_report else ""
                    ),
                },
            )
        except Exception as exc:
            logger.warning("Erro ao atualizar memoria: %s", exc)
