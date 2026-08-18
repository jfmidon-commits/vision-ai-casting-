import json
import redis.asyncio as redis
from app.config import settings

class CacheService:
    def __init__(self):
        self._redis = None

    async def get_client(self):
        if self._redis is None:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    async def get(self, key: str):
        client = await self.get_client()
        value = await client.get(key)
        return json.loads(value) if value else None

    async def set(self, key: str, value, ttl: int = 3600):
        client = await self.get_client()
        await client.setex(key, ttl, json.dumps(value))

    async def delete(self, key: str):
        client = await self.get_client()
        await client.delete(key)

cache_service = CacheService()
