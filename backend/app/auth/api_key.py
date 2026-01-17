"""API key authentication utilities."""
from datetime import datetime
from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.models.api_key import APIKey
from app.models.project import Project
from app.database import get_db
from app.utils.hashing import hash_api_key, verify_api_key_hash
from app.utils.logger import logger
from app.utils.exceptions import not_found_error, authentication_error


def verify_api_key(
    api_key: str = Header(..., alias="X-API-Key", description="API Key for authentication"),
    db: Session = Depends(get_db),
) -> APIKey:
    """
    Verify API key and return the APIKey object.
    
    Raises HTTPException if key is invalid.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
        )
    
    # Hash the provided key to compare with stored hash
    key_hash = hash_api_key(api_key)
    
    # Find API key in database
    db_api_key = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True,
    ).first()
    
    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    # Check if key has expired
    if db_api_key.expires_at and db_api_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )
    
    # Update last used timestamp
    db_api_key.last_used_at = datetime.utcnow()
    db.commit()
    
    return db_api_key


def get_api_key_project(db: Session, api_key_obj: APIKey) -> Project:
    """Get the project associated with an API key."""
    project = db.query(Project).filter(Project.id == api_key_obj.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def get_project_from_api_key(
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Project:
    """
    Get project from API key. API key is required.
    This is a helper function that can be used as a dependency.
    
    Args:
        api_key: API key from header
        db: Database session
        
    Returns:
        Project instance
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not api_key:
        raise authentication_error("API key is required")
    
    # Find project via API key
    key_hash = hash_api_key(api_key)
    db_api_key = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True,
    ).first()
    
    if not db_api_key:
        raise authentication_error("Invalid API key")
    
    project = db.query(Project).filter(Project.id == db_api_key.project_id).first()
    if not project:
        raise not_found_error("Project")
    
    return project
