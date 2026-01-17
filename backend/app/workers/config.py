"""ARQ worker configuration."""
from arq.connections import RedisSettings
from arq.cron import cron
from app.config import settings
from app.utils.logger import logger
from urllib.parse import urlparse

# Import the actual task functions
from app.workers.tasks import generate_session_video, cleanup_stale_sessions


def parse_redis_url(url: str) -> RedisSettings:
    """Parse Redis URL into RedisSettings."""
    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password,
        database=int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0,
    )


redis_settings = parse_redis_url(settings.redis_url)


async def startup(ctx):
    """Worker startup hook."""
    logger.info("ARQ worker starting up...")
    ctx["startup_complete"] = True


async def shutdown(ctx):
    """Worker shutdown hook."""
    logger.info("ARQ worker shutting down...")


class WorkerSettings:
    """ARQ worker settings."""

    # Use actual function references, not strings
    functions = [
        generate_session_video,
        cleanup_stale_sessions,
    ]

    cron_jobs = [
        # Run cleanup every 5 minutes
        cron(
            cleanup_stale_sessions,
            minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55},
        ),
    ]

    on_startup = startup
    on_shutdown = shutdown

    redis_settings = redis_settings

    # Job configuration
    max_jobs = 5  # Max concurrent jobs
    job_timeout = 600  # 10 minute timeout for video generation
    keep_result = 3600  # Keep results for 1 hour
    retry_jobs = True
    max_tries = 3
