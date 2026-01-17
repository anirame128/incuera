"""Video management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.session import Session as SessionModel
from app.models.project import Project
from app.auth.api_key import get_project_from_api_key
from app.schemas.session import VideoStatusResponse
from app.utils.video_queue import queue_video_generation
from app.utils.url import decode_session_id
from app.utils.logger import logger
from app.utils.exceptions import not_found_error, forbidden_error, validation_error
from app.constants import SessionStatus

router = APIRouter(prefix="/api", tags=["videos"])


@router.get("/sessions/{session_id}/video", response_model=VideoStatusResponse)
async def get_video_status(
    session_id: str,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Get video generation status and URLs for a session.
    """
    try:
        # URL decode the session_id in case it's encoded
        decoded_session_id = decode_session_id(session_id)

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

        logger.error(f"[VIDEO_API] Getting video status for session {session_id}. Status: {session.status}, video_url: {session.video_url}, video_thumbnail_url: {session.video_thumbnail_url}")
        return VideoStatusResponse(
            session_id=session.session_id,
            status=session.status or SessionStatus.ACTIVE,
            video_url=session.video_url,
            video_thumbnail_url=session.video_thumbnail_url,
            keyframes_url=session.keyframes_url,
            video_generated_at=session.video_generated_at,
            video_duration_ms=session.video_duration_ms,
            video_size_bytes=session.video_size_bytes,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get video status for session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get video status: {str(e)}",
        )


@router.post("/sessions/{session_id}/regenerate-video")
async def regenerate_video(
    session_id: str,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Manually trigger video regeneration for a session.
    """
    try:
        # URL decode the session_id in case it's encoded
        decoded_session_id = decode_session_id(session_id)

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

        # Check if session has events to generate video from
        if session.event_count == 0:
            raise validation_error("Session has no events to generate video from")

        # Update status to pending regeneration
        session.status = SessionStatus.COMPLETED  # Reset to completed so worker picks it up
        session.video_url = None
        session.video_thumbnail_url = None
        session.keyframes_url = None
        session.video_generated_at = None
        session.video_duration_ms = None
        session.video_size_bytes = None

        db.commit()

        # Queue video generation job
        video_queued = await queue_video_generation(decoded_session_id)

        return {
            "success": True,
            "message": "Video regeneration queued",
            "video_job_queued": video_queued,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to regenerate video for session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate video: {str(e)}",
        )
