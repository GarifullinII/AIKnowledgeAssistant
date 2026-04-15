import redis
from app.core.config import settings

redis_client = redis.Redis.from_url(
    settings.redis_url,
    decode_responses=True,
)

queue_redis_client = redis.Redis.from_url(
    settings.redis_url,
    decode_responses=False,
)


def get_cached_answer(cache_key: str) -> str | None:
    return redis_client.get(cache_key)


def set_cached_answer(cache_key: str, value: str, ttl_seconds: int = 3600) -> None:
    redis_client.set(cache_key, value, ex=ttl_seconds)


def get_selected_document_id(chat_id: int) -> str | None:
    return redis_client.get(f"telegram:selected_document:{chat_id}")


def set_selected_document_id(chat_id: int, document_id: str) -> None:
    redis_client.set(f"telegram:selected_document:{chat_id}", document_id)


def clear_selected_document_id(chat_id: int) -> None:
    redis_client.delete(f"telegram:selected_document:{chat_id}")
