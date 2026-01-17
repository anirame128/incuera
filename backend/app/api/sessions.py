"""Session management endpoints."""
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.session import Session as SessionModel
from app.models.event import Event
from app.models.project import Project
from app.auth.api_key import get_project_from_api_key
from app.schemas.session import (
    SessionStartRequest,
    SessionStartResponse,
    SessionHeartbeatRequest,
    SessionHeartbeatResponse,
    SessionEndRequest,
    SessionEndResponse,
    SessionListItem,
)
from app.utils.video_queue import queue_video_generation
from app.utils.url import decode_session_id
from app.utils.logger import logger
from app.utils.exceptions import not_found_error, forbidden_error, handle_database_error
from app.constants import SessionStatus

router = APIRouter(prefix="/api", tags=["sessions"])


@router.post("/sessions/start", response_model=SessionStartResponse)
async def start_session(
    request: SessionStartRequest,
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_from_api_key),
) -> SessionStartResponse:
    """
    Start a new session.
    
    This endpoint is called when the SDK initializes to create a session record.
    Requires API key to identify project.
    
    Args:
        request: Session start request with metadata
        db: Database session
        project: Project from API key
        
    Returns:
        Session start response
    """
    try:
        # Check if session already exists
        existing_session = db.query(SessionModel).filter(
            SessionModel.session_id == request.sessionId,
            SessionModel.project_id == project.id,
        ).first()
        
        if existing_session:
            # Update existing session metadata
            existing_session.user_id = request.userId or existing_session.user_id
            existing_session.user_email = request.userEmail or existing_session.user_email
            existing_session.url = request.metadata.url
            existing_session.referrer = request.metadata.referrer
            existing_session.user_agent = request.metadata.userAgent
            existing_session.screen_width = request.metadata.screen.get("width")
            existing_session.screen_height = request.metadata.screen.get("height")
            existing_session.viewport_width = request.metadata.viewport.get("width")
            existing_session.viewport_height = request.metadata.viewport.get("height")
            existing_session.updated_at = datetime.utcnow()
            
            db.commit()
            
            return SessionStartResponse(
                success=True,
                message="Session updated successfully",
                session_id=request.sessionId,
            )
        
        # Create new session with the project
        session = SessionModel(
            id=uuid.uuid4(),
            session_id=request.sessionId,
            project_id=project.id,  # Use actual project ID
            user_id=request.userId,
            user_email=request.userEmail,
            url=request.metadata.url,
            referrer=request.metadata.referrer,
            user_agent=request.metadata.userAgent,
            screen_width=request.metadata.screen.get("width"),
            screen_height=request.metadata.screen.get("height"),
            viewport_width=request.metadata.viewport.get("width"),
            viewport_height=request.metadata.viewport.get("height"),
            started_at=datetime.fromtimestamp(request.metadata.timestamp / 1000),
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return SessionStartResponse(
            success=True,
            message="Session started successfully",
            session_id=request.sessionId,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to start session {request.sessionId}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start session: {str(e)}",
        )


@router.get("/sessions", response_model=List[SessionListItem])
async def list_sessions(
    project_id: str = Query(..., description="Project ID"),
    db: Session = Depends(get_db),
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> List[SessionListItem]:
    """
    List all sessions for a project.
    
    Args:
        project_id: The project ID
        db: Database session
        api_key: Optional API key for authentication
        
    Returns:
        List of sessions
    """
    try:
        # Get project (using API key if provided, otherwise use project_id directly)
        if api_key:
            project = get_project_from_api_key(api_key, db)
            if str(project.id) != project_id:
                raise forbidden_error("Project ID mismatch")
        else:
            # For development, allow direct project_id access
            try:
                from app.utils.db import get_by_id
                project = get_by_id(db, Project, project_id, "Project not found")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid project ID format",
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


@router.post("/sessions/heartbeat", response_model=SessionHeartbeatResponse)
async def session_heartbeat(
    request: SessionHeartbeatRequest,
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_from_api_key),
) -> SessionHeartbeatResponse:
    """
    Receive heartbeat from SDK to keep session active.

    Updates last_heartbeat_at timestamp and event_count.
    
    Args:
        request: Heartbeat request with session ID and event count
        db: Database session
        project: Project from API key
        
    Returns:
        Heartbeat response
    """
    try:
        session = db.query(SessionModel).filter(
            SessionModel.session_id == request.sessionId,
            SessionModel.project_id == project.id,
        ).first()

        if not session:
            raise not_found_error("Session", request.sessionId)

        # Update heartbeat timestamp and event count
        session.last_heartbeat_at = datetime.utcnow()
        session.event_count = request.eventCount
        session.updated_at = datetime.utcnow()

        db.commit()

        return SessionHeartbeatResponse(
            success=True,
            message="Heartbeat received",
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to process heartbeat for session {request.sessionId}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process heartbeat: {str(e)}",
        )


@router.post("/sessions/end", response_model=SessionEndResponse)
async def end_session(
    request: SessionEndRequest,
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_from_api_key),
) -> SessionEndResponse:
    """
    Signal end of session from SDK.

    Marks session as completed and queues video generation.
    
    Args:
        request: Session end request
        db: Database session
        project: Project from API key
        
    Returns:
        Session end response
    """
    try:
        session = db.query(SessionModel).filter(
            SessionModel.session_id == request.sessionId,
            SessionModel.project_id == project.id,
        ).first()

        if not session:
            raise not_found_error("Session", request.sessionId)

        # Only process if session is still active
        if session.status == SessionStatus.ACTIVE:
            session.status = SessionStatus.COMPLETED
            session.ended_at = datetime.fromtimestamp(request.timestamp / 1000)
            session.event_count = request.finalEventCount

            # Calculate duration
            if session.started_at:
                duration_seconds = (session.ended_at - session.started_at).total_seconds()
                session.duration = int(duration_seconds)

            session.updated_at = datetime.utcnow()
            db.commit()

            # Queue video generation job
            video_queued = await queue_video_generation(request.sessionId)

            return SessionEndResponse(
                success=True,
                message="Session ended successfully",
                video_job_queued=video_queued,
            )

        return SessionEndResponse(
            success=True,
            message=f"Session already in status: {session.status}",
            video_job_queued=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end session: {str(e)}",
        )
