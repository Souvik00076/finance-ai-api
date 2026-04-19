"""Singleton Redis manager for Redis operations."""

import logging
from typing import Any, Optional

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisManager:
    """Singleton async Redis client manager."""

    _instance: Optional["RedisManager"] = None
    _client: Optional[Redis] = None

    def __new__(cls) -> "RedisManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self) -> None:
        """Initialize the Redis connection."""
        if self._client is not None:
            return
        self._client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
        logger.info("Redis connection established")

    async def disconnect(self) -> None:
        """Close the Redis connection."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            RedisManager._instance = None
            logger.info("Redis connection closed")

    @property
    def client(self) -> Redis:
        """Return the underlying Redis client. Raises if not connected."""
        if self._client is None:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        return self._client

    # ---- Convenience wrappers ----

    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)

    async def set(
        self, key: str, value: Any, ex: Optional[int] = None
    ) -> None:
        response = await self.client.set(key, value, ex=ex)
        print(key)

    async def delete(self, key: str) -> None:
        await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self.client.exists(key))

    async def expire(self, key: str, seconds: int) -> None:
        await self.client.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        return await self.client.ttl(key)


redis_manager = RedisManager()
