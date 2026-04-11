import redis
from app.core.config import settings

redis_client = redis.Redis.from_url(
    settings.redis_url,
    decode_responses=True,
)


def get_cached_answer(cache_key: str) -> str | None:
    return redis_client.get(cache_key)


def set_cached_answer(cache_key: str, value: str, ttl_seconds: int = 3600) -> None:
    redis_client.set(cache_key, value, ex=ttl_seconds)