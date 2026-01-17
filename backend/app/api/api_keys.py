"""API Keys management endpoints."""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import APIKey
from app.utils.hashing import hash_api_key, generate_api_key
from app.utils.logger import logger
from app.utils.exceptions import not_found_error, validation_error, handle_database_error
from app.utils.db import get_by_id

router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])


class APIKeyCreate(BaseModel):
    project_id: str
    name: str


class APIKeyResponse(BaseModel):
    id: str
    project_id: str
    key_prefix: str
    name: str
    is_active: bool
    last_used_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj: APIKey) -> "APIKeyResponse":
        """Convert SQLAlchemy model to response model."""
        return cls(
            id=str(obj.id),
            project_id=str(obj.project_id),
            key_prefix=obj.key_prefix,
            name=obj.name,
            is_active=obj.is_active,
            last_used_at=obj.last_used_at.isoformat() if obj.last_used_at else None,
            created_at=obj.created_at.isoformat() if obj.created_at else None,
        )


@router.get("", response_model=list[APIKeyResponse])
async def get_api_keys(
    project_id: str = Query(..., description="Project ID"),
    db: Session = Depends(get_db),
) -> list[APIKeyResponse]:
    """
    Get all API keys for a project.
    
    Args:
        project_id: The project ID
        db: Database session
        
    Returns:
        List of API keys for the project
    """
    try:
        keys = db.query(APIKey).filter(APIKey.project_id == uuid.UUID(project_id)).all()
        return [APIKeyResponse.from_orm(k) for k in keys]
    except ValueError:
        raise validation_error("Invalid project ID format")
    except Exception as e:
        logger.error(f"Failed to get API keys for project {project_id}: {e}", exc_info=True)
        raise handle_database_error(e, "get_api_keys")


@router.post("")
async def create_api_key(
    request: APIKeyCreate,
    db: Session = Depends(get_db),
) -> dict[str, str | APIKeyResponse]:
    """
    Create a new API key.
    
    Args:
        request: API key creation data
        db: Database session
        
    Returns:
        Dictionary with the raw key (only shown once) and API key details
    """
    try:
        # Generate new API key
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
        key_prefix = raw_key[:8]
        
        new_key = APIKey(
            id=uuid.uuid4(),
            project_id=uuid.UUID(request.project_id),
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=request.name,
            is_active=True,
        )
        
        db.add(new_key)
        db.commit()
        db.refresh(new_key)
        
        logger.info(f"Created API key {new_key.id} for project {request.project_id}")
        
        return {
            "key": raw_key,  # Only returned once!
            "apiKey": APIKeyResponse.from_orm(new_key),
        }
    except ValueError as e:
        db.rollback()
        raise validation_error(f"Invalid project ID format: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create API key: {e}", exc_info=True)
        raise handle_database_error(e, "create_api_key")


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: str,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """
    Delete an API key.
    
    Args:
        key_id: The API key ID to delete
        db: Database session
        
    Returns:
        Success status
    """
    try:
        key = get_by_id(db, APIKey, key_id, "API key not found")
        
        db.delete(key)
        db.commit()
        
        logger.info(f"Deleted API key {key_id}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete API key {key_id}: {e}", exc_info=True)
        raise handle_database_error(e, "delete_api_key")
