"""Projects API endpoints."""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Project
from app.utils.logger import logger
from app.utils.exceptions import not_found_error, validation_error, handle_database_error
from app.utils.db import get_by_id

router = APIRouter(prefix="/api/projects", tags=["projects"])


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
        new_project = Project(
            id=uuid.uuid4(),
            user_id=uuid.UUID(project.user_id),
            name=project.name,
            domain=project.domain,
        )
        
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        
        logger.info(f"Created project {new_project.id} for user {project.user_id}")
        return ProjectResponse.from_orm(new_project)
    except ValueError as e:
        db.rollback()
        raise validation_error(f"Invalid user ID format: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create project: {e}", exc_info=True)
        raise handle_database_error(e, "create_project")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    """
    Get a specific project by ID.
    
    Args:
        project_id: The project ID
        db: Database session
        
    Returns:
        Project details
    """
    try:
        project = get_by_id(db, Project, project_id, "Project not found")
        return ProjectResponse.from_orm(project)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project {project_id}: {e}", exc_info=True)
        raise handle_database_error(e, "get_project")


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    """
    Update a project's name and domain.
    
    Args:
        project_id: The project ID to update
        project_update: Updated project data
        db: Database session
        
    Returns:
        Updated project
    """
    try:
        project = get_by_id(db, Project, project_id, "Project not found")
        
        project.name = project_update.name
        project.domain = project_update.domain
        
        db.commit()
        db.refresh(project)
        
        logger.info(f"Updated project {project_id}")
        return ProjectResponse.from_orm(project)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update project {project_id}: {e}", exc_info=True)
        raise handle_database_error(e, "update_project")


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Delete a project and all associated data.
    
    Args:
        project_id: The project ID to delete
        db: Database session
        
    Returns:
        Success message
    """
    try:
        project = get_by_id(db, Project, project_id, "Project not found")
        
        # Cascade delete will handle API keys and sessions
        db.delete(project)
        db.commit()
        
        logger.info(f"Deleted project {project_id}")
        return {"message": "Project deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete project {project_id}: {e}", exc_info=True)
        raise handle_database_error(e, "delete_project")
