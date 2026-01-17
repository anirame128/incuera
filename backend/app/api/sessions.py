"""Session management endpoints."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header, Request

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.session import Session as SessionModel
from app.models.event import Event
from app.models.project import Project
from app.auth.api_key import get_project_from_api_key, get_project_from_api_key_value
from app.utils.exceptions import not_found_error, forbidden_error
from app.schemas.session import (
    SessionStartRequest,
    SessionStartResponse,
    SessionEndRequest,
    SessionEndResponse,
    SessionListItem,
)
from app.utils.video_queue import queue_video_generation
from app.utils.url import decode_session_id
from app.utils.logger import logger
from app.utils.exceptions import not_found_error, forbidden_error, handle_database_error
from app.utils.pending_sessions import store_pending_session, delete_pending_session, get_pending_events, delete_pending_events, acquire_session_end_lock, release_session_end_lock
from app.constants import SessionStatus

router = APIRouter(prefix="/api", tags=["sessions"])


@router.post("/sessions/start", response_model=SessionStartResponse)
async def start_session(
    request: SessionStartRequest,
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_from_api_key),
) -> SessionStartResponse:
    """
    Register session metadata.

    This endpoint stores session metadata temporarily in Redis. The actual session
    record is only created when the session ends via /api/sessions/end AND the
    session duration is >= 30 seconds. This ensures we only track meaningful sessions.

    Args:
        request: Session start request with metadata
        db: Database session
        project: Project from API key

    Returns:
        Session start response
    """
    try:
        # Store metadata in Redis (session will be created when it ends and is >= 30s)
        metadata = {
            "userId": request.userId,
            "userEmail": request.userEmail,
            "url": request.metadata.url,
            "referrer": request.metadata.referrer,
            "userAgent": request.metadata.userAgent,
            "screen": request.metadata.screen,
            "viewport": request.metadata.viewport,
            "timestamp": request.metadata.timestamp,
        }

        stored = await store_pending_session(
            session_id=request.sessionId,
            project_id=str(project.id),
            metadata=metadata,
        )

        if not stored:
            logger.error(f"Failed to store pending session metadata in Redis for {request.sessionId}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store session metadata. Please try again.",
            )

        logger.info(f"Stored pending session metadata for {request.sessionId}")

        return SessionStartResponse(
            success=True,
            message="Session metadata registered (session will be created if duration >= 30s)",
            session_id=request.sessionId,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register session {request.sessionId}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register session: {str(e)}",
        )


@router.get("/sessions", response_model=List[SessionListItem])
async def list_sessions(
    project_slug: str = Query(..., description="Project slug"),
    db: Session = Depends(get_db),
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    request: Request = None,
) -> List[SessionListItem]:
    """
    List all sessions for a project.
    
    Args:
        project_slug: The project slug
        db: Database session
        api_key: Optional API key for authentication
        request: Request object for headers
        
    Returns:
        List of sessions
    """
    try:
        # Get project (using API key if provided, otherwise use slug with user_id)
        if api_key:
            project = get_project_from_api_key(api_key, db)
            if project.slug != project_slug:
                raise forbidden_error("Project slug mismatch")
        else:
            # Require user_id for authorization
            user_id = request.headers.get("X-User-ID")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User ID required for authorization",
                )
            try:
                project = db.query(Project).filter(
                    Project.slug == project_slug,
                    Project.user_id == uuid.UUID(user_id)
                ).first()
                if not project:
                    raise not_found_error("Project")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid user ID format",
                )
        
        sessions = db.query(SessionModel).filter(
            SessionModel.project_id == project.id
        ).order_by(SessionModel.started_at.desc()).limit(100).all()
        
        return [SessionListItem.from_orm(session) for session in sessions]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch sessions for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sessions: {str(e)}",
        )


@router.get("/sessions/{session_id}/events")
async def get_session_events(
    session_id: str,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> dict:
    """
    Get all events for a specific session.
    
    Args:
        session_id: The session ID
        db: Database session
        api_key: Optional API key for authentication
        
    Returns:
        Dictionary with session info and events
    """
    try:
        # URL decode the session_id in case it's encoded
        decoded_session_id = decode_session_id(session_id)
        
        # Find the session first
        session = db.query(SessionModel).filter(
            SessionModel.session_id == decoded_session_id,
        ).first()
        
        if not session:
            raise not_found_error("Session", decoded_session_id)
        
        # Verify project access if API key provided
        if api_key:
            project = get_project_from_api_key(api_key, db)
            if session.project_id != project.id:
                raise forbidden_error("Access denied")
        
        # Get all events for this session, ordered by sequence
        events = db.query(Event).filter(
            Event.session_id == session.id
        ).order_by(Event.sequence_number.asc()).all()
        
        return {
            "session": {
                "id": str(session.id),
                "session_id": session.session_id,
                "url": session.url,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "event_count": session.event_count,
            },
            "events": [
                {
                    "id": str(event.id),
                    "event_data": event.event_data,
                    "event_type": event.event_type,
                    "event_timestamp": event.event_timestamp,
                    "sequence_number": event.sequence_number,
                }
                for event in events
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch events for session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch events: {str(e)}",
        )


@router.post("/sessions/end", response_model=SessionEndResponse)
async def end_session(
    request: SessionEndRequest,
    db: Session = Depends(get_db),
    api_key_header: Optional[str] = Header(None, alias="X-API-Key"),
) -> SessionEndResponse:
    """
    Signal end of session from SDK.
    
    Only processes sessions that are >= 30 seconds long.
    Immediately marks session as COMPLETED and queues video generation.

    Accepts API key from either header (X-API-Key) or request body (apiKey field).
    This is necessary because sendBeacon doesn't support custom headers.

    Args:
        request: Session end request
        db: Database session
        api_key_header: Optional API key from header

    Returns:
        Session end response
    """
    try:
        # Get API key from header or body (sendBeacon can't send headers)
        api_key = api_key_header or request.apiKey
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is required (in header or body)",
            )

        project = get_project_from_api_key_value(api_key, db)

        session = db.query(SessionModel).filter(
            SessionModel.session_id == request.sessionId,
            SessionModel.project_id == project.id,
        ).first()

        # If session already exists and is completed/processing/ready, this is a duplicate request - return success
        if session and session.status in [SessionStatus.COMPLETED, SessionStatus.PROCESSING, SessionStatus.READY]:
            return SessionEndResponse(
                success=True,
                message="Session already ended",
                video_job_queued=session.status != SessionStatus.COMPLETED or session.video_url is not None,
            )

        # If session doesn't exist in DB, check Redis for pending data
        if not session:
            from app.utils.pending_sessions import get_pending_session, get_pending_events, delete_pending_session, delete_pending_events
            
            # Acquire lock to prevent concurrent processing
            lock_acquired = await acquire_session_end_lock(request.sessionId)
            if not lock_acquired:
                # Another request is already processing this session end - return success
                return SessionEndResponse(
                    success=True,
                    message="Session end already being processed",
                    video_job_queued=False,
                )
            
            try:
                pending = await get_pending_session(request.sessionId)
                if not pending:
                    # No pending data, just clean up
                    await delete_pending_events(request.sessionId)
                    return SessionEndResponse(
                        success=True,
                        message="Session ended (no data)",
                        video_job_queued=False,
                    )

                # Get pending events
                pending_events = await get_pending_events(request.sessionId)
                
                # Calculate duration from metadata timestamp to end timestamp
                metadata = pending.get("metadata", {})
                start_timestamp = metadata.get("timestamp", 0)
                end_timestamp = request.timestamp
                
                if start_timestamp > 0:
                    duration_seconds = (end_timestamp - start_timestamp) / 1000  # Convert ms to seconds
                    
                    # Only create session if duration >= 30 seconds
                    if duration_seconds >= 30:
                        # Check again if session exists (might have been created by concurrent request)
                        session = db.query(SessionModel).filter(
                            SessionModel.session_id == request.sessionId,
                            SessionModel.project_id == project.id,
                        ).first()
                        
                        if session:
                            # Session already exists - update it
                            session.ended_at = datetime.fromtimestamp(end_timestamp / 1000, tz=timezone.utc)
                            session.duration = int(duration_seconds)
                            session.event_count = len(pending_events)
                            session.status = SessionStatus.COMPLETED
                            session.updated_at = datetime.utcnow()
                            db.commit()
                            
                            # Clean up Redis
                            await delete_pending_session(request.sessionId)
                            await delete_pending_events(request.sessionId)
                            
                            # Queue video generation
                            video_queued = await queue_video_generation(request.sessionId)
                            
                            return SessionEndResponse(
                                success=True,
                                message="Session updated and video generation queued",
                                video_job_queued=video_queued,
                            )
                        
                        # Create session from pending metadata
                        session = SessionModel(
                            id=uuid.uuid4(),
                            session_id=request.sessionId,
                            project_id=project.id,
                            user_id=metadata.get("userId"),
                            user_email=metadata.get("userEmail"),
                            url=metadata.get("url", ""),
                            referrer=metadata.get("referrer"),
                            user_agent=metadata.get("userAgent", ""),
                            screen_width=metadata.get("screen", {}).get("width"),
                            screen_height=metadata.get("screen", {}).get("height"),
                            viewport_width=metadata.get("viewport", {}).get("width"),
                            viewport_height=metadata.get("viewport", {}).get("height"),
                            started_at=datetime.fromtimestamp(start_timestamp / 1000, tz=timezone.utc),
                            ended_at=datetime.fromtimestamp(end_timestamp / 1000, tz=timezone.utc),
                            duration=int(duration_seconds),
                            event_count=len(pending_events),
                            status=SessionStatus.COMPLETED,
                        )
                        
                        try:
                            db.add(session)
                            db.flush()  # Get session ID
                            
                            # Insert all events
                            if pending_events:
                                events_to_insert = []
                                for idx, event_data in enumerate(pending_events):
                                    if not isinstance(event_data, dict):
                                        continue
                                    
                                    event = Event(
                                        session_id=session.id,
                                        event_data=event_data,
                                        event_type=event_data.get("type", "unknown"),
                                        event_timestamp=event_data.get("timestamp", 0),
                                        sequence_number=idx,
                                    )
                                    events_to_insert.append(event)
                                
                                if events_to_insert:
                                    db.bulk_save_objects(events_to_insert)
                            
                            db.commit()
                        except Exception as e:
                            db.rollback()
                            # Check if it's a duplicate key error
                            is_duplicate = False
                            if isinstance(e, IntegrityError):
                                is_duplicate = True
                            elif hasattr(e, 'orig') and hasattr(e.orig, 'pgcode'):
                                # Check for PostgreSQL unique violation error code
                                if e.orig.pgcode == '23505':  # Unique violation
                                    is_duplicate = True
                            
                            if is_duplicate:
                                # Session might have been created by concurrent request - check again
                                session = db.query(SessionModel).filter(
                                    SessionModel.session_id == request.sessionId,
                                    SessionModel.project_id == project.id,
                                ).first()
                                
                                if session:
                                    # Session exists - update it
                                    session.ended_at = datetime.fromtimestamp(end_timestamp / 1000, tz=timezone.utc)
                                    session.duration = int(duration_seconds)
                                    session.event_count = len(pending_events)
                                    session.status = SessionStatus.COMPLETED
                                    session.updated_at = datetime.utcnow()
                                    db.commit()
                                    
                                    # Clean up Redis
                                    await delete_pending_session(request.sessionId)
                                    await delete_pending_events(request.sessionId)
                                    
                                    # Queue video generation
                                    video_queued = await queue_video_generation(request.sessionId)
                                    
                                    return SessionEndResponse(
                                        success=True,
                                        message="Session updated and video generation queued",
                                        video_job_queued=video_queued,
                                    )
                            
                            # Re-raise if it's not a duplicate key error or session doesn't exist
                            raise
                        
                        # Clean up Redis (only if session was successfully created)
                        await delete_pending_session(request.sessionId)
                        await delete_pending_events(request.sessionId)
                        
                        # Queue video generation
                        video_queued = await queue_video_generation(request.sessionId)
                        
                        return SessionEndResponse(
                            success=True,
                            message="Session created and video generation queued",
                            video_job_queued=video_queued,
                        )
                    else:
                        # Session too short - discard everything
                        await delete_pending_session(request.sessionId)
                        await delete_pending_events(request.sessionId)
                        
                        return SessionEndResponse(
                            success=True,
                            message="Session ended (duration < 30s, discarded)",
                            video_job_queued=False,
                        )
                else:
                    # No start timestamp - discard
                    await delete_pending_session(request.sessionId)
                    await delete_pending_events(request.sessionId)
                    
                    return SessionEndResponse(
                        success=True,
                        message="Session ended (no start time)",
                        video_job_queued=False,
                    )
            finally:
                # Always release the lock
                await release_session_end_lock(request.sessionId)

        # Session already exists in DB - process normally
        if session.status == SessionStatus.ACTIVE:
            session.ended_at = datetime.fromtimestamp(request.timestamp / 1000, tz=timezone.utc)
            session.event_count = request.finalEventCount

            # Calculate duration
            if session.started_at:
                duration_seconds = (session.ended_at - session.started_at).total_seconds()
                session.duration = int(duration_seconds)
                
                # Only process if session is >= 30 seconds
                if session.duration >= 30:
                    session.status = SessionStatus.COMPLETED
                    session.updated_at = datetime.utcnow()
                    db.commit()

                    # Queue video generation immediately
                    video_queued = await queue_video_generation(request.sessionId)

                    return SessionEndResponse(
                        success=True,
                        message="Session ended and video generation queued",
                        video_job_queued=video_queued,
                    )
                else:
                    # Session too short, mark as completed but don't queue video
                    session.status = SessionStatus.COMPLETED
                    session.updated_at = datetime.utcnow()
                    db.commit()

                    return SessionEndResponse(
                        success=True,
                        message="Session ended (duration < 30s, no video generated)",
                        video_job_queued=False,
                    )
            else:
                # No start time, can't calculate duration - don't process
                return SessionEndResponse(
                    success=True,
                    message="Session ended (no start time)",
                    video_job_queued=False,
                )

        # Session already completed or in another state
        return SessionEndResponse(
            success=True,
            message=f"Session already in status: {session.status}",
            video_job_queued=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to end session {request.sessionId}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end session: {str(e)}",
        )
