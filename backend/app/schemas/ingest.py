"""Schemas for event ingestion."""
from pydantic import BaseModel, Field
from typing import List, Dict, Any


class IngestRequest(BaseModel):
    """Request schema for /api/ingest endpoint."""
    sessionId: str = Field(..., description="Session ID from SDK")
    events: List[Dict[str, Any]] = Field(..., description="Array of rrweb events")
    timestamp: int = Field(..., description="Timestamp when events were sent")


class IngestResponse(BaseModel):
    """Response schema for /api/ingest endpoint."""
    success: bool
    message: str
    events_received: int
    session_finalized: bool = False  # True if session is already finalized (SDK should create new session)
