"""Application-wide constants."""

# Session status values
class SessionStatus:
    """Session status constants."""
    ACTIVE = "active"
    COMPLETED = "completed"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


# API Key status
class APIKeyStatus:
    """API Key status constants."""
    ACTIVE = True
    INACTIVE = False
