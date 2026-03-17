"""Async Redis client wrapper (aioredis via redis-py)."""
from typing import Optional
import redis.asyncio as aioredis
from app.config import settings

_redis: Optional[aioredis.Redis] = None


async def init_redis() -> None:
    global _redis
    _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


async def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialised – call init_redis() first")
    return _redis
