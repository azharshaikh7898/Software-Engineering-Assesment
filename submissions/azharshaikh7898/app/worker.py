from redis import Redis
from rq import Queue, Worker

from . import embeddings
from .config import settings
from .jobs import QUEUE_NAME
from .logging_conf import setup_logging


def main() -> None:
    setup_logging()
    embeddings.warmup()  # load the model once, before jobs arrive
    conn = Redis.from_url(settings.redis_url)
    Worker([Queue(QUEUE_NAME, connection=conn)], connection=conn).work()


if __name__ == "__main__":
    main()
