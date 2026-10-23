import os

from redis import Redis
from rq import Queue, SimpleWorker, Worker

from backend.config.settings import settings


def main() -> None:
    connection = Redis.from_url(settings.REDIS_URL)
    queue = Queue(settings.MATCH_QUEUE_NAME, connection=connection)
    worker_type = SimpleWorker if os.name == "nt" else Worker
    worker = worker_type([queue], connection=connection)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()