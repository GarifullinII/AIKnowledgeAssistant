from rq import Queue, Retry

from app.core.config import settings
from app.services.cache_service import queue_redis_client


def get_document_queue() -> Queue:
    return Queue(name=settings.document_queue_name, connection=queue_redis_client)


def enqueue_document_processing(document_id: str) -> str:
    job = get_document_queue().enqueue(
        "app.services.document_service.process_document",
        document_id,
        retry=Retry(max=3, interval=[10, 30, 60]),
        job_timeout=900,
        result_ttl=3600,
        failure_ttl=86400,
    )
    return job.id
