"""
backend/app/ai/visagism/analyzer.py

VisagismAnalyzer — implementacao real (v2.0.0).

Substitui o analisador anterior baseado em prompt gigante para LLM.
Agora usa o pipeline hibrido proprietario:
- Medicoes determinísticas via MediaPipe (Vision Core)
- Regras de visagismo proprietarias
- LLM Vision apenas para interpretacao qualitativa

Entrada: PreprocessedPhoto + contexto
Saida: VisagismAnalysisResult (JSON canonico) + relatorio humano
"""

import logging
from typing import Dict, List, Optional, Any
from uuid import UUID

from app.ai.visagism.schemas import (
    VisagismAnalysisInput,
    VisagismAnalysisResult,
    PhotoInput,
    ProfileContext,
    PhotoAngle,
    LegacyVisagismAnalysis,
)
from app.ai.visagism.pipeline import VisagismPipeline
from app.core.event_bus import EventBus

logger = logging.getLogger(__name__)


class VisagismAnalyzer:
    """
    Analisador de visagismo capilar real.
    
    Orquestra o pipeline hibrido completo de analise facial,
    produzindo recomendacoes de corte tecnicamente justificadas.
    
    Fluxo:
    1. Converte PreprocessedPhoto + contexto -> VisagismAnalysisInput
    2. Executa VisagismPipeline
    3. Converte VisagismAnalysisResult -> formato de saida
    4. Emite eventos de progresso
    """
    
    def __init__(self):
        self.pipeline = VisagismPipeline()
        self.event_bus = EventBus()
    
    async def analyze(
        self,
        preprocessed: Any,  # PreprocessedPhoto ou lista
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Executa analise de visagismo completa.
        
        Args:
            preprocessed: Foto(s) pre-processada(s) ou lista de fotos
            context: Contexto com profile, analysis_request, etc
            
        Returns:
            Dict com 'visagism_analysis' (JSON canonico) e 'report' (texto humano)
        """
        logger.info("Iniciando analise de visagismo real (pipeline hibrido)")
        
        # Emitir evento de inicio
        await self.event_bus.emit("AI_TASK_STARTED", {
            "task": "visagism_analysis",
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        })
        
        try:
            # 1. Converter entrada para schema do pipeline
            visagism_input = self._convert_input(preprocessed, context)
            
            # 2. Executar pipeline
            result = await self.pipeline.execute(visagism_input)
            
            # 3. Converter saida
            output = self._convert_output(result)
            
            # 4. Emitir evento de sucesso
            await self.event_bus.emit("AI_TASK_COMPLETED", {
                "task": "visagism_analysis",
                "success": True,
                "confidence": result.overall_confidence,
                "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            })
            
            logger.info(
                f"Analise de visagismo concluida. "
                f"Confidence: {result.overall_confidence:.2f}, "
                f"Fotos: {result.photos_usable}/{result.photos_analyzed}"
            )
            
            return output
            
        except Exception as e:
            logger.error(f"Erro na analise de visagismo: {str(e)}", exc_info=True)
            
            # Emitir evento de falha
            await self.event_bus.emit("AI_TASK_FAILED", {
                "task": "visagism_analysis",
                "error": str(e),
                "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            })
            
            # Retornar resultado minimo com erro
            return {
                "visagism_analysis": self._create_error_result(str(e)),
                "report": f"Erro na analise: {str(e)}",
                "error": str(e),
            }
    
    def _convert_input(
        self,
        preprocessed: Any,
        context: Dict[str, Any],
    ) -> VisagismAnalysisInput:
        """Converte entrada do sistema para schema do pipeline."""
        
        # Extrair fotos
        photos = []
        
        if isinstance(preprocessed, list):
            photo_list = preprocessed
        else:
            photo_list = [preprocessed]
        
        for photo in photo_list:
            # Mapear angulo
            angle_str = getattr(photo, 'angle', 'front')
            angle = self._map_angle(angle_str)
            
            photo_input = PhotoInput(
                photo_id=getattr(photo, 'id', UUID(int=0)),
                url=getattr(photo, 'url', ''),
                angle=angle,
                quality_score=getattr(photo, 'quality_score', None),
                is_usable=getattr(photo, 'is_usable', True),
            )
            photos.append(photo_input)
        
        # Extrair contexto do perfil
        profile_data = context.get('profile', {})
        analysis_request = context.get('analysis_request', {})
        
        profile = ProfileContext(
            profile_id=profile_data.get('id', UUID(int=0)),
            gender=profile_data.get('gender'),
            age_estimate=profile_data.get('age_estimate'),
            current_hair_length=profile_data.get('current_hair_length'),
            current_hair_color=profile_data.get('current_hair_color'),
            current_hair_texture=profile_data.get('current_hair_texture'),
            facial_hair=profile_data.get('facial_hair'),
            style_preferences=profile_data.get('style_preferences', []),
            previous_visagism_analyses=profile_data.get('previous_visagism_analyses', []),
            approved_appearances=profile_data.get('approved_appearances', []),
        )
        
        return VisagismAnalysisInput(
            photos=photos,
            profile=profile,
            analysis_types=analysis_request.get('analysis_types', ['hair']),
            include_report=True,
            include_visualization_data=True,
            correlation_id=context.get('correlation_id'),
        )
    
    def _map_angle(self, angle_str: str) -> PhotoAngle:
        """Mapeia string de angulo para enum."""
        mapping = {
            'front': PhotoAngle.FRONT_NEUTRAL,
            'left_profile': PhotoAngle.PROFILE_LEFT,
            'right_profile': PhotoAngle.PROFILE_RIGHT,
            'left_45': PhotoAngle.THREE_QUARTER_LEFT,
            'right_45': PhotoAngle.THREE_QUARTER_RIGHT,
            'smiling': PhotoAngle.FRONT_SMILING,
            'neutral': PhotoAngle.FRONT_NEUTRAL,
            'hairline': PhotoAngle.HAIRLINE,
            'posterior': PhotoAngle.POSTERIOR,
            'half_body': PhotoAngle.HALF_BODY,
        }
        return mapping.get(angle_str, PhotoAngle.FRONT_NEUTRAL)
    
    def _convert_output(self, result: VisagismAnalysisResult) -> Dict[str, Any]:
        """Converte resultado do pipeline para formato de saida do sistema."""
        
        # JSON canonico
        visagism_json = result.model_dump()
        
        # Relatorio humano
        report = result.human_report or "Relatorio nao gerado"
        
        # Legacy format para compatibilidade
        legacy = self._to_legacy_format(result)
        
        return {
            "visagism_analysis": visagism_json,
            "report": report,
            "legacy_format": legacy.model_dump(),
            "confidence": result.overall_confidence,
            "version": result.version,
            "generated_at": result.generated_at.isoformat(),
        }
    
    def _to_legacy_format(self, result: VisagismAnalysisResult) -> LegacyVisagismAnalysis:
        """Converte para formato legacy mantendo compatibilidade."""
        
        primary = result.primary_recommendation
        
        return LegacyVisagismAnalysis(
            face_shape_category=result.face_shape_category.value,
            face_shape_description=self._get_shape_description(result.face_shape_category),
            recommended_hairstyles=[
                primary.name if primary else "",
                *[alt.name for alt in result.alternative_recommendations[:2]],
            ],
            recommended_eyebrow_shapes=[],
            recommended_makeup_styles=[],
            contouring_tips=[],
            highlighting_tips=[],
            color_recommendations={},
            overall_recommendation=primary.justification if primary else "",
            confidence=result.overall_confidence,
        )
    
    def _get_shape_description(self, shape: PhotoAngle) -> str:
        """Retorna descricao do formato facial."""
        descriptions = {
            FaceShape.OVAL: "Formato equilibrado e versatil",
            FaceShape.ROUND: "Formato com curvas predominantes",
            FaceShape.SQUARE: "Formato com angulos marcantes",
            FaceShape.HEART: "Formato com testa larga e queixo estreito",
            FaceShape.DIAMOND: "Formato com zigomas proeminentes",
            FaceShape.OBLONG: "Formato alongado",
            FaceShape.TRIANGULAR: "Formato com mandibula larga",
            FaceShape.MIXED: "Formato com caracteristicas mistas",
            FaceShape.UNKNOWN: "Formato nao determinado",
        }
        return descriptions.get(shape, "")
    
    def _create_error_result(self, error_msg: str) -> Dict[str, Any]:
        """Cria resultado minimo em caso de erro."""
        return {
            "version": "1.0.0-error",
            "error": error_msg,
            "face_shape_category": "unknown",
            "overall_confidence": 0.0,
            "overall_confidence_explanation": f"Falha na analise: {error_msg}",
            "photo_assessments": [],
            "facial_measurements": [],
            "facial_proportions": [],
            "primary_recommendation": None,
            "alternative_recommendations": [],
            "analysis_limitations": [error_msg],
        }
