"""Projects API endpoints."""
import uuid
import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Project
from app.utils.logger import logger
from app.utils.exceptions import not_found_error, validation_error, handle_database_error, forbidden_error
from app.utils.db import get_by_id

router = APIRouter(prefix="/api/projects", tags=["projects"])


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a project name."""
    # Convert to lowercase
    slug = name.lower()
    # Replace spaces and underscores with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)
    # Remove special characters, keep only alphanumeric and hyphens
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    # Ensure it's not empty
    if not slug:
        slug = 'project'
    return slug


def get_unique_slug(db: Session, base_slug: str, user_id: uuid.UUID, exclude_project_id: Optional[uuid.UUID] = None) -> str:
    """Generate a unique slug for a user, appending numbers if needed."""
    slug = base_slug
    counter = 1
    
    while True:
        query = db.query(Project).filter(
            Project.slug == slug,
            Project.user_id == user_id
        )
        if exclude_project_id:
            query = query.filter(Project.id != exclude_project_id)
        
        existing = query.first()
        if not existing:
            return slug
        
        slug = f"{base_slug}-{counter}"
        counter += 1


def verify_project_ownership(project: Project, user_id: str) -> None:
    """Verify that the project belongs to the user."""
    if str(project.user_id) != user_id:
        raise forbidden_error("Access denied: You don't have permission to access this project")


class ProjectCreate(BaseModel):
    name: str
    domain: Optional[str] = None
    user_id: str


class ProjectUpdate(BaseModel):
    name: str
    domain: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    user_id: str
    name: str
    slug: str
    domain: Optional[str]
    created_at: Optional[str]

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj: Project) -> "ProjectResponse":
        """Convert SQLAlchemy model to response model."""
        return cls(
            id=str(obj.id),
            user_id=str(obj.user_id),
            name=obj.name,
            slug=obj.slug,
            domain=obj.domain,
            created_at=obj.created_at.isoformat() if obj.created_at else None,
        )


@router.get("", response_model=list[ProjectResponse])
async def get_projects(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db),
) -> list[ProjectResponse]:
    """
    Get all projects for a user.
    
    Args:
        user_id: The user ID to get projects for
        db: Database session
        
    Returns:
        List of projects for the user
    """
    try:
        projects = db.query(Project).filter(Project.user_id == uuid.UUID(user_id)).all()
        return [ProjectResponse.from_orm(p) for p in projects]
    except ValueError:
        raise validation_error("Invalid user ID format")
    except Exception as e:
        logger.error(f"Failed to get projects for user {user_id}: {e}", exc_info=True)
        raise handle_database_error(e, "get_projects")


@router.post("", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    """
    Create a new project.
    
    Args:
        project: Project creation data
        db: Database session
        
    Returns:
        Created project
    """
    try:
        # Generate unique slug
        base_slug = generate_slug(project.name)
        unique_slug = get_unique_slug(db, base_slug, uuid.UUID(project.user_id))
        
        new_project = Project(
            id=uuid.uuid4(),
            user_id=uuid.UUID(project.user_id),
            name=project.name,
            slug=unique_slug,
            domain=project.domain,
        )
        
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        
        return ProjectResponse.from_orm(new_project)
    except ValueError as e:
        db.rollback()
        raise validation_error(f"Invalid user ID format: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create project: {e}", exc_info=True)
        raise handle_database_error(e, "create_project")


@router.get("/{project_slug}", response_model=ProjectResponse)
async def get_project(
    project_slug: str,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    """
    Get a specific project by slug.
    
    Args:
        project_slug: The project slug (URL-friendly identifier)
        user_id: The user ID (must own the project)
        db: Database session
        
    Returns:
        Project details
    """
    try:
        project = db.query(Project).filter(
            Project.slug == project_slug,
            Project.user_id == uuid.UUID(user_id)
        ).first()
        
        if not project:
            raise not_found_error("Project")
        
        return ProjectResponse.from_orm(project)
    except HTTPException:
        raise
    except ValueError:
        raise validation_error("Invalid user ID format")
    except Exception as e:
        logger.error(f"Failed to get project {project_slug}: {e}", exc_info=True)
        raise handle_database_error(e, "get_project")


@router.put("/{project_slug}", response_model=ProjectResponse)
async def update_project(
    project_slug: str,
    project_update: ProjectUpdate,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    """
    Update a project's name and domain.
    
    Args:
        project_slug: The project slug to update
        project_update: Updated project data
        user_id: The user ID (must own the project)
        db: Database session
        
    Returns:
        Updated project
    """
    try:
        project = db.query(Project).filter(
            Project.slug == project_slug,
            Project.user_id == uuid.UUID(user_id)
        ).first()
        
        if not project:
            raise not_found_error("Project")
        
        # Update name and regenerate slug if name changed
        if project.name != project_update.name:
            project.name = project_update.name
            base_slug = generate_slug(project_update.name)
            project.slug = get_unique_slug(db, base_slug, uuid.UUID(user_id), exclude_project_id=project.id)
        
        project.domain = project_update.domain
        
        db.commit()
        db.refresh(project)
        
        return ProjectResponse.from_orm(project)
    except HTTPException:
        raise
    except ValueError:
        raise validation_error("Invalid user ID format")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update project {project_slug}: {e}", exc_info=True)
        raise handle_database_error(e, "update_project")


@router.delete("/{project_slug}")
async def delete_project(
    project_slug: str,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Delete a project and all associated data.
    
    Args:
        project_slug: The project slug to delete
        user_id: The user ID (must own the project)
        db: Database session
        
    Returns:
        Success message
    """
    try:
        project = db.query(Project).filter(
            Project.slug == project_slug,
            Project.user_id == uuid.UUID(user_id)
        ).first()
        
        if not project:
            raise not_found_error("Project")
        
        # Cascade delete will handle API keys and sessions
        db.delete(project)
        db.commit()
        
        return {"message": "Project deleted successfully"}
    except HTTPException:
        raise
    except ValueError:
        raise validation_error("Invalid user ID format")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete project {project_slug}: {e}", exc_info=True)
        raise handle_database_error(e, "delete_project")
