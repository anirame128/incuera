"""ARQ worker configuration."""
from arq.cron import cron
from app.workers.redis_config import redis_settings


async def startup(ctx):
    """Worker startup hook."""
    pass


async def shutdown(ctx):
    """Worker shutdown hook."""
    pass


class WorkerSettings:
    """ARQ worker settings."""

    # Functions will be set after module import to avoid circular dependencies
    functions = []
    cron_jobs = []

    on_startup = startup
    on_shutdown = shutdown

    redis_settings = redis_settings

    # Job configuration
    max_jobs = 5  # Max concurrent jobs
    job_timeout = 600  # 10 minute timeout for video generation
    keep_result = 3600  # Keep results for 1 hour
    retry_jobs = True
    max_tries = 3
    
    # Analysis job timeout (5 minutes for Molmo 2 analysis)
    # Note: analyze_session_video has its own 5-minute timeout in the task


# Lazy import of task functions after class definition to avoid circular imports
def _init_worker_settings():
    """Initialize worker settings with task functions."""
    from app.workers.tasks import generate_session_video, cleanup_stale_sessions, analyze_session_video
    
    WorkerSettings.functions = [
        generate_session_video,
        cleanup_stale_sessions,
        analyze_session_video,
    ]
    
    WorkerSettings.cron_jobs = [
        # Run cleanup every 5 minutes
        cron(
            cleanup_stale_sessions,
            minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55},
        ),
    ]


# Initialize settings when module is imported
_init_worker_settings()