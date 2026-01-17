"""ARQ background tasks for video generation."""
import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from sqlalchemy.orm import sessionmaker

from app.database import engine
from app.models.session import Session
from app.models.event import Event
from app.services.video import VideoGenerator
from app.services.storage import storage_service
from app.utils.logger import logger
from app.constants import SessionStatus


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
    db = SessionLocal()
    temp_dir = None

    try:
        # Find the session
        session = db.query(Session).filter(
            Session.session_id == session_id
        ).first()

        if not session:
            return {"success": False, "error": f"Session not found: {session_id}"}

        # Check if session should be processed
        if session.status not in [SessionStatus.COMPLETED, SessionStatus.FAILED]:
            return {
                "success": False,
                "error": f"Session status is {session.status}, not eligible for video generation",
            }

        # Update status to processing
        session.status = SessionStatus.PROCESSING
        db.commit()

        # Get all events for the session
        events = db.query(Event).filter(
            Event.session_id == session.id
        ).order_by(Event.sequence_number.asc()).all()

        if not events:
            session.status = SessionStatus.FAILED
            db.commit()
            return {"success": False, "error": "No events found for session"}

        # Extract event data
        event_data = [event.event_data for event in events]

        # Create temporary output directory
        temp_dir = tempfile.mkdtemp(prefix=f"video_output_{session_id}_")

        # Generate video
        generator = VideoGenerator()
        result = await generator.generate_video(
            events=event_data,
            output_dir=temp_dir,
            session_id=session_id,
        )

        if not result.success:
            session.status = SessionStatus.FAILED
            db.commit()
            logger.error(f"Video generation failed for session {session_id}: {result.error}")
            return {"success": False, "error": result.error}

        # Upload to Supabase Storage
        project_id = str(session.project_id)
        
        upload_success = True
        upload_errors = []

        # Upload video
        if result.video_path:
            video_result = await storage_service.upload_video(
                result.video_path, project_id, session_id
            )
            if video_result.success:
                session.video_url = video_result.url
            else:
                upload_success = False
                upload_errors.append(f"Video upload failed: {video_result.error}")
        
        # Upload thumbnail
        if result.thumbnail_path and upload_success:
            thumb_result = await storage_service.upload_thumbnail(
                result.thumbnail_path, project_id, session_id
            )
            if thumb_result.success:
                session.video_thumbnail_url = thumb_result.url
            else:
                logger.warning(f"Thumbnail upload failed: {thumb_result.error}")
                # We don't fail the whole process for just a thumbnail failure
        
        # Upload keyframes
        if result.keyframes_path and upload_success:
            keyframes_result = await storage_service.upload_keyframes(
                result.keyframes_path, project_id, session_id
            )
            if keyframes_result.success:
                session.keyframes_url = keyframes_result.url
            else:
                logger.warning(f"Keyframes upload failed: {keyframes_result.error}")

        if not upload_success:
            session.status = SessionStatus.FAILED
            db.commit()
            error_msg = "; ".join(upload_errors)
            logger.error(f"Upload failed for session {session_id}: {error_msg}")
            return {"success": False, "error": error_msg}

        # Update session with video details
        session.status = SessionStatus.READY
        session.video_generated_at = utc_now()
        session.video_duration_ms = result.duration_ms
        session.video_size_bytes = result.size_bytes
        db.commit()

        logger.info(
            f"Video generated and uploaded successfully for session {session_id}: "
            f"{result.duration_ms}ms, {result.size_bytes} bytes"
        )

        return {
            "success": True,
            "session_id": session_id,
            "video_url": session.video_url,
            "duration_ms": result.duration_ms,
            "size_bytes": result.size_bytes,
        }

    except Exception as e:
        # Mark session as failed
        logger.error(f"Error generating video for session {session_id}: {e}", exc_info=True)
        try:
            session = db.query(Session).filter(
                Session.session_id == session_id
            ).first()
            if session:
                session.status = SessionStatus.FAILED
                db.commit()
        except Exception:
            pass

        return {"success": False, "error": str(e)}

    finally:
        db.close()
        # Cleanup temp directory
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


async def cleanup_stale_sessions(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Find and process stale sessions.

    Sessions are considered stale if:
    - Status is 'active'
    - Last heartbeat was more than 5 minutes ago OR no heartbeat and started > 5 min ago

    Returns:
        Dict with count of sessions processed
    """
    db = SessionLocal()

    try:
        stale_threshold = utc_now() - timedelta(minutes=5)

        # Find stale sessions
        stale_sessions = db.query(Session).filter(
            Session.status == SessionStatus.ACTIVE,
        ).filter(
            # Either last heartbeat is stale, or no heartbeat and session started long ago
            (
                (Session.last_heartbeat_at.isnot(None)) &
                (Session.last_heartbeat_at < stale_threshold)
            ) | (
                (Session.last_heartbeat_at.is_(None)) &
                (Session.started_at < stale_threshold)
            )
        ).all()

        processed = 0
        queued_for_video = 0

        for session in stale_sessions:
            # Only process sessions with events
            if session.event_count > 0:
                session.status = SessionStatus.COMPLETED
                session.ended_at = session.last_heartbeat_at or utc_now()

                # Calculate duration
                if session.started_at:
                    duration = (session.ended_at - session.started_at).total_seconds()
                    session.duration = int(duration)

                db.commit()

                # Queue video generation
                try:
                    from app.utils.video_queue import queue_video_generation
                    queued = await queue_video_generation(session.session_id)
                    if queued:
                        queued_for_video += 1
                except Exception as e:
                    logger.error(
                        f"Failed to queue video for session {session.session_id}: {e}",
                        exc_info=True
                    )

                processed += 1
            else:
                # No events, just mark as completed without video
                session.status = SessionStatus.COMPLETED
                db.commit()
                processed += 1

        return {
            "success": True,
            "sessions_processed": processed,
            "sessions_queued_for_video": queued_for_video,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

    finally:
        db.close()
