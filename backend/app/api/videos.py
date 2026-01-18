"""Video management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.session import Session as SessionModel
from app.auth.api_key import get_project_from_api_key
from app.schemas.session import VideoStatusResponse, SessionAnalysisResponse
from app.utils.video_queue import queue_video_generation, queue_video_analysis
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

        logger.info(f"[VIDEO_API] Getting video status for session {session_id}. Status: {session.status}, video_url: {session.video_url}, video_thumbnail_url: {session.video_thumbnail_url}")
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


@router.get("/sessions/{session_id}/analysis", response_model=SessionAnalysisResponse)
async def get_session_analysis(
    session_id: str,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Get Molmo 2 analysis results for a session.
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

        # Trigger analysis on-demand if analysis fields are empty
        from app.config import settings
        analysis_fields_empty = (
            not session.session_summary and
            not session.interaction_heatmap and
            not session.conversion_funnel and
            not session.error_events and
            not session.action_counts
        )
        
        # Check if error is from legacy code (old torch/transformers errors)
        has_legacy_error = False
        if session.molmo_analysis_metadata and isinstance(session.molmo_analysis_metadata, dict):
            error_msg = str(session.molmo_analysis_metadata.get("error", ""))
            has_legacy_error = any(keyword in error_msg.lower() for keyword in [
                "device_map", "accelerate", "torch", "transformers", "from_pretrained"
            ])
        
        # Allow retry if: fields are empty AND (status is not processing OR it's a failed legacy error)
        should_retry = (
            analysis_fields_empty and
            session.analysis_status != "processing" and
            (session.analysis_status != "failed" or has_legacy_error)
        )
        
        if (
            settings.molmo_enabled and
            session.video_url and
            (session.status == "ready" or session.video_url) and
            should_retry
        ):
            # Queue analysis in background (non-blocking) only if fields are empty
            try:
                from app.utils.video_queue import queue_video_analysis
                # Clear old error metadata if retrying a failed analysis
                if has_legacy_error or session.analysis_status == "failed":
                    session.molmo_analysis_metadata = None
                await queue_video_analysis(session.session_id)
                # Update status to processing
                session.analysis_status = "processing"
                db.commit()
                logger.info(f"[ANALYSIS_API] Triggered analysis on-demand for session {session.session_id} (fields were empty, legacy_error={has_legacy_error})")
            except Exception as e:
                logger.error(f"[ANALYSIS_API] Failed to trigger analysis on-demand: {e}")

        return SessionAnalysisResponse(
            session_id=session.session_id,
            analysis_status=session.analysis_status or "pending",
            analysis_completed_at=session.analysis_completed_at,
            session_summary=session.session_summary,
            interaction_heatmap=session.interaction_heatmap,
            conversion_funnel=session.conversion_funnel,
            error_events=session.error_events,
            action_counts=session.action_counts,
            molmo_analysis_metadata=session.molmo_analysis_metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis for session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analysis: {str(e)}",
        )


@router.post("/sessions/{session_id}/analyze")
async def trigger_analysis(
    session_id: str,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Manually trigger Molmo 2 analysis for a session video.
    Works for both new and pre-existing videos.
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

        # Check if video exists
        if not session.video_url:
            raise validation_error("Session has no video to analyze. Generate a video first.")

        # Check if analysis is enabled
        from app.config import settings
        if not settings.molmo_enabled:
            raise validation_error("Molmo 2 analysis is disabled")

        # Check if analysis is already processing or completed
        if session.analysis_status == "processing":
            return {
                "success": True,
                "message": "Analysis is already in progress",
                "analysis_status": "processing",
            }

        # Reset analysis status to pending (allows re-analysis)
        session.analysis_status = "pending"
        session.analysis_completed_at = None
        # Clear previous analysis results
        session.session_summary = None
        session.interaction_heatmap = None
        session.conversion_funnel = None
        session.error_events = None
        session.action_counts = None
        session.molmo_analysis_metadata = None
        db.commit()

        # Queue analysis job
        analysis_queued = await queue_video_analysis(decoded_session_id)

        if not analysis_queued:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to queue analysis job",
            )

        return {
            "success": True,
            "message": "Analysis job queued",
            "analysis_job_queued": analysis_queued,
            "analysis_status": "pending",
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to trigger analysis for session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger analysis: {str(e)}",
        )
