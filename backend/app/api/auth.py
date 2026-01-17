"""Authentication API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import User
from app.utils.logger import logger
from app.utils.exceptions import authentication_error, handle_database_error
from app.utils.hashing import verify_password, hash_password_legacy

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    user: dict
    token: str | None = None


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """
    Login endpoint - simple password check for now.
    
    Note: In production, use proper password verification with bcrypt.
    
    Args:
        request: Login credentials
        db: Database session
        
    Returns:
        Login response with user data
    """
    try:
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            raise authentication_error("Invalid credentials")
        
        # Try bcrypt first, fall back to legacy SHA-256 for migration
        password_valid = False
        if user.password_hash.startswith('$2b$') or user.password_hash.startswith('$2a$'):
            # Bcrypt hash
            password_valid = verify_password(request.password, user.password_hash)
        else:
            # Legacy SHA-256 hash (for migration)
            legacy_hash = hash_password_legacy(request.password)
            password_valid = (user.password_hash == legacy_hash)
        
        if not password_valid:
            raise authentication_error("Invalid credentials")
        
        return LoginResponse(
            user={
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
            token=None,  # In production, generate JWT token
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {request.email}: {e}", exc_info=True)
        raise authentication_error("Login failed")
