"""Serialization utilities for converting models to API responses."""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID


def serialize_uuid(value: Optional[UUID]) -> Optional[str]:
    """
    Serialize UUID to string.
    
    Args:
        value: UUID value or None
        
    Returns:
        String representation or None
    """
    return str(value) if value else None


def serialize_datetime(value: Optional[datetime]) -> Optional[str]:
    """
    Serialize datetime to ISO format string.
    
    Args:
        value: Datetime value or None
        
    Returns:
        ISO format string or None
    """
    return value.isoformat() if value else None


def serialize_model_to_dict(
    model: Any,
    uuid_fields: Optional[list[str]] = None,
    datetime_fields: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """
    Serialize a SQLAlchemy model to a dictionary.
    
    Args:
        model: SQLAlchemy model instance
        uuid_fields: List of field names that are UUIDs
        datetime_fields: List of field names that are datetimes
        
    Returns:
        Dictionary representation of the model
    """
    uuid_fields = uuid_fields or []
    datetime_fields = datetime_fields or []
    
    result = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        
        if column.name in uuid_fields:
            result[column.name] = serialize_uuid(value)
        elif column.name in datetime_fields:
            result[column.name] = serialize_datetime(value)
        else:
            result[column.name] = value
    
    return result
