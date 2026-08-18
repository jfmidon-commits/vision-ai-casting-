"""
ContextBuilder - Construtor de contexto do Vision Core.

Monta o AgentContext completo a partir dos dados do comando,
incluindo memória do usuário e metadados relevantes.
"""

from typing import Dict, Any, Optional
from uuid import UUID
from app.agents.base import AgentContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ContextBuilder:
    """
    Construtor de contexto do Vision Core.

    Monta o AgentContext completo a partir dos dados do comando,
    incluindo memória do usuário e metadados relevantes.
    """

    def __init__(self):
        pass

    async def build(
        self,
        user_id: UUID,
        tenant_id: UUID,
        intent: str,
        input_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentContext:
        """
        Constrói o contexto completo para execução.

        Args:
            user_id: ID do usuário
            tenant_id: ID do tenant
            intent: Intenção reconhecida
            input_data: Dados de entrada
            metadata: Metadados adicionais

        Returns:
            AgentContext pronto para uso
        """
        # Busca memória do usuário (placeholder)
        memory = await self._load_memory(user_id)

        context = AgentContext(
            user_id=user_id,
            tenant_id=tenant_id,
            intent=intent,
            input_data=input_data,
            metadata=metadata or {},
            memory=memory,
        )

        logger.info(f"Context built for user {user_id}, intent: {intent}")
        return context

    async def _load_memory(self, user_id: UUID) -> Dict[str, Any]:
        """
        Carrega memória do usuário.

        Placeholder - futuramente consultará o banco de memória.
        """
        return {
            "user_id": str(user_id),
            "loaded_at": "2024-01-01T00:00:00",  # placeholder
            "preferences": {},
            "history": [],
        }
