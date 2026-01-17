"""URL utility functions."""
import urllib.parse
from typing import Optional


def decode_session_id(session_id: str) -> str:
    """
    Decode a URL-encoded session ID.
    
    Args:
        session_id: Potentially URL-encoded session ID
        
    Returns:
        Decoded session ID
    """
    try:
        return urllib.parse.unquote(session_id)
    except Exception:
        # If decoding fails, return original
        return session_id
