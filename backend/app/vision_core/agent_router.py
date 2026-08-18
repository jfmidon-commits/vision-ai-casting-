"""
AgentRouter - Roteador de agentes do Vision Core.

Responsável por:
- Registrar todos os agentes disponíveis
- Selecionar o agente correto baseado na intenção
- Fallback para agentes genéricos
"""

from typing import List, Optional, Dict, Any
from app.agents.base import VisionAgent, AgentContext, AgentResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AgentRouter:
    """
    Roteador de agentes do Vision Core.

    Responsável por:
    - Registrar todos os agentes disponíveis
    - Selecionar o agente correto baseado na intenção
    - Fallback para agentes genéricos
    """

    def __init__(self):
        self._agents: List[VisionAgent] = []

    def register(self, agent: VisionAgent) -> None:
        """Registra um novo agente."""
        self._agents.append(agent)
        logger.info(f"Agent registered: {agent.name} (id={agent.id})")

    def register_all(self, agents: List[VisionAgent]) -> None:
        """Registra múltiplos agentes."""
        for agent in agents:
            self.register(agent)

    def get_agent(self, context: AgentContext) -> Optional[VisionAgent]:
        """
        Seleciona o melhor agente para o contexto.

        Prioridade:
        1. Agente que declara can_handle=True
        2. Agente com maior número de capabilities relevantes
        3. Primeiro agente disponível
        """
        candidates = []

        for agent in self._agents:
            if agent.status.value != "active":
                continue

            if agent.can_handle(context):
                candidates.append(agent)

        if not candidates:
            logger.warning(f"No agent found for intent: {context.intent}")
            return None

        # Retorna o primeiro match (pode ser melhorado com scoring)
        return candidates[0]

    def get_all_agents(self) -> List[VisionAgent]:
        """Retorna todos os agentes registrados."""
        return self._agents.copy()

    def get_agent_by_name(self, name: str) -> Optional[VisionAgent]:
        """Busca agente pelo nome."""
        for agent in self._agents:
            if agent.name == name:
                return agent
        return None

    def get_health(self) -> Dict[str, Any]:
        """Retorna saúde de todos os agentes."""
        return {
            "total_agents": len(self._agents),
            "agents": [agent.health_check() for agent in self._agents],
        }
