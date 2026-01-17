"""Event ingestion endpoint."""
from datetime import datetime
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

router = APIRouter(prefix="/api", tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_events(
    request: IngestRequest,
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_from_api_key),
) -> IngestResponse:
    """
    Ingest session events from the SDK.
    
    This endpoint receives batches of rrweb events and stores them in the database.
    Requires API key to identify project.
    
    Args:
        request: Ingest request with session ID and events
        db: Database session
        project: Project from API key
        
    Returns:
        Ingest response with success status and event count
    """
    try:
        # Find the session (must exist - should be created by /sessions/start first)
        session = db.query(SessionModel).filter(
            SessionModel.session_id == request.sessionId,
            SessionModel.project_id == project.id,
        ).first()
        
        if not session:
            raise not_found_error(
                "Session",
                f"{request.sessionId}. Please call /api/sessions/start first."
            )

        # Validate events array
        if not request.events or len(request.events) == 0:
            return IngestResponse(
                success=True,
                message="No events to ingest",
                events_received=0,
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
            
            # Update session event count
            session.event_count += len(events_to_insert)
            session.updated_at = datetime.utcnow()
            
            db.commit()
        
        logger.info(
            f"Ingested {len(events_to_insert)} events for session {request.sessionId}"
        )
        
        return IngestResponse(
            success=True,
            message="Events ingested successfully",
            events_received=len(events_to_insert),
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
