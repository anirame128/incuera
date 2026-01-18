"""ARQ background tasks for video generation."""
import os
import shutil
import tempfile
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from sqlalchemy.orm import sessionmaker
import httpx

from app.database import engine
from app.models.session import Session
from app.models.event import Event
from app.services.video import VideoGenerator
from app.services.storage import storage_service
from app.services.molmo_analyzer import MolmoAnalyzer
from app.utils.logger import logger
from app.utils.video_queue import queue_video_analysis
from app.constants import SessionStatus
from app.config import settings


def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


# Reuse database engine from app.database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def generate_session_video(ctx: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """
    Generate video for a completed session.

    Args:
        ctx: ARQ context
        session_id: The session_id (SDK-generated ID) to process

    Returns:
        Dict with success status and details
    """
    logger.info(f"[VIDEO_GEN] Starting video generation for session {session_id}")
    db = SessionLocal()
    temp_dir = None

    try:
        # Find the session
        session = db.query(Session).filter(
            Session.session_id == session_id
        ).first()

        if not session:
            logger.error(f"[VIDEO_GEN] Session not found: {session_id}")
            return {"success": False, "error": f"Session not found: {session_id}"}

        logger.info(f"[VIDEO_GEN] Found session {session_id}, status: {session.status}, project_id: {session.project_id}")

        # Check if session should be processed
        if session.status not in [SessionStatus.COMPLETED, SessionStatus.FAILED]:
            logger.error(f"[VIDEO_GEN] Session {session_id} status is {session.status}, not eligible for video generation")
            return {
                "success": False,
                "error": f"Session status is {session.status}, not eligible for video generation",
            }

        # Update status to processing
        session.status = SessionStatus.PROCESSING
        db.commit()
        logger.info(f"[VIDEO_GEN] Updated session {session_id} status to PROCESSING")

        # Get all events for the session
        events = db.query(Event).filter(
            Event.session_id == session.id
        ).order_by(Event.sequence_number.asc()).all()

        if not events:
            logger.error(f"[VIDEO_GEN] No events found for session {session_id}")
            session.status = SessionStatus.FAILED
            db.commit()
            return {"success": False, "error": "No events found for session"}

        logger.info(f"[VIDEO_GEN] Found {len(events)} events for session {session_id}")

        # Extract event data
        event_data = [event.event_data for event in events]

        # Create temporary output directory
        temp_dir = tempfile.mkdtemp(prefix=f"video_output_{session_id}_")
        logger.info(f"[VIDEO_GEN] Created temp directory: {temp_dir}")

        # Generate video
        logger.info(f"[VIDEO_GEN] Starting video generation with {len(event_data)} events")
        generator = VideoGenerator()
        result = await generator.generate_video(
            events=event_data,
            output_dir=temp_dir,
            session_id=session_id,
        )

        if not result.success:
            logger.error(f"[VIDEO_GEN] Video generation failed for session {session_id}: {result.error}")
            session.status = SessionStatus.FAILED
            db.commit()
            return {"success": False, "error": result.error}

        logger.info(f"[VIDEO_GEN] Video generation successful for session {session_id}. Video path: {result.video_path}, Duration: {result.duration_ms}ms, Size: {result.size_bytes} bytes")

        # Upload to Supabase Storage
        project_id = str(session.project_id)
        logger.info(f"[VIDEO_GEN] Starting uploads for session {session_id}, project_id: {project_id}")
        
        upload_success = True
        upload_errors = []

        # Upload video
        if result.video_path:
            logger.info(f"[VIDEO_GEN] Uploading video from {result.video_path}")
            video_result = await storage_service.upload_video(
                result.video_path, project_id, session_id
            )
            if video_result.success:
                logger.info(f"[VIDEO_GEN] Video upload successful. URL: {video_result.url}")
                session.video_url = video_result.url
            else:
                logger.error(f"[VIDEO_GEN] Video upload failed: {video_result.error}")
                upload_success = False
                upload_errors.append(f"Video upload failed: {video_result.error}")
        else:
            logger.error(f"[VIDEO_GEN] No video path in result, skipping video upload")
        
        # Upload thumbnail
        if result.thumbnail_path and upload_success:
            logger.info(f"[VIDEO_GEN] Uploading thumbnail from {result.thumbnail_path}")
            thumb_result = await storage_service.upload_thumbnail(
                result.thumbnail_path, project_id, session_id
            )
            if thumb_result.success:
                logger.info(f"[VIDEO_GEN] Thumbnail upload successful. URL: {thumb_result.url}")
                session.video_thumbnail_url = thumb_result.url
            else:
                logger.warning(f"[VIDEO_GEN] Thumbnail upload failed: {thumb_result.error} (non-critical)")
            # Thumbnail upload failure is non-critical, continue without it
        else:
            if not result.thumbnail_path:
                logger.warning(f"[VIDEO_GEN] No thumbnail path in result, skipping thumbnail upload")
            if not upload_success:
                logger.warning(f"[VIDEO_GEN] Skipping thumbnail upload due to previous upload failure")
        
        # Upload keyframes
        if result.keyframes_path and upload_success:
            logger.info(f"[VIDEO_GEN] Uploading keyframes from {result.keyframes_path}")
            keyframes_result = await storage_service.upload_keyframes(
                result.keyframes_path, project_id, session_id
            )
            if keyframes_result.success:
                logger.info(f"[VIDEO_GEN] Keyframes upload successful. URL: {keyframes_result.url}")
                session.keyframes_url = keyframes_result.url
            else:
                logger.warning(f"[VIDEO_GEN] Keyframes upload failed: {keyframes_result.error} (non-critical)")
            # Keyframes upload failure is non-critical, continue without it
        else:
            if not result.keyframes_path:
                logger.warning(f"[VIDEO_GEN] No keyframes path in result, skipping keyframes upload")
            if not upload_success:
                logger.warning(f"[VIDEO_GEN] Skipping keyframes upload due to previous upload failure")

        if not upload_success:
            # Re-fetch session to avoid stale data issues
            session = db.query(Session).filter(Session.session_id == session_id).first()
            if session and session.status == SessionStatus.PROCESSING:
                session.status = SessionStatus.FAILED
                db.commit()
            error_msg = "; ".join(upload_errors)
            logger.error(f"[VIDEO_GEN] Upload failed for session {session_id}: {error_msg}")
            return {"success": False, "error": error_msg}

        # Store URLs before expiring session object
        video_url = session.video_url
        thumbnail_url = session.video_thumbnail_url
        keyframes_url = session.keyframes_url
        logger.info(f"[VIDEO_GEN] Stored URLs before re-fetch: video_url={video_url}, thumbnail_url={thumbnail_url}, keyframes_url={keyframes_url}")

        # Re-fetch session to check if it was reactivated during video generation
        db.expire_all()  # Clear cached objects
        session = db.query(Session).filter(Session.session_id == session_id).first()

        if not session:
            logger.error(f"[VIDEO_GEN] Session {session_id} no longer exists after video generation")
            return {"success": False, "error": "Session no longer exists"}

        # Check if session was reactivated while we were generating video
        if session.status != SessionStatus.PROCESSING:
            logger.error(
                f"[VIDEO_GEN] Session {session_id} was reactivated during video generation "
                f"(status: {session.status}). Video generated but not marking as READY."
            )
            # Don't update status - session continues recording
            # The video was generated but will be overwritten when session finally ends
            return {
                "success": True,
                "session_id": session_id,
                "message": "Video generated but session was reactivated, will regenerate on final end",
            }

        # Update session with video details (including URLs that were set before re-fetch)
        logger.info(f"[VIDEO_GEN] Updating session {session_id} to READY status. video_url: {video_url}, thumbnail_url: {thumbnail_url}, keyframes_url: {keyframes_url}, duration_ms: {result.duration_ms}, size_bytes: {result.size_bytes}")
        session.status = SessionStatus.READY
        session.video_url = video_url
        session.video_thumbnail_url = thumbnail_url
        session.keyframes_url = keyframes_url
        session.video_generated_at = utc_now()
        session.video_duration_ms = result.duration_ms
        session.video_size_bytes = result.size_bytes
        db.commit()
        logger.info(f"[VIDEO_GEN] Committed session update. Final video_url: {session.video_url}")
        logger.info(f"[VIDEO_GEN] Successfully completed video generation for session {session_id}")

        # Note: Analysis will be triggered on-demand when analysis data is requested
        # and fields are empty (see /api/sessions/{session_id}/analysis endpoint)

        return {
            "success": True,
            "session_id": session_id,
            "video_url": session.video_url,
            "duration_ms": result.duration_ms,
            "size_bytes": result.size_bytes,
        }

    except Exception as e:
        # Mark session as failed
        logger.error(f"[VIDEO_GEN] Exception generating video for session {session_id}: {e}", exc_info=True)
        try:
            session = db.query(Session).filter(
                Session.session_id == session_id
            ).first()
            if session:
                session.status = SessionStatus.FAILED
                db.commit()
                logger.error(f"[VIDEO_GEN] Marked session {session_id} as FAILED due to exception")
        except Exception as db_error:
            logger.error(f"[VIDEO_GEN] Failed to update session status after error: {db_error}")

        return {"success": False, "error": str(e)}

    finally:
        db.close()
        # Cleanup temp directory
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


async def analyze_session_video(ctx: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """
    Analyze session video using Molmo 2.

    Args:
        ctx: ARQ context
        session_id: The session_id (SDK-generated ID) to analyze

    Returns:
        Dict with success status and details
    """
    if not settings.molmo_enabled:
        logger.info(f"[MOLMO] Analysis disabled, skipping session {session_id}")
        return {"success": False, "error": "Analysis is disabled"}

    logger.info(f"[MOLMO] Starting analysis for session {session_id}")
    db = SessionLocal()

    try:
        # Find the session
        session = db.query(Session).filter(
            Session.session_id == session_id
        ).first()

        if not session:
            logger.error(f"[MOLMO] Session not found: {session_id}")
            return {"success": False, "error": f"Session not found: {session_id}"}

        # Check if video exists
        if not session.video_url:
            logger.error(f"[MOLMO] No video URL for session {session_id}")
            return {"success": False, "error": "No video URL available"}

        # Check video duration
        if session.video_duration_ms and session.video_duration_ms > settings.molmo_max_video_duration_seconds * 1000:
            logger.error(f"[MOLMO] Video too long ({session.video_duration_ms}ms), skipping analysis")
            session.analysis_status = "failed"
            session.molmo_analysis_metadata = {"error": "Video duration exceeds maximum"}
            db.commit()
            return {"success": False, "error": "Video duration exceeds maximum"}

        # Update status to processing
        session.analysis_status = "processing"
        db.commit()
        logger.info(f"[MOLMO] Updated session {session_id} analysis status to processing")

        # Use the video URL directly (must be publicly accessible for OpenRouter API)
        video_url = session.video_url
        if not video_url:
            raise Exception("Video URL required for analysis")

        # Initialize OpenRouter API analyzer
        analyzer = MolmoAnalyzer()
        logger.info(f"[MOLMO] Using OpenRouter API analyzer with video URL: {video_url}")
        
        # Run analysis with timeout (5 minutes should be enough for API)
        try:
            analysis_results = await asyncio.wait_for(
                asyncio.to_thread(analyzer.analyze, video_url),
                timeout=300.0  # 5 minutes
            )
        except asyncio.TimeoutError:
            raise Exception("Analysis timed out after 5 minutes")

        # Store results in database
        session.analysis_status = "completed"
        session.analysis_completed_at = utc_now()
        session.session_summary = analysis_results.get("session_summary")
        session.interaction_heatmap = analysis_results.get("interaction_heatmap")
        session.conversion_funnel = analysis_results.get("conversion_funnel")
        session.error_events = analysis_results.get("error_events")
        session.action_counts = analysis_results.get("action_counts")
        session.molmo_analysis_metadata = {
            "model": settings.molmo_api_model,
            "provider": "openrouter",
            "processing_time": None,  # Could track this if needed
        }

        db.commit()
        logger.info(f"[MOLMO] Analysis completed and stored for session {session_id}")

        return {
            "success": True,
            "session_id": session_id,
            "analysis_status": "completed",
        }

    except Exception as e:
        logger.error(f"[MOLMO] Exception analyzing video for session {session_id}: {e}", exc_info=True)
        try:
            session = db.query(Session).filter(
                Session.session_id == session_id
            ).first()
            if session:
                session.analysis_status = "failed"
                # Store detailed error information
                error_details = {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "timestamp": utc_now().isoformat(),
                }
                # Add more context if available
                if hasattr(e, "__traceback__"):
                    import traceback
                    error_details["traceback"] = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                session.molmo_analysis_metadata = error_details
                db.commit()
                logger.error(f"[MOLMO] Marked session {session_id} analysis as FAILED: {str(e)}")
        except Exception as db_error:
            logger.error(f"[MOLMO] Failed to update session status after error: {db_error}")

        return {"success": False, "error": str(e)}

    finally:
        db.close()


async def cleanup_stale_sessions(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Find and process stale sessions.

    Sessions are considered stale if:
    - Status is 'active' and started > 5 minutes ago (no heartbeat tracking anymore)

    Returns:
        Dict with count of sessions processed
    """
    db = SessionLocal()

    try:
        now = utc_now()
        stale_threshold = now - timedelta(minutes=5)

        processed = 0
        queued_for_video = 0

        # Find stale ACTIVE sessions (started > 5 minutes ago)
        stale_active_sessions = db.query(Session).filter(
            Session.status == SessionStatus.ACTIVE,
            Session.started_at < stale_threshold,
        ).all()

        for session in stale_active_sessions:
            # Mark as completed
            session.status = SessionStatus.COMPLETED
            session.ended_at = now
            session.updated_at = now

            # Calculate duration
            if session.started_at:
                duration = (session.ended_at - session.started_at).total_seconds()
                session.duration = int(duration)

            db.commit()

            # Queue video generation if session has events AND duration >= 30s
            if session.duration and session.duration >= 30 and session.event_count > 0:
                try:
                    from app.utils.video_queue import queue_video_generation
                    queued = await queue_video_generation(session.session_id)
                    if queued:
                        queued_for_video += 1
                except Exception as e:
                    logger.error(
                        f"Failed to queue video generation for stale session {session.session_id}: {e}",
                        exc_info=True
                    )

            processed += 1

        return {
            "success": True,
            "processed": processed,
            "queued_for_video": queued_for_video,
        }

    except Exception as e:
        logger.error(f"Error in cleanup_stale_sessions: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

    finally:
        db.close()
