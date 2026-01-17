"""Session Event model for storing rrweb events."""
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Event(Base):
    """Event model for storing rrweb session events."""
    __tablename__ = "events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, index=True)
    event_data = Column(JSONB, nullable=False)  # Full rrweb event
    event_type = Column(String, nullable=False, index=True)  # e.g., "dom-content-loaded", "full-snapshot"
    event_timestamp = Column(BigInteger, nullable=False)  # From rrweb (milliseconds since epoch - needs BIGINT)
    sequence_number = Column(Integer, nullable=False)  # Order within session
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("Session", back_populates="events")
    
    # Composite index for efficient querying
    __table_args__ = (
        Index('idx_session_sequence', 'session_id', 'sequence_number'),
    )
