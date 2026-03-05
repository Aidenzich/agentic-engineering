from arq.connections import RedisSettings

from app.core.config import settings


async def startup(ctx):
    """Called when the worker starts."""
    pass


async def shutdown(ctx):
    """Called when the worker shuts down."""
    pass


def parse_redis_url(url: str) -> RedisSettings:
    """Parse redis URL into arq RedisSettings."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password,
        database=int(parsed.path.lstrip("/") or 0),
    )


class WorkerSettings:
    functions = []  # Will be populated as we add worker tasks
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = parse_redis_url(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 300
