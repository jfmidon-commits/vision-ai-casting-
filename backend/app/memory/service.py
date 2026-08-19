"""
MemoryService - Camada de Memória Persistente do Vision Ecosystem.

Responsável por:
- Armazenar preferências do usuário no banco de dados
- Manter histórico de decisões
- Registrar feedbacks
- Consultar memória para agentes
- Cache inteligente com TTL
"""

from typing import Dict, List, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.dialects.postgresql import insert

from app.models import UserMemory, UserFeedback
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryService:
    """
    Camada de Memória Persistente do Vision Ecosystem.
    Armazena memórias de usuários no PostgreSQL com cache em memória.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self._db = db
        # Cache em memória para acesso rápido (TTL: 5 minutos)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl: Dict[str, datetime] = {}
        self._cache_duration = timedelta(minutes=5)

    def _cache_key(self, user_id: UUID, key: str, category: str) -> str:
        """Gera chave de cache."""
        return f"{user_id}:{category}:{key}"

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Recupera valor do cache se válido."""
        if cache_key in self._cache:
            if datetime.utcnow() < self._cache_ttl.get(cache_key, datetime.min):
                return self._cache[cache_key]
            # Expirado, remover
            del self._cache[cache_key]
            del self._cache_ttl[cache_key]
        return None

    def _set_cache(self, cache_key: str, value: Any) -> None:
        """Armazena valor no cache com TTL."""
        self._cache[cache_key] = value
        self._cache_ttl[cache_key] = datetime.utcnow() + self._cache_duration

    def _invalidate_cache(self, user_id: UUID) -> None:
        """Invalida todo o cache de um usuário."""
        prefix = f"{user_id}:"
        keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
        for k in keys_to_remove:
            del self._cache[k]
            if k in self._cache_ttl:
                del self._cache_ttl[k]

    async def store(
        self,
        db: AsyncSession,
        user_id: UUID,
        key: str,
        value: Any,
        category: str = "general",
        ttl_days: Optional[int] = None,
    ) -> UserMemory:
        """
        Armazena um valor na memória persistente do usuário.

        Args:
            db: Sessão do banco de dados
            user_id: ID do usuário
            key: Chave da memória
            value: Valor a ser armazenado (serializável em JSON)
            category: Categoria da memória
            ttl_days: Dias até expiração (None = sem expiração)

        Returns:
            UserMemory: Registro criado/atualizado
        """
        expires_at = None
        if ttl_days:
            expires_at = datetime.utcnow() + timedelta(days=ttl_days)

        # Upsert: atualiza se existe, cria se não
        stmt = (
            insert(UserMemory)
            .values(
                user_id=user_id,
                memory_key=key,
                category=category,
                value=value,
                expires_at=expires_at,
                updated_at=datetime.utcnow(),
            )
            .on_conflict_do_update(
                index_elements=["user_id", "memory_key"],
                set_={
                    "value": value,
                    "category": category,
                    "expires_at": expires_at,
                    "updated_at": datetime.utcnow(),
                    "access_count": UserMemory.access_count + 1,
                },
            )
        )

        await db.execute(stmt)
        await db.commit()

        # Atualizar cache
        cache_key = self._cache_key(user_id, key, category)
        self._set_cache(cache_key, value)

        logger.info(f"Memory stored for user {user_id}: {key} (category: {category})")

        # Retornar o registro
        result = await db.execute(
            select(UserMemory).where(
                and_(UserMemory.user_id == user_id, UserMemory.memory_key == key)
            )
        )
        return result.scalar_one()

    async def retrieve(
        self,
        db: AsyncSession,
        user_id: UUID,
        key: str,
        category: str = "general",
    ) -> Optional[Any]:
        """
        Recupera um valor da memória do usuário.

        Args:
            db: Sessão do banco de dados
            user_id: ID do usuário
            key: Chave da memória
            category: Categoria da memória

        Returns:
            Valor armazenado ou None
        """
        cache_key = self._cache_key(user_id, key, category)

        # Tentar cache primeiro
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            logger.debug(f"Memory cache hit for user {user_id}: {key}")
            return cached

        # Buscar no banco
        result = await db.execute(
            select(UserMemory).where(
                and_(
                    UserMemory.user_id == user_id,
                    UserMemory.memory_key == key,
                    or_(
                        UserMemory.expires_at.is_(None),
                        UserMemory.expires_at > datetime.utcnow(),
                    ),
                )
            )
        )
        memory = result.scalar_one_or_none()

        if memory:
            memory.access_count += 1
            memory.last_accessed_at = datetime.utcnow()
            await db.commit()
            self._set_cache(cache_key, memory.value)
            return memory.value

        return None

    async def get_user_memory(
        self,
        db: AsyncSession,
        user_id: UUID,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        query = select(UserMemory).where(
            and_(
                UserMemory.user_id == user_id,
                or_(
                    UserMemory.expires_at.is_(None),
                    UserMemory.expires_at > datetime.utcnow(),
                ),
            )
        )

        if category:
            query = query.where(UserMemory.category == category)

        query = query.order_by(desc(UserMemory.updated_at)).limit(limit)
        result = await db.execute(query)
        memories = result.scalars().all()

        return {
            "memories": [
                {
                    "key": m.memory_key,
                    "value": m.value,
                    "category": m.category,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "updated_at": m.updated_at.isoformat() if m.updated_at else None,
                    "access_count": m.access_count,
                    "expires_at": m.expires_at.isoformat() if m.expires_at else None,
                }
                for m in memories
            ],
            "total": len(memories),
            "user_id": str(user_id),
        }

    async def delete_memory(self, db: AsyncSession, user_id: UUID, key: str) -> bool:
        result = await db.execute(
            select(UserMemory).where(
                and_(UserMemory.user_id == user_id, UserMemory.memory_key == key)
            )
        )
        memory = result.scalar_one_or_none()
        if not memory:
            return False
        await db.delete(memory)
        await db.commit()
        self._invalidate_cache(user_id)
        return True

    async def add_feedback(
        self,
        db: AsyncSession,
        user_id: UUID,
        item_type: str,
        item_id: str,
        feedback_text: Optional[str] = None,
        rating: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UserFeedback:
        feedback = UserFeedback(
            user_id=user_id,
            item_type=item_type,
            item_id=item_id,
            feedback_text=feedback_text,
            rating=rating,
            _metadata=metadata or {},
        )
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)
        return feedback

    async def get_feedback(
        self,
        db: AsyncSession,
        user_id: UUID,
        item_type: Optional[str] = None,
        item_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[UserFeedback]:
        query = select(UserFeedback).where(UserFeedback.user_id == user_id)
        if item_type:
            query = query.where(UserFeedback.item_type == item_type)
        if item_id:
            query = query.where(UserFeedback.item_id == item_id)
        query = query.order_by(desc(UserFeedback.created_at)).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())
