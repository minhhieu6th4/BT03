from typing import Callable, Optional

from fastapi import HTTPException
from redis import Redis
from redis.exceptions import RedisError
from rq import Queue

from backend.config.settings import settings


def enqueue_or_run_inline(
    task_path: str,
    args: tuple,
    inline_runner: Callable[[], None],
) -> Optional[str]:
    mode = settings.MATCH_EXECUTION_MODE.lower()
    if mode not in {"auto", "inline", "queued"}:
        raise RuntimeError("MATCH_EXECUTION_MODE must be auto, inline, or queued")
    if mode == "inline":
        if settings.ENVIRONMENT.lower() == "production":
            raise HTTPException(
                status_code=503,
                detail="Inline match execution is disabled in production.",
            )
        inline_runner()
        return None

    try:
        connection = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        try:
            connection.ping()
            queue = Queue(settings.MATCH_QUEUE_NAME, connection=connection)
            job = queue.enqueue(
                task_path,
                *args,
                job_timeout=settings.MATCH_JOB_TIMEOUT_SECONDS,
                result_ttl=3600,
                failure_ttl=86400,
            )
            return job.id
        finally:
            connection.close()
    except RedisError as exc:
        if mode == "auto" and settings.ENVIRONMENT.lower() != "production":
            inline_runner()
            return None
        raise HTTPException(
            status_code=503,
            detail="Hàng đợi trận đấu chưa sẵn sàng; vui lòng thử lại sau.",
        ) from exc