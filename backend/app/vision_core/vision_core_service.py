"""
VisionCoreService - Orquestrador central do Vision Ecosystem.

Responsabilidades:
- Receber comandos dos usuários
- Criar contexto de execução
- Identificar intenção
- Encaminhar tarefa ao agente correto
- Registrar execução
- Emitir eventos
- Solicitar aprovação quando necessário
- Registrar resultado
"""

from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from datetime import datetime

from app.agents.base import AgentContext, AgentResult
from app.vision_core.agent_router import AgentRouter
from app.vision_core.intent_recognizer import IntentRecognizer, IntentType
from app.vision_core.context_builder import ContextBuilder
from app.core.event_bus import emit_event, VisionEventType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VisionCoreService:
    """
    Vision Core - Orquestrador central do Vision Ecosystem.

    Responsabilidades:
    - Receber comandos dos usuários
    - Criar contexto de execução
    - Identificar intenção
    - Encaminhar tarefa ao agente correto
    - Registrar execução
    - Emitir eventos
    - Solicitar aprovação quando necessário
    - Registrar resultado
    """

    def __init__(self):
        self.router = AgentRouter()
        self.intent_recognizer = IntentRecognizer()
        self.context_builder = ContextBuilder()
        self._command_history: List[Dict[str, Any]] = []
        logger.info("VisionCoreService initialized")

    def register_agents(self, agents: List[Any]) -> None:
        """Registra agentes no roteador."""
        self.router.register_all(agents)
        logger.info(f"Registered {len(agents)} agents")

    async def process_command(
        self,
        user_id: UUID,
        tenant_id: UUID,
        input_type: str,  # text | voice
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Processa um comando do usuário.

        Fluxo:
        1. Registra comando
        2. Identifica intenção
        3. Escolhe agente
        4. Cria AI Task
        5. Executa fluxo
        6. Registra resultado
        """
        command_id = str(uuid4())
        correlation_id = str(uuid4())

        # 1. Registra comando
        command_record = {
            "command_id": command_id,
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "input_type": input_type,
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._command_history.append(command_record)

        logger.info(f"Command received: {command_id} - {text[:50]}...")

        # 2. Identifica intenção
        intent_result = self.intent_recognizer.recognize_with_confidence(text)
        intent = intent_result["intent"]

        # 3. Cria contexto
        context = await self.context_builder.build(
            user_id=user_id,
            tenant_id=tenant_id,
            intent=intent,
            input_data={"text": text, "input_type": input_type},
            metadata=metadata,
        )

        # 4. Emite evento de task criada
        await emit_event(
            event_type=VisionEventType.AI_TASK_CREATED,
            payload={
                "command_id": command_id,
                "intent": intent,
                "input_type": input_type,
                "text_preview": text[:100],
            },
            source="VisionCoreService",
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            correlation_id=correlation_id,
        )

        # 5. Seleciona e executa agente
        agent = self.router.get_agent(context)

        if not agent:
            error_msg = f"No agent found for intent: {intent}"
            logger.error(error_msg)

            await emit_event(
                event_type=VisionEventType.AI_TASK_FAILED,
                payload={"command_id": command_id, "error": error_msg},
                source="VisionCoreService",
                correlation_id=correlation_id,
            )

            return {
                "command_id": command_id,
                "success": False,
                "error": error_msg,
                "intent": intent,
            }

        # 6. Executa o agente
        try:
            result = await agent.execute(context)

            # 7. Valida resultado
            is_valid = agent.validate(result)

            # 8. Emite evento apropriado
            if result.success and is_valid:
                event_type = VisionEventType.AI_TASK_COMPLETED
            else:
                event_type = VisionEventType.AI_TASK_FAILED

            await emit_event(
                event_type=event_type,
                payload={
                    "command_id": command_id,
                    "agent": agent.name,
                    "success": result.success,
                    "requires_approval": result.requires_approval,
                },
                source="VisionCoreService",
                user_id=str(user_id),
                tenant_id=str(tenant_id),
                correlation_id=correlation_id,
            )

            # 9. Se requer aprovação, emite evento específico
            if result.requires_approval:
                await emit_event(
                    event_type=VisionEventType.CONTENT_APPROVAL_REQUESTED,
                    payload={
                        "command_id": command_id,
                        "approval_type": result.approval_type,
                        "agent_result": result.to_dict(),
                    },
                    source="VisionCoreService",
                    user_id=str(user_id),
                    tenant_id=str(tenant_id),
                    correlation_id=correlation_id,
                )

            return {
                "command_id": command_id,
                "success": result.success,
                "intent": intent,
                "agent": agent.name,
                "result": result.to_dict(),
                "requires_approval": result.requires_approval,
                "correlation_id": correlation_id,
            }

        except Exception as e:
            logger.error(f"Error executing agent: {e}", exc_info=True)

            await emit_event(
                event_type=VisionEventType.AI_TASK_FAILED,
                payload={"command_id": command_id, "error": str(e)},
                source="VisionCoreService",
                correlation_id=correlation_id,
            )

            return {
                "command_id": command_id,
                "success": False,
                "error": str(e),
                "intent": intent,
            }

    def get_command_history(
        self,
        user_id: Optional[UUID] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retorna histórico de comandos."""
        history = self._command_history
        if user_id:
            history = [c for c in history if c["user_id"] == str(user_id)]
        return history[-limit:]

    def get_health(self) -> Dict[str, Any]:
        """Retorna saúde do Vision Core."""
        return {
            "status": "healthy",
            "total_commands_processed": len(self._command_history),
            "agents": self.router.get_health(),
            "intent_recognizer": "active",
        }
