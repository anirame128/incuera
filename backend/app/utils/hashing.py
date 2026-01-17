"""Hashing utilities for passwords and API keys."""
import hashlib
import secrets
import bcrypt
from app.config import settings


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256 with salt.
    
    Args:
        api_key: The API key to hash
        
    Returns:
        Hex digest of the hashed key
    """
    salted_key = f"{api_key}{settings.api_key_salt}"
    return hashlib.sha256(salted_key.encode()).hexdigest()


def verify_api_key_hash(api_key: str, stored_hash: str) -> bool:
    """
    Verify an API key against a stored hash.
    
    Args:
        api_key: The API key to verify
        stored_hash: The stored hash to compare against
        
    Returns:
        True if the key matches, False otherwise
    """
    computed_hash = hash_api_key(api_key)
    return computed_hash == stored_hash


def generate_api_key() -> str:
    """
    Generate a new API key.
    
    Returns:
        A new API key string (format: inc_xxxxxxxxxxxx)
    """
    random_part = secrets.token_urlsafe(32)
    return f"inc_{random_part}"


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: The password to hash
        
    Returns:
        Bcrypt hash string
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a bcrypt hash.
    
    Args:
        password: The password to verify
        password_hash: The stored bcrypt hash
        
    Returns:
        True if the password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


def hash_password_legacy(password: str) -> str:
    """
    Legacy SHA-256 password hashing (for migration purposes).
    
    Args:
        password: The password to hash
        
    Returns:
        SHA-256 hex digest
    """
    return hashlib.sha256(password.encode()).hexdigest()
