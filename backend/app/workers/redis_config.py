"""Redis configuration for ARQ workers."""
from arq.connections import RedisSettings
from app.config import settings
from urllib.parse import urlparse


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
