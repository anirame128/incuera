"""Video generation queue utilities."""
import logging
from datetime import timedelta
from typing import Optional
from arq import create_pool
from app.workers.config import redis_settings
from app.utils.logger import logger


async def queue_video_generation(session_id: str) -> bool:
    """
    Queue a video generation job for the session.

    Args:
        session_id: The session ID to generate video for

    Returns:
        True if job was queued successfully, False otherwise
    """
    try:
        redis = await create_pool(redis_settings)
        await redis.enqueue_job("generate_session_video", session_id)
        await redis.close()
        return True
    except Exception as e:
        logger.error(f"Failed to queue video generation for session {session_id}: {e}", exc_info=True)
        return False


