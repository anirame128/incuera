"""Session model."""
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Session(Base):
    """Session model for tracking user sessions."""
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String, unique=True, nullable=False, index=True)  # From SDK
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(String, nullable=True)  # From SDK (optional)
    user_email = Column(String, nullable=True)  # From SDK (optional)
    url = Column(String, nullable=False)
    referrer = Column(String, nullable=True)
    user_agent = Column(String, nullable=False)
    screen_width = Column(Integer, nullable=True)
    screen_height = Column(Integer, nullable=True)
    viewport_width = Column(Integer, nullable=True)
    viewport_height = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Integer, nullable=True)  # Duration in seconds
    event_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Video generation fields
    status = Column(String(20), default="active", index=True)  # active|completed|processing|ready|failed
    video_url = Column(String(500), nullable=True)
    video_thumbnail_url = Column(String(500), nullable=True)
    keyframes_url = Column(String(500), nullable=True)
    video_generated_at = Column(DateTime(timezone=True), nullable=True)
    video_duration_ms = Column(Integer, nullable=True)
    video_size_bytes = Column(BigInteger, nullable=True)
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="sessions")
    events = relationship("Event", back_populates="session", cascade="all, delete-orphan", order_by="Event.sequence_number")
