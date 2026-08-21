"""
MemoryService - camada de memória persistente do Vision Ecosystem.

O serviço suporta dois modos por compatibilidade:
1. Persistente: recebe AsyncSession (posicional ou via ``db=``) e usa PostgreSQL.
2. Local/legado: quando nenhuma sessão é fornecida, mantém a memória na instância.

O modo local existe para consumidores leves e testes antigos sem enfraquecer o
contrato persistente usado pela aplicação.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserFeedback, UserMemory
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryService:
    """Memória de usuário com backend PostgreSQL e fallback local compatível."""

    def __init__(self, db: Optional[AsyncSession] = None):
        self._db = db
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: Dict[str, datetime] = {}
        self._cache_duration = timedelta(minutes=5)
        self._local_memory: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._local_feedback: List[Dict[str, Any]] = []

    @staticmethod
    def _looks_like_db(value: Any) -> bool:
        return value is not None and callable(getattr(value, "execute", None))

    def _cache_key(self, user_id: UUID, key: str, category: str) -> str:
        return f"{user_id}:{category}:{key}"

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        if cache_key not in self._cache:
            return None
        if datetime.utcnow() >= self._cache_ttl.get(cache_key, datetime.min):
            self._cache.pop(cache_key, None)
            self._cache_ttl.pop(cache_key, None)
            return None
        return self._cache[cache_key]

    def _set_cache(self, cache_key: str, value: Any) -> None:
        self._cache[cache_key] = value
        self._cache_ttl[cache_key] = datetime.utcnow() + self._cache_duration

    def _invalidate_cache(self, user_id: UUID) -> None:
        prefix = f"{user_id}:"
        for cache_key in [k for k in self._cache if k.startswith(prefix)]:
            self._cache.pop(cache_key, None)
            self._cache_ttl.pop(cache_key, None)

    def _put_local(
        self,
        user_id: UUID,
        key: str,
        value: Any,
        category: str,
        ttl_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        expires_at = (
            datetime.utcnow() + timedelta(days=ttl_days) if ttl_days else None
        )
        user_bucket = self._local_memory.setdefault(str(user_id), {})
        category_bucket = user_bucket.setdefault(category, {})
        record = {
            "key": key,
            "value": value,
            "category": category,
            "expires_at": expires_at,
            "updated_at": datetime.utcnow(),
        }
        category_bucket[key] = record
        self._set_cache(self._cache_key(user_id, key, category), value)
        return record

    def _get_local(self, user_id: UUID, key: str, category: str) -> Optional[Any]:
        record = (
            self._local_memory.get(str(user_id), {})
            .get(category, {})
            .get(key)
        )
        if not record:
            return None
        expires_at = record.get("expires_at")
        if expires_at and datetime.utcnow() >= expires_at:
            self._local_memory[str(user_id)][category].pop(key, None)
            return None
        return record["value"]

    @staticmethod
    def _parse_store_args(
        args: Tuple[Any, ...],
        db: Optional[AsyncSession],
        user_id: Optional[UUID],
        key: Optional[str],
        value: Any,
        category: str,
    ) -> Tuple[Optional[AsyncSession], UUID, str, Any, str]:
        values = list(args)
        if values and MemoryService._looks_like_db(values[0]):
            db = values.pop(0)
        if user_id is None and values:
            user_id = values.pop(0)
        if key is None and values:
            key = values.pop(0)
        if value is None and values:
            value = values.pop(0)
        if values:
            category = values.pop(0)
        if user_id is None or key is None:
            raise TypeError("store requer user_id e key")
        return db, user_id, key, value, category

    async def store(
        self,
        *args: Any,
        db: Optional[AsyncSession] = None,
        user_id: Optional[UUID] = None,
        key: Optional[str] = None,
        value: Any = None,
        category: str = "general",
        ttl_days: Optional[int] = None,
    ) -> Any:
        """Armazena memória usando PostgreSQL ou o modo local compatível."""
        db, user_id, key, value, category = self._parse_store_args(
            args, db, user_id, key, value, category
        )
        db = db or self._db

        if not self._looks_like_db(db):
            return self._put_local(user_id, key, value, category, ttl_days)

        expires_at = datetime.utcnow() + timedelta(days=ttl_days) if ttl_days else None
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
        self._set_cache(self._cache_key(user_id, key, category), value)
        result = await db.execute(
            select(UserMemory).where(
                and_(UserMemory.user_id == user_id, UserMemory.memory_key == key)
            )
        )
        return result.scalar_one()

    async def retrieve(
        self,
        *args: Any,
        db: Optional[AsyncSession] = None,
        user_id: Optional[UUID] = None,
        key: Optional[str] = None,
        category: str = "general",
    ) -> Optional[Any]:
        """Recupera memória nos dois formatos de chamada suportados."""
        values = list(args)
        if values and self._looks_like_db(values[0]):
            db = values.pop(0)
        if user_id is None and values:
            user_id = values.pop(0)
        if key is None and values:
            key = values.pop(0)
        if values:
            category = values.pop(0)
        if user_id is None or key is None:
            raise TypeError("retrieve requer user_id e key")

        cache_key = self._cache_key(user_id, key, category)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        db = db or self._db
        if not self._looks_like_db(db):
            value = self._get_local(user_id, key, category)
            if value is not None:
                self._set_cache(cache_key, value)
            return value

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
        if not memory:
            return None
        memory.access_count += 1
        memory.last_accessed_at = datetime.utcnow()
        await db.commit()
        self._set_cache(cache_key, memory.value)
        return memory.value

    async def get_user_memory(
        self,
        *args: Any,
        db: Optional[AsyncSession] = None,
        user_id: Optional[UUID] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Lista memória; no modo legado também expõe categorias no topo."""
        values = list(args)
        if values and self._looks_like_db(values[0]):
            db = values.pop(0)
        if user_id is None and values:
            user_id = values.pop(0)
        if values and category is None:
            category = values.pop(0)
        if user_id is None:
            raise TypeError("get_user_memory requer user_id")

        db = db or self._db
        if not self._looks_like_db(db):
            source = self._local_memory.get(str(user_id), {})
            result: Dict[str, Any] = {}
            categories = [category] if category else list(source.keys())
            for cat in categories:
                entries = source.get(cat, {})
                result[cat] = {
                    key: record["value"]
                    for key, record in entries.items()
                    if not record.get("expires_at")
                    or datetime.utcnow() < record["expires_at"]
                }
            return result

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

    async def delete_memory(
        self,
        *args: Any,
        db: Optional[AsyncSession] = None,
        user_id: Optional[UUID] = None,
        key: Optional[str] = None,
        category: str = "general",
    ) -> bool:
        values = list(args)
        if values and self._looks_like_db(values[0]):
            db = values.pop(0)
        if user_id is None and values:
            user_id = values.pop(0)
        if key is None and values:
            key = values.pop(0)
        if user_id is None or key is None:
            raise TypeError("delete_memory requer user_id e key")

        db = db or self._db
        if not self._looks_like_db(db):
            user_bucket = self._local_memory.get(str(user_id), {})
            removed = False
            for cat, entries in user_bucket.items():
                if key in entries and (category == "general" or cat == category):
                    entries.pop(key, None)
                    removed = True
            self._invalidate_cache(user_id)
            return removed

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
        *args: Any,
        db: Optional[AsyncSession] = None,
        user_id: Optional[UUID] = None,
        item_type: Optional[str] = None,
        item_id: Optional[str] = None,
        feedback: Optional[str] = None,
        rating: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Registra feedback com ou sem sessão persistente."""
        values = list(args)
        if values and self._looks_like_db(values[0]):
            db = values.pop(0)
        for name in ("user_id", "item_type", "item_id", "feedback"):
            if not values:
                break
            if name == "user_id" and user_id is None:
                user_id = values.pop(0)
            elif name == "item_type" and item_type is None:
                item_type = values.pop(0)
            elif name == "item_id" and item_id is None:
                item_id = values.pop(0)
            elif name == "feedback" and feedback is None:
                feedback = values.pop(0)
        if user_id is None or item_type is None or item_id is None or feedback is None:
            raise TypeError("add_feedback requer user_id, item_type, item_id e feedback")

        payload = {
            "feedback": feedback,
            "rating": rating,
            "item_type": item_type,
            "item_id": item_id,
            "metadata": metadata or {},
        }
        db = db or self._db
        if not self._looks_like_db(db):
            feedback_id = str(uuid4())
            payload["feedback_id"] = feedback_id
            self._local_feedback.append({"user_id": str(user_id), **payload})
            self._put_local(
                user_id,
                f"feedback_{item_type}_{item_id}",
                payload,
                "feedback",
            )
            return payload

        feedback_record = UserFeedback(
            user_id=user_id,
            item_type=item_type,
            item_id=item_id,
            feedback_text=feedback,
            rating=rating,
            metadata=metadata or {},
        )
        db.add(feedback_record)
        await db.commit()
        await db.refresh(feedback_record)
        payload["feedback_id"] = str(feedback_record.id)
        await self.store(
            db=db,
            user_id=user_id,
            key=f"feedback_{item_type}_{item_id}",
            value=payload,
            category="feedback",
        )
        return feedback_record

    async def get_feedback(
        self,
        db: AsyncSession,
        user_id: UUID,
        item_type: Optional[str] = None,
        item_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query = select(UserFeedback).where(UserFeedback.user_id == user_id)
        if item_type:
            query = query.where(UserFeedback.item_type == item_type)
        if item_id:
            query = query.where(UserFeedback.item_id == item_id)
        query = query.order_by(desc(UserFeedback.created_at)).limit(limit)
        result = await db.execute(query)
        feedbacks = result.scalars().all()
        return [
            {
                "id": str(f.id),
                "item_type": f.item_type,
                "item_id": f.item_id,
                "feedback": f.feedback_text,
                "rating": f.rating,
                "metadata": f.metadata,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in feedbacks
        ]

    async def get_preferences(
        self, db: AsyncSession, user_id: UUID
    ) -> Dict[str, Any]:
        prefs = await self.get_user_memory(db, user_id, category="preferences")
        return {m["key"]: m["value"] for m in prefs.get("memories", [])}

    async def set_preference(
        self,
        db: AsyncSession,
        user_id: UUID,
        preference_key: str,
        value: Any,
    ) -> UserMemory:
        return await self.store(
            db=db,
            user_id=user_id,
            key=preference_key,
            value=value,
            category="preferences",
        )

    async def cleanup_expired(self, db: AsyncSession) -> int:
        result = await db.execute(
            select(UserMemory).where(
                and_(
                    UserMemory.expires_at.isnot(None),
                    UserMemory.expires_at < datetime.utcnow(),
                )
            )
        )
        expired = result.scalars().all()
        for memory in expired:
            await db.delete(memory)
        await db.commit()
        return len(expired)
