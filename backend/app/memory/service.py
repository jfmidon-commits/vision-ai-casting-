"""Persistent user memory with backward-compatible in-memory fallback."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserFeedback, UserMemory
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryService:
    """Store memory in PostgreSQL when a DB session is available.

    Calls without a DB keep the original Vision API working through a local
    in-memory fallback; production callers can pass/inject an AsyncSession.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self._db = db
        self._memory: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: Dict[str, datetime] = {}
        self._cache_duration = timedelta(minutes=5)

    @staticmethod
    def _looks_like_db(value: Any) -> bool:
        return value is not None and hasattr(value, "execute") and hasattr(value, "commit")

    def _cache_key(self, user_id: UUID, key: str, category: str) -> str:
        return f"{user_id}:{category}:{key}"

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        expires = self._cache_ttl.get(cache_key)
        if cache_key in self._cache and expires and datetime.utcnow() < expires:
            return self._cache[cache_key]
        self._cache.pop(cache_key, None)
        self._cache_ttl.pop(cache_key, None)
        return None

    def _set_cache(self, cache_key: str, value: Any) -> None:
        self._cache[cache_key] = value
        self._cache_ttl[cache_key] = datetime.utcnow() + self._cache_duration

    def _invalidate_cache(self, user_id: UUID) -> None:
        prefix = f"{user_id}:"
        for key in [k for k in self._cache if k.startswith(prefix)]:
            self._cache.pop(key, None)
            self._cache_ttl.pop(key, None)

    def _parse_memory_args(
        self, args: Tuple[Any, ...], kwargs: Dict[str, Any], *, include_value: bool
    ) -> Tuple[Optional[AsyncSession], UUID, str, Any, str, Optional[int]]:
        values = list(args)
        db = kwargs.pop("db", None)
        if values and self._looks_like_db(values[0]):
            db = values.pop(0)
        db = db or self._db
        user_id = kwargs.pop("user_id", values.pop(0) if values else None)
        key = kwargs.pop("key", values.pop(0) if values else None)
        value = kwargs.pop("value", values.pop(0) if values else None) if include_value else None
        category = kwargs.pop("category", values.pop(0) if values else "general")
        ttl_days = kwargs.pop("ttl_days", values.pop(0) if values else None)
        if user_id is None or key is None:
            raise TypeError("user_id and key are required")
        return db, user_id, key, value, category, ttl_days

    async def store(self, *args: Any, **kwargs: Any) -> Optional[UserMemory]:
        db, user_id, key, value, category, ttl_days = self._parse_memory_args(
            args, kwargs, include_value=True
        )
        expires_at = datetime.utcnow() + timedelta(days=ttl_days) if ttl_days else None
        cache_key = self._cache_key(user_id, key, category)

        if db is None:
            self._memory.setdefault(str(user_id), {}).setdefault(category, {})[key] = {
                "value": value,
                "stored_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at,
            }
            self._set_cache(cache_key, value)
            return None

        result = await db.execute(
            select(UserMemory).where(
                and_(UserMemory.user_id == user_id, UserMemory.memory_key == key)
            )
        )
        memory = result.scalar_one_or_none()
        if memory is None:
            memory = UserMemory(
                user_id=user_id,
                memory_key=key,
                category=category,
                value=value,
                expires_at=expires_at,
            )
            db.add(memory)
        else:
            memory.category = category
            memory.value = value
            memory.expires_at = expires_at
            memory.updated_at = datetime.utcnow()
            memory.access_count = (memory.access_count or 0) + 1
        await db.commit()
        try:
            await db.refresh(memory)
        except Exception:
            pass
        self._set_cache(cache_key, value)
        return memory

    async def retrieve(self, *args: Any, **kwargs: Any) -> Optional[Any]:
        db, user_id, key, _, category, _ = self._parse_memory_args(
            args, kwargs, include_value=False
        )
        cache_key = self._cache_key(user_id, key, category)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        if db is None:
            entry = self._memory.get(str(user_id), {}).get(category, {}).get(key)
            if not entry:
                return None
            expires_at = entry.get("expires_at")
            if expires_at and datetime.utcnow() >= expires_at:
                return None
            self._set_cache(cache_key, entry["value"])
            return entry["value"]

        result = await db.execute(
            select(UserMemory).where(
                and_(
                    UserMemory.user_id == user_id,
                    UserMemory.memory_key == key,
                    or_(UserMemory.expires_at.is_(None), UserMemory.expires_at > datetime.utcnow()),
                )
            )
        )
        memory = result.scalar_one_or_none()
        if memory is None:
            return None
        memory.access_count = (memory.access_count or 0) + 1
        memory.last_accessed_at = datetime.utcnow()
        await db.commit()
        self._set_cache(cache_key, memory.value)
        return memory.value

    async def get_user_memory(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        values = list(args)
        db = kwargs.pop("db", None)
        if values and self._looks_like_db(values[0]):
            db = values.pop(0)
        db = db or self._db
        user_id = kwargs.pop("user_id", values.pop(0) if values else None)
        category = kwargs.pop("category", values.pop(0) if values else None)
        limit = kwargs.pop("limit", values.pop(0) if values else 100)
        if user_id is None:
            raise TypeError("user_id is required")

        if db is None:
            memory = self._memory.get(str(user_id), {})
            if category is not None:
                return {category: memory.get(category, {})} if category in memory else {}
            return memory

        query = select(UserMemory).where(
            and_(
                UserMemory.user_id == user_id,
                or_(UserMemory.expires_at.is_(None), UserMemory.expires_at > datetime.utcnow()),
            )
        )
        if category:
            query = query.where(UserMemory.category == category)
        result = await db.execute(query.order_by(desc(UserMemory.updated_at)).limit(limit))
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

    async def delete_memory(self, *args: Any, **kwargs: Any) -> bool:
        db, user_id, key, _, _, _ = self._parse_memory_args(args, kwargs, include_value=False)
        if db is None:
            removed = False
            for entries in self._memory.get(str(user_id), {}).values():
                if key in entries:
                    del entries[key]
                    removed = True
            self._invalidate_cache(user_id)
            return removed

        result = await db.execute(
            select(UserMemory).where(
                and_(UserMemory.user_id == user_id, UserMemory.memory_key == key)
            )
        )
        memory = result.scalar_one_or_none()
        if memory is None:
            return False
        await db.delete(memory)
        await db.commit()
        self._invalidate_cache(user_id)
        return True

    async def add_feedback(self, *args: Any, **kwargs: Any) -> Optional[UserFeedback]:
        values = list(args)
        db = kwargs.pop("db", None)
        if values and self._looks_like_db(values[0]):
            db = values.pop(0)
        db = db or self._db
        user_id = kwargs.pop("user_id", values.pop(0) if values else None)
        item_type = kwargs.pop("item_type", values.pop(0) if values else None)
        item_id = kwargs.pop("item_id", values.pop(0) if values else None)
        feedback = kwargs.pop("feedback", values.pop(0) if values else None)
        rating = kwargs.pop("rating", values.pop(0) if values else None)
        metadata = kwargs.pop("metadata", values.pop(0) if values else None)
        if user_id is None or item_type is None or item_id is None:
            raise TypeError("user_id, item_type and item_id are required")

        payload = {
            "feedback": feedback,
            "rating": rating,
            "item_type": item_type,
            "item_id": item_id,
        }
        if db is None:
            await self.store(
                user_id=user_id,
                key=f"feedback_{item_type}_{item_id}",
                value=payload,
                category="feedback",
            )
            return None

        feedback_record = UserFeedback(
            user_id=user_id,
            item_type=item_type,
            item_id=item_id,
            feedback_text=feedback,
            rating=rating,
            _metadata=metadata or {},
        )
        db.add(feedback_record)
        await db.commit()
        try:
            await db.refresh(feedback_record)
        except Exception:
            pass
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
        result = await db.execute(query.order_by(desc(UserFeedback.created_at)).limit(limit))
        return [
            {
                "id": str(f.id),
                "item_type": f.item_type,
                "item_id": f.item_id,
                "feedback": f.feedback_text,
                "rating": f.rating,
                "metadata": f._metadata,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in result.scalars().all()
        ]

    async def get_preferences(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        memory = await self.get_user_memory(*args, category="preferences", **kwargs)
        if "memories" in memory:
            return {m["key"]: m["value"] for m in memory["memories"]}
        return {key: entry["value"] for key, entry in memory.get("preferences", {}).items()}

    async def set_preference(
        self, db: AsyncSession, user_id: UUID, preference_key: str, value: Any
    ) -> Optional[UserMemory]:
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
                and_(UserMemory.expires_at.isnot(None), UserMemory.expires_at < datetime.utcnow())
            )
        )
        expired = result.scalars().all()
        for memory in expired:
            await db.delete(memory)
        await db.commit()
        return len(expired)
