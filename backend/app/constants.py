"""Application-wide constants."""

# Session status values
class SessionStatus:
    """Session status constants."""
    ACTIVE = "active"
    COMPLETED = "completed"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


# Session configuration
STALE_SESSION_MINUTES = 5  # Time before considering a session stale



