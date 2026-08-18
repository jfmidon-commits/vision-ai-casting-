"""
backend/app/agents/visagism_agent.py

VisagismAgent — implementacao real (v2.0.0).

Substitui o mock anterior. Agora orquestra o pipeline hibrido de
analise de visagismo, produzindo recomendacoes de corte tecnicamente
justificadas com rastreabilidade completa.

Compativel com a interface VisionAgent (base.py).
"""

import logging
from typing import Dict, List, Optional, Any

from app.agents.base import (
    VisionAgent, AgentContext, AgentResult,
    AgentCapability, AgentStatus,
)
from app.ai.visagism.pipeline import VisagismPipeline
from app.ai.visagism.schemas import VisagismAnalysisInput, ProfileContext, PhotoInput, PhotoAngle
from app.core.event_bus import EventBus

logger = logging.getLogger(__name__)


class VisagismAgent(VisionAgent):
    """
    Agente de visagismo capilar real.
    
    Responsabilidades:
    1. Receber solicitacoes de analise de visagismo via AgentContext
    2. Validar pre-condicoes (fotos suficientes, permissao, etc)
    3. Orquestrar o VisagismPipeline
    4. Retornar AgentResult com JSON canonico + relatorio + metadata
    5. Registrar na CareerMemory quando apropriado
    
    Intents suportados:
    - ANALYZE_VISAGISM: analise completa
    - STYLE_RECOMMENDATION: recomendacao de estilo/corte
    - HAIR_ANALYSIS: analise especifica de cabelo
    
    Contrato VisionAgent:
    - can_handle(context: AgentContext) -> bool
    - execute(context: AgentContext) -> AgentResult
    - validate(result: AgentResult) -> bool  [obrigatorio da base]
    """
    
    SUPPORTED_INTENTS = [
        "ANALYZE_VISAGISM",
        "STYLE_RECOMMENDATION",
        "HAIR_ANALYSIS",
    ]
    
    def __init__(self):
        super().__init__(
            name="VisagismAgent",
            description="Agente de analise de visagismo capilar com pipeline hibrido proprietario",
            capabilities=[
                AgentCapability.VISAGISM_ANALYSIS,
                AgentCapability.STYLE_RECOMMENDATION,
            ],
        )
        self.pipeline = VisagismPipeline()
        self.event_bus = EventBus()
    
    def can_handle(self, context: AgentContext) -> bool:
        """
        Verifica se este agente pode processar a solicitacao.
        
        Args:
            context: Contexto da solicitacao
            
        Returns:
            True se o intent e suportado
        """
        return context.intent in self.SUPPORTED_INTENTS
    
    def _validate_input(self, context: AgentContext) -> tuple[bool, Optional[str]]:
        """
        Valida se o contexto tem dados suficientes para analise.
        
        Args:
            context: Contexto da solicitacao
            
        Returns:
            (is_valid, error_message)
        """
        input_data = context.input_data
        
        # Verificar se ha fotos
        photos = input_data.get('photos', [])
        if not photos:
            return False, "Nenhuma foto fornecida para analise de visagismo"
        
        # Verificar se ha pelo menos uma foto usavel
        usable = [p for p in photos if p.get('is_usable', True)]
        if not usable:
            return False, "Nenhuma foto usavel para analise de visagismo"
        
        # Verificar se ha contexto de perfil
        profile = input_data.get('profile')
        if not profile:
            logger.warning("Analise de visagismo sem contexto de perfil — usando defaults")
        
        return True, None
    
    def validate(self, result: AgentResult) -> bool:
        """
        Valida se o resultado da execucao e aceitavel.
        
        Implementacao obrigatoria do contrato VisionAgent.
        
        Args:
            result: O resultado a ser validado
            
        Returns:
            True se o resultado e valido
        """
        if not result.success:
            return False
        
        # Validar estrutura minima
        data = result.data or {}
        visagism_result = data.get('visagism_result', {})
        
        # Deve ter face_shape
        if not visagism_result.get('face_shape_category'):
            return False
        
        # Deve ter pelo menos uma recomendacao ou explicar por que nao
        if not visagism_result.get('primary_recommendation'):
            # Permitido se houver limitacoes explicadas
            if not visagism_result.get('analysis_limitations'):
                return False
        
        # Confidence deve estar no range valido
        if not (0.0 <= result.confidence <= 1.0):
            return False
        
        return True
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Executa a analise de visagismo.
        
        Args:
            context: Contexto completo da solicitacao
            
        Returns:
            AgentResult com resultado da analise
        """
        logger.info(f"VisagismAgent executando intent: {context.intent}")
        self._increment_execution()
        
        # 1. Validar entrada
        is_valid, error = self._validate_input(context)
        if not is_valid:
            logger.warning(f"Validacao de entrada falhou: {error}")
            self._increment_error()
            return AgentResult(
                success=False,
                data={"error": error, "intent": context.intent},
                message=error,
                error=error,
                requires_approval=False,
                confidence=0.0,
            )
        
        # 2. Converter para input do pipeline
        try:
            pipeline_input = self._build_pipeline_input(context)
        except Exception as e:
            logger.error(f"Erro ao construir input do pipeline: {str(e)}")
            self._increment_error()
            return AgentResult(
                success=False,
                data={"error": str(e)},
                message="Erro na preparacao da analise",
                error=str(e),
                requires_approval=False,
                confidence=0.0,
            )
        
        # 3. Executar pipeline
        try:
            result = await self.pipeline.execute(pipeline_input)
            
            # 4. Construir AgentResult
            agent_result = self._build_agent_result(result, context)
            
            # 5. Validar resultado (contrato da base)
            if not self.validate(agent_result):
                logger.warning("Resultado da analise nao passou na validacao estrutural")
                agent_result.success = False
                agent_result.error = "Resultado estruturalmente invalido"
            
            # 6. Registrar na memoria se configurado
            if context.memory:
                await self._update_memory(context, result)
            
            logger.info(
                f"VisagismAgent concluido. Success={agent_result.success}, "
                f"Confidence={agent_result.confidence:.2f}"
            )
            
            return agent_result
            
        except Exception as e:
            logger.error(f"Erro no pipeline de visagismo: {str(e)}", exc_info=True)
            self._increment_error()
            return AgentResult(
                success=False,
                data={"error": str(e), "intent": context.intent},
                message="Erro durante a analise de visagismo",
                error=str(e),
                requires_approval=False,
                confidence=0.0,
            )
    
    def _build_pipeline_input(self, context: AgentContext) -> VisagismAnalysisInput:
        """Constroi VisagismAnalysisInput a partir do AgentContext."""
        
        input_data = context.input_data
        
        # Fotos
        photos = []
        for photo_data in input_data.get('photos', []):
            angle_str = photo_data.get('angle', 'front')
            angle = self._map_angle(angle_str)
            
            photos.append(PhotoInput(
                photo_id=photo_data.get('id'),
                url=photo_data.get('url', ''),
                angle=angle,
                quality_score=photo_data.get('quality_score'),
                is_usable=photo_data.get('is_usable', True),
                unusable_reason=photo_data.get('unusable_reason'),
            ))
        
        # Perfil
        profile_data = input_data.get('profile', {})
        profile = ProfileContext(
            profile_id=profile_data.get('id'),
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
        
        # Metadados
        metadata = context.metadata or {}
        
        return VisagismAnalysisInput(
            photos=photos,
            profile=profile,
            analysis_types=input_data.get('analysis_types', ['hair']),
            include_report=True,
            include_visualization_data=True,
            correlation_id=metadata.get('correlation_id'),
        )
    
    def _map_angle(self, angle_str: str) -> PhotoAngle:
        """Mapeia string de angulo para enum."""
        mapping = {
            'front': PhotoAngle.FRONT_NEUTRAL,
            'front_neutral': PhotoAngle.FRONT_NEUTRAL,
            'left_profile': PhotoAngle.PROFILE_LEFT,
            'right_profile': PhotoAngle.PROFILE_RIGHT,
            'left_45': PhotoAngle.THREE_QUARTER_LEFT,
            'right_45': PhotoAngle.THREE_QUARTER_RIGHT,
            'three_quarter_left': PhotoAngle.THREE_QUARTER_LEFT,
            'three_quarter_right': PhotoAngle.THREE_QUARTER_RIGHT,
            'smiling': PhotoAngle.FRONT_SMILING,
            'front_smiling': PhotoAngle.FRONT_SMILING,
            'neutral': PhotoAngle.FRONT_NEUTRAL,
            'hairline': PhotoAngle.HAIRLINE,
            'posterior': PhotoAngle.POSTERIOR,
            'half_body': PhotoAngle.HALF_BODY,
        }
        return mapping.get(angle_str, PhotoAngle.FRONT_NEUTRAL)
    
    def _build_agent_result(
        self,
        result: Any,  # VisagismAnalysisResult
        context: AgentContext,
    ) -> AgentResult:
        """Constroi AgentResult a partir do resultado do pipeline."""
        
        # Determinar se precisa de aprovacao
        requires_approval = result.overall_confidence < 0.6
        
        # Construir mensagem
        if result.primary_recommendation:
            primary = result.primary_recommendation
            message = (
                f"Analise de visagismo concluida. "
                f"Recomendacao principal: {primary.name} "
                f"(confianca: {result.overall_confidence:.0%})"
            )
        else:
            message = (
                f"Analise de visagismo concluida com limitacoes. "
                f"Confianca: {result.overall_confidence:.0%}"
            )
        
        # Dados completos
        data = {
            "visagism_result": result.model_dump(),
            "human_report": result.human_report,
            "visualization_data": result.visualization_data,
            "evidence_map": result.evidence_map,
            "intent": context.intent,
        }
        
        return AgentResult(
            success=result.overall_confidence > 0.3,  # Sucesso parcial se > 30%
            data=data,
            message=message,
            error=None,
            requires_approval=requires_approval,
            confidence=result.overall_confidence,
        )
    
    async def _update_memory(self, context: AgentContext, result: Any) -> None:
        """Atualiza CareerMemory com resultado da analise."""
        try:
            memory = context.memory
            
            # Registrar preferencias de estilo
            if result.primary_recommendation:
                await memory.add_style_preference(
                    profile_id=context.input_data.get('profile', {}).get('id'),
                    preference={
                        "type": "visagism_recommendation",
                        "primary_cut": result.primary_recommendation.name,
                        "face_shape": result.face_shape_category.value,
                        "confidence": result.overall_confidence,
                        "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
                    }
                )
            
            # Registrar aparencia
            await memory.add_appearance_record(
                profile_id=context.input_data.get('profile', {}).get('id'),
                appearance={
                    "type": "visagism_analysis",
                    "analysis_id": context.metadata.get('analysis_id') if context.metadata else None,
                    "result_summary": result.human_report[:500] if result.human_report else "",
                }
            )
            
        except Exception as e:
            logger.warning(f"Erro ao atualizar memoria: {str(e)}")
