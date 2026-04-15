import time
from collections.abc import Callable
from typing import TypeVar

from openai import (
    APIConnectionError,
    APITimeoutError,
    APIStatusError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from app.core.config import settings

T = TypeVar("T")

client = OpenAI(
    api_key=settings.openai_api_key,
    timeout=settings.openai_timeout_seconds,
    max_retries=0,
)


class OpenAIServiceError(RuntimeError):
    pass


RETRIABLE_EXCEPTIONS = (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)


def run_with_openai_retry(operation: Callable[[], T], action_name: str) -> T:
    attempts = max(settings.openai_retry_attempts, 1)
    base_delay = max(settings.openai_retry_base_delay_seconds, 0.1)

    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except RETRIABLE_EXCEPTIONS as exc:
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(base_delay * (2 ** (attempt - 1)))
        except APIStatusError as exc:
            last_error = exc
            if exc.status_code not in {408, 409, 429, 500, 502, 503, 504} or attempt == attempts:
                break
            time.sleep(base_delay * (2 ** (attempt - 1)))
        except Exception as exc:
            raise OpenAIServiceError(f"Unexpected error during {action_name}: {exc}") from exc

    raise OpenAIServiceError(f"OpenAI request failed during {action_name}: {last_error}") from last_error
