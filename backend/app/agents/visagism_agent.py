"""VisagismAgent - Análise de visagismo e recomendações de estilo."""
import logging
import os
from typing import Dict, List, Optional

from app.agents.base import AgentCapability, AgentContext, AgentResult, VisionAgent
from app.ai.image_triage.engine import ImageTriageEngine, TriageCategory
from app.ai.visagism.analyzer import VisagismAnalyzer
from app.ai.visagism.card_photo_guard import (
    CardPhotoGuardError,
    DEFAULT_CARD_PHOTO_GUARD,
)

logger = logging.getLogger(__name__)


class VisagismAgent(VisionAgent):
    def __init__(self):
        super().__init__(
            name="VisagismAgent",
            description="Análise de visagismo e recomendações de estilo",
            capabilities=[
                AgentCapability.VISAGISM_ANALYSIS,
                AgentCapability.STYLE_RECOMMENDATION,
            ],
        )
        self.analyzer = VisagismAnalyzer()
        self.triage_engine = ImageTriageEngine()

    def can_handle(self, context: AgentContext) -> bool:
        return context.intent in ["ANALYZE_VISAGISM", "STYLE_RECOMMENDATION", "TRIAGE_AND_ANALYZE"]

    async def execute(self, context: AgentContext) -> AgentResult:
        self._increment_execution()

        try:
            photos = context.input_data.get("photos", [])
            if not photos:
                return AgentResult(
                    success=False,
                    data={"error": "No photos provided"},
                    message="Nenhuma foto fornecida para análise",
                )

            # Fail closed before analysis/card generation: every successful
            # visagism result must have a proven real source photo.
            try:
                card_media = DEFAULT_CARD_PHOTO_GUARD.build_card_media(photos=photos)
            except CardPhotoGuardError as exc:
                return AgentResult(
                    success=False,
                    data={
                        "error": str(exc),
                        "card_media": None,
                        "placeholders": ["real_person_photo_required"],
                    },
                    message="É obrigatória uma foto real da pessoa para gerar o card",
                )

            # Triagem primeiro
            triage_results = []
            for photo in photos:
                path = photo.get("path") or photo.get("url")
                if path and os.path.exists(path):
                    result = self.triage_engine.process_image(path)
                    triage_results.append(
                        {
                            "filename": result.filename,
                            "category": result.category.value,
                            "confidence": result.confidence,
                            "selected": result.selected,
                        }
                    )

            # Análise de visagismo
            analysis = await self.analyzer.analyze(photos)

            data = {
                "analysis": analysis,
                "confidence": analysis.get("confidence", 0.5),
                "recommendations": {
                    "hairstyles": analysis.get("recommended_hairstyles", []),
                    "eyebrows": analysis.get("recommended_eyebrow_shapes", []),
                    "makeup": analysis.get("recommended_makeup_styles", []),
                },
                # Mandatory card-media contract. Consumers must render
                # personPhoto even if a validated simulation is later attached.
                "card_media": card_media,
                "source_photos": card_media["realPhotoRefs"],
                "limitations": [],
                "evidence_map": {
                    "face_shape": analysis.get("face_shape_category"),
                    "confidence": analysis.get("confidence"),
                },
                "placeholders": [],
            }

            if analysis.get("confidence", 1.0) < 0.7:
                data["placeholders"].append("low_confidence_analysis")
            if "error" in analysis:
                data["placeholders"].append("analysis_error")
                data["limitations"].append(f"Erro: {analysis['error']}")

            return AgentResult(
                success=True,
                data=data,
                message="Análise de visagismo concluída",
            )

        except Exception as e:
            logger.exception("Erro no VisagismAgent")
            return AgentResult(
                success=False,
                data={"error": str(e), "placeholders": ["execution_error"]},
                message=f"Erro: {str(e)}",
            )

    def validate(self, result: AgentResult) -> bool:
        if not result.success:
            return False
        data = result.data
        if not isinstance(data, dict):
            return False
        card_media = data.get("card_media")
        if not isinstance(card_media, dict):
            return False
        if not card_media.get("realPhotoVerified"):
            return False
        if not card_media.get("personPhoto"):
            return False
        return "analysis" in data or "placeholders" in data
