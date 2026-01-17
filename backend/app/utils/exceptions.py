"""Custom exceptions and error handling utilities."""
from fastapi import HTTPException, status
from typing import Optional


class AppException(Exception):
    """Base exception for application errors."""
    pass


class NotFoundError(AppException):
    """Raised when a resource is not found."""
    pass


class ValidationError(AppException):
    """Raised when validation fails."""
    pass


class AuthenticationError(AppException):
    """Raised when authentication fails."""
    pass


def handle_database_error(error: Exception, operation: str) -> HTTPException:
    """
    Convert database errors to HTTP exceptions.
    
    Args:
        error: The database error
        operation: Description of the operation that failed
        
    Returns:
        HTTPException with appropriate status code
    """
    error_message = str(error)
    
    # Handle common database errors
    if "not found" in error_message.lower() or "does not exist" in error_message.lower():
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource not found: {operation}",
        )
    
    if "duplicate" in error_message.lower() or "unique" in error_message.lower():
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Resource already exists: {operation}",
        )
    
    # Default to 500 for unknown database errors
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Database error during {operation}: {error_message}",
    )


def not_found_error(resource: str, identifier: Optional[str] = None) -> HTTPException:
    """
    Create a standardized 404 error.
    
    Args:
        resource: Name of the resource (e.g., "Session", "Project")
        identifier: Optional identifier that was not found
        
    Returns:
        HTTPException with 404 status
    """
    message = f"{resource} not found"
    if identifier:
        message += f": {identifier}"
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)


def validation_error(message: str) -> HTTPException:
    """
    Create a standardized 400 validation error.
    
    Args:
        message: Validation error message
        
    Returns:
        HTTPException with 400 status
    """
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def authentication_error(message: str = "Invalid credentials") -> HTTPException:
    """
    Create a standardized 401 authentication error.
    
    Args:
        message: Authentication error message
        
    Returns:
        HTTPException with 401 status
    """
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)


def forbidden_error(message: str = "Access denied") -> HTTPException:
    """
    Create a standardized 403 forbidden error.
    
    Args:
        message: Forbidden error message
        
    Returns:
        HTTPException with 403 status
    """
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)
