"""Event ingestion endpoint."""
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.session import Session as SessionModel
from app.models.event import Event
from app.models.project import Project
from app.auth.api_key import get_project_from_api_key
from app.schemas.ingest import IngestRequest, IngestResponse
from app.utils.logger import logger
from app.utils.exceptions import not_found_error, handle_database_error
from app.utils.pending_sessions import get_pending_session, delete_pending_session, append_pending_events, get_pending_events, delete_pending_events
from app.constants import SessionStatus

router = APIRouter(prefix="/api", tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_events(
    request: IngestRequest,
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_from_api_key),
) -> IngestResponse:
    """
    Ingest session events from the SDK.

    This endpoint receives batches of rrweb events and stores them temporarily in Redis
    if the session doesn't exist in the database yet. Sessions are only created in the
    database when they end via /api/sessions/end AND duration >= 30 seconds.
    Requires API key to identify project.

    Status handling:
    - Session exists in DB: Process events normally
    - Session not in DB: Store events in Redis temporarily
    - COMPLETED/PROCESSING/READY: Reject events, return session_finalized=true

    Args:
        request: Ingest request with session ID and events
        db: Database session
        project: Project from API key

    Returns:
        Ingest response with success status, event count, and session_finalized flag
    """
    try:
        # Validate events array early - no point creating session without events
        if not request.events or len(request.events) == 0:
            return IngestResponse(
                success=True,
                message="No events to ingest",
                events_received=0,
                session_finalized=False,
            )

        # Find the session in database
        session = db.query(SessionModel).filter(
            SessionModel.session_id == request.sessionId,
            SessionModel.project_id == project.id,
        ).first()

        # If session exists in DB, process events normally
        if session:
            # Check if session is already finalized (video generation started or complete)
            finalized_statuses = [SessionStatus.COMPLETED, SessionStatus.PROCESSING, SessionStatus.READY]
            if session.status in finalized_statuses:
                logger.info(
                    f"Rejecting events for finalized session {request.sessionId} "
                    f"(status: {session.status}, events: {len(request.events)})"
                )
                return IngestResponse(
                    success=True,
                    message="Session already finalized, events rejected",
                    events_received=0,
                    session_finalized=True,
                )

            # Get current max sequence number for this session
            max_sequence = db.query(Event.sequence_number).filter(
                Event.session_id == session.id
            ).order_by(Event.sequence_number.desc()).first()

            start_sequence = (max_sequence[0] + 1) if max_sequence else 0

            # Insert events
            events_to_insert = []
            for idx, event_data in enumerate(request.events):
                # Ensure event_data is a dict
                if not isinstance(event_data, dict):
                    continue

                event = Event(
                    session_id=session.id,
                    event_data=event_data,
                    event_type=event_data.get("type", "unknown"),
                    event_timestamp=event_data.get("timestamp", 0),
                    sequence_number=start_sequence + idx,
                )
                events_to_insert.append(event)

            if events_to_insert:
                db.bulk_save_objects(events_to_insert)

                # Update session event count and last_event_at
                session.event_count += len(events_to_insert)
                session.last_event_at = datetime.utcnow()
                session.updated_at = datetime.utcnow()

                db.commit()

            return IngestResponse(
                success=True,
                message="Events ingested successfully",
                events_received=len(events_to_insert),
                session_finalized=False,
            )

        # Session doesn't exist in DB - store events in Redis temporarily
        # Session will only be created when it ends AND duration >= 30s
        
        # Verify pending metadata exists
        pending = await get_pending_session(request.sessionId)
        if not pending:
            logger.warning(f"No pending metadata found in Redis for session {request.sessionId}")
            # Silently accept events but don't store them (session will be discarded anyway)
            return IngestResponse(
                success=True,
                message="Events accepted (pending session)",
                events_received=len(request.events),
                session_finalized=False,
            )

        # Verify project matches
        if pending.get("project_id") != str(project.id):
            logger.warning(f"Project mismatch for session {request.sessionId}")
            return IngestResponse(
                success=True,
                message="Events accepted (project mismatch)",
                events_received=len(request.events),
                session_finalized=False,
            )

        # Store events in Redis
        stored = await append_pending_events(request.sessionId, request.events)
        if not stored:
            logger.error(f"Failed to store pending events for {request.sessionId}")

        events_received = len(request.events)

        return IngestResponse(
            success=True,
            message="Events stored temporarily (session pending)",
            events_received=events_received,
            session_finalized=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            f"Failed to ingest events for session {request.sessionId}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest events: {str(e)}",
        )
