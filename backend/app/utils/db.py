"""Database query utility functions."""
from typing import Optional, TypeVar, Type, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
from fastapi import HTTPException, status

T = TypeVar("T")


def get_by_id(
    db: Session,
    model: Type[T],
    id_value: str | UUID,
    error_message: Optional[str] = None,
) -> T:
    """
    Get a model instance by ID.
    
    Args:
        db: Database session
        model: SQLAlchemy model class
        id_value: ID value (UUID string or UUID object)
        error_message: Custom error message if not found
        
    Returns:
        Model instance
        
    Raises:
        HTTPException: If model not found
    """
    try:
        # Convert string to UUID if needed
        if isinstance(id_value, str):
            id_value = UUID(id_value)
        
        instance = db.query(model).filter(model.id == id_value).first()
        
        if not instance:
            message = error_message or f"{model.__name__} not found"
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        
        return instance
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {model.__name__} ID format",
        )


def get_by_field(
    db: Session,
    model: Type[T],
    field_name: str,
    field_value: Any,
    error_message: Optional[str] = None,
) -> Optional[T]:
    """
    Get a model instance by a specific field.
    
    Args:
        db: Database session
        model: SQLAlchemy model class
        field_name: Name of the field to filter by
        field_value: Value to filter by
        error_message: Custom error message if not found (if None, returns None instead of raising)
        
    Returns:
        Model instance or None
    """
    field = getattr(model, field_name)
    instance = db.query(model).filter(field == field_value).first()
    
    if not instance and error_message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_message)
    
    return instance
