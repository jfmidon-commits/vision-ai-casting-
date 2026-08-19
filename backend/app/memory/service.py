"""
MemoryService - Camada de Memória do Vision Ecosystem.

Responsável por:
- Armazenar preferências do usuário
- Manter histórico de decisões
- Registrar feedbacks
- Consultar memória para agentes
"""

from typing import Dict, List, Any, Optional
from uuid import UUID

from app.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryService:
    """
    Camada de Memória do Vision Ecosystem.

    Placeholder - futuramente persistirá em banco de dados vetorial
    ou estrutura especializada de memória.
    """

    def __init__(self):
        # Memória em memória (placeholder)
        self._memory: Dict[str, Dict[str, Any]] = {}

    async def store(
        self,
        user_id: UUID,
        key: str,
        value: Any,
        category: str = "general",
    ) -> None:
        """Armazena um valor na memória do usuário."""
        user_key = str(user_id)
        if user_key not in self._memory:
            self._memory[user_key] = {}

        if category not in self._memory[user_key]:
            self._memory[user_key][category] = {}

        self._memory[user_key][category][key] = {
            "value": value,
            "stored_at": "2024-01-01T00:00:00",  # placeholder
        }

        logger.info(f"Memory stored for user {user_id}: {key}")

    async def retrieve(
        self,
        user_id: UUID,
        key: str,
        category: str = "general",
    ) -> Optional[Any]:
        """Recupera um valor da memória do usuário."""
        user_key = str(user_id)
        if user_key not in self._memory:
            return None

        if category not in self._memory[user_key]:
            return None

        entry = self._memory[user_key][category].get(key)
        return entry["value"] if entry else None

    async def get_user_memory(
        self,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """Retorna toda a memória de um usuário."""
        return self._memory.get(str(user_id), {})

    async def add_feedback(
        self,
        user_id: UUID,
        item_type: str,
        item_id: str,
        feedback: str,
        rating: Optional[int] = None,
    ) -> None:
        """Adiciona feedback do usuário sobre um item."""
        await self.store(
            user_id=user_id,
            key=f"feedback_{item_type}_{item_id}",
            value={
                "feedback": feedback,
                "rating": rating,
                "item_type": item_type,
                "item_id": item_id,
            },
            category="feedback",
        )
