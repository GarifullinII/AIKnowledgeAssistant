from rq import Worker

from app.core.config import settings
from app.db.database import ensure_runtime_schema
from app.services.cache_service import queue_redis_client


def main() -> None:
    ensure_runtime_schema()
    worker = Worker([settings.document_queue_name], connection=queue_redis_client)
    worker.work()


if __name__ == "__main__":
    main()
