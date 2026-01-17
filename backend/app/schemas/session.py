"""Schemas for session management."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class SessionMetadata(BaseModel):
    """Session metadata from SDK."""
    url: str
    referrer: Optional[str] = None
    userAgent: str
    screen: Dict[str, int]
    viewport: Dict[str, int]
    timestamp: int


class SessionStartRequest(BaseModel):
    """Request schema for /api/sessions/start endpoint."""
    sessionId: str = Field(..., description="Session ID from SDK")
    userId: Optional[str] = Field(None, description="User ID from SDK")
    userEmail: Optional[str] = Field(None, description="User email from SDK")
    metadata: SessionMetadata


class SessionStartResponse(BaseModel):
    """Response schema for /api/sessions/start endpoint."""
    success: bool
    message: str
    session_id: str


class SessionHeartbeatRequest(BaseModel):
    """Request schema for /api/sessions/heartbeat endpoint."""
    sessionId: str = Field(..., description="Session ID from SDK")
    timestamp: int = Field(..., description="Client timestamp in milliseconds")
    eventCount: int = Field(..., description="Current event count")


class SessionHeartbeatResponse(BaseModel):
    """Response schema for /api/sessions/heartbeat endpoint."""
    success: bool
    message: str


class SessionEndRequest(BaseModel):
    """Request schema for /api/sessions/end endpoint."""
    sessionId: str = Field(..., description="Session ID from SDK")
    reason: str = Field(..., description="Reason for session end (beforeunload, pagehide, manual_stop)")
    timestamp: int = Field(..., description="Client timestamp in milliseconds")
    finalEventCount: int = Field(..., description="Final event count")


class SessionEndResponse(BaseModel):
    """Response schema for /api/sessions/end endpoint."""
    success: bool
    message: str
    video_job_queued: bool = False


class VideoStatusResponse(BaseModel):
    """Response schema for video status."""
    session_id: str
    status: str
    video_url: Optional[str] = None
    video_thumbnail_url: Optional[str] = None
    keyframes_url: Optional[str] = None
    video_generated_at: Optional[datetime] = None
    video_duration_ms: Optional[int] = None
    video_size_bytes: Optional[int] = None


class SessionListItem(BaseModel):
    """Session list item response."""
    id: str
    session_id: str
    project_id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    url: Optional[str] = None
    started_at: Optional[str] = None
    event_count: int
    duration: Optional[int] = None
    status: str
    video_url: Optional[str] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj) -> "SessionListItem":
        """Convert SQLAlchemy model to response model."""
        return cls(
            id=str(obj.id),
            session_id=obj.session_id,
            project_id=str(obj.project_id),
            user_id=obj.user_id,
            user_email=obj.user_email,
            url=obj.url,
            started_at=obj.started_at.isoformat() if obj.started_at else None,
            event_count=obj.event_count,
            duration=obj.duration,
            status=obj.status,
            video_url=obj.video_url,
        )
