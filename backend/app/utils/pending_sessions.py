"""Pending session metadata and events storage using Redis.

Sessions are only created in the database when:
1. The session ends (via /api/sessions/end)
2. AND the session duration is >= 30 seconds

This module stores session metadata and events temporarily in Redis until the session ends.
If the session is < 30 seconds, everything is discarded. If >= 30 seconds, the session
and all events are persisted to the database.
"""
import json
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import redis.asyncio as redis
from app.config import settings
from app.utils.logger import logger

# TTL for pending session metadata (10 minutes)
PENDING_SESSION_TTL = 600


@asynccontextmanager
async def get_redis_client():
    """Get async Redis client with proper cleanup."""
    client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield client
    finally:
        await client.close()


def _pending_key(session_id: str) -> str:
    """Generate Redis key for pending session metadata."""
    return f"pending_session:{session_id}"


def _pending_events_key(session_id: str) -> str:
    """Generate Redis key for pending session events."""
    return f"pending_events:{session_id}"


def _processing_lock_key(session_id: str) -> str:
    """Generate Redis key for session end processing lock."""
    return f"session_end_processing:{session_id}"


async def store_pending_session(
    session_id: str,
    project_id: str,
    metadata: Dict[str, Any],
) -> bool:
    """
    Store pending session metadata in Redis.

    Called when /sessions/start is invoked. The actual session
    will be created when first events arrive.

    Args:
        session_id: The SDK-generated session ID
        project_id: The project UUID (string)
        metadata: Session metadata from SDK

    Returns:
        True if stored successfully, False otherwise
    """
    try:
        async with get_redis_client() as client:
            key = _pending_key(session_id)

            data = {
                "session_id": session_id,
                "project_id": project_id,
                "metadata": metadata,
            }

            await client.setex(key, PENDING_SESSION_TTL, json.dumps(data))
            logger.debug(f"Stored pending session {session_id} in Redis")
            return True
    except Exception as e:
        logger.error(f"Failed to store pending session {session_id}: {e}", exc_info=True)
        return False


async def get_pending_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve pending session metadata from Redis.

    Args:
        session_id: The SDK-generated session ID

    Returns:
        Session metadata dict if found, None otherwise
    """
    try:
        async with get_redis_client() as client:
            key = _pending_key(session_id)
            data = await client.get(key)

            if data:
                logger.debug(f"Found pending session {session_id} in Redis")
                return json.loads(data)

            logger.debug(f"No pending session {session_id} found in Redis")
            return None
    except Exception as e:
        logger.error(f"Failed to get pending session {session_id}: {e}", exc_info=True)
        return None


async def delete_pending_session(session_id: str) -> bool:
    """
    Delete pending session metadata from Redis.

    Called after session is created in the database.

    Args:
        session_id: The SDK-generated session ID

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        async with get_redis_client() as client:
            key = _pending_key(session_id)
            await client.delete(key)
            logger.debug(f"Deleted pending session {session_id} from Redis")
            return True
    except Exception as e:
        logger.error(f"Failed to delete pending session {session_id}: {e}", exc_info=True)
        return False




async def append_pending_events(session_id: str, events: list) -> bool:
    """
    Append events to pending session events in Redis.

    Events are stored in a list and will be persisted to database
    only if session duration >= 30 seconds when session ends.

    Args:
        session_id: The SDK-generated session ID
        events: List of event dictionaries

    Returns:
        True if stored successfully, False otherwise
    """
    try:
        async with get_redis_client() as client:
            key = _pending_events_key(session_id)
            
            # Append events to list (using Redis list)
            for event in events:
                await client.rpush(key, json.dumps(event))
            
            # Set TTL on the list
            await client.expire(key, PENDING_SESSION_TTL)
            
            logger.debug(f"Appended {len(events)} events to pending session {session_id}")
            return True
    except Exception as e:
        logger.error(f"Failed to append pending events for {session_id}: {e}", exc_info=True)
        return False


async def get_pending_events(session_id: str) -> list:
    """
    Retrieve all pending events for a session from Redis.

    Args:
        session_id: The SDK-generated session ID

    Returns:
        List of event dictionaries
    """
    try:
        async with get_redis_client() as client:
            key = _pending_events_key(session_id)
            events_data = await client.lrange(key, 0, -1)
            
            if events_data:
                events = [json.loads(event_str) for event_str in events_data]
                logger.debug(f"Retrieved {len(events)} pending events for {session_id}")
                return events
            
            return []
    except Exception as e:
        logger.error(f"Failed to get pending events for {session_id}: {e}", exc_info=True)
        return []


async def delete_pending_events(session_id: str) -> bool:
    """
    Delete pending events from Redis.

    Called after events are persisted to database or session is discarded.

    Args:
        session_id: The SDK-generated session ID

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        async with get_redis_client() as client:
            key = _pending_events_key(session_id)
            await client.delete(key)
            logger.debug(f"Deleted pending events for {session_id}")
            return True
    except Exception as e:
        logger.error(f"Failed to delete pending events for {session_id}: {e}", exc_info=True)
        return False


async def acquire_session_end_lock(session_id: str, ttl_seconds: int = 30) -> bool:
    """
    Acquire a lock for processing session end to prevent concurrent processing.
    
    Args:
        session_id: The SDK-generated session ID
        ttl_seconds: Lock TTL in seconds (default 30)
        
    Returns:
        True if lock was acquired, False if already locked
    """
    try:
        async with get_redis_client() as client:
            key = _processing_lock_key(session_id)
            # Use SET with NX (only if not exists) and EX (expiration)
            result = await client.set(key, "1", ex=ttl_seconds, nx=True)
            return result is True
    except Exception as e:
        logger.error(f"Failed to acquire session end lock for {session_id}: {e}", exc_info=True)
        return False


async def release_session_end_lock(session_id: str) -> bool:
    """
    Release the session end processing lock.
    
    Args:
        session_id: The SDK-generated session ID
        
    Returns:
        True if released successfully, False otherwise
    """
    try:
        async with get_redis_client() as client:
            key = _processing_lock_key(session_id)
            await client.delete(key)
            return True
    except Exception as e:
        logger.error(f"Failed to release session end lock for {session_id}: {e}", exc_info=True)
        return False
