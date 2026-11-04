import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.modules.identity.models import User, UserRole
from app.modules.projects.models import ProjectStatus
from app.modules.projects.schemas import (
    ProjectCreateRequest,
    ProjectRead,
    ProjectReviewRead,
    ProjectReviewRequest,
    ProjectUpdateRequest,
)
from app.modules.projects.services import (
    create_project,
    get_project_by_id,
    list_owner_projects,
    list_pending_projects,
    list_public_projects,
    review_project,
    update_project,
)
from app.shared.database import get_db
from app.shared.dependencies import get_current_user, require_roles

projects_router = APIRouter(prefix="/projects", tags=["Projects"])
admin_projects_router = APIRouter(prefix="/admin/projects", tags=["Admin - Project Review"])


# ==========================================
# PUBLIC DISCOVERY
# ==========================================

@projects_router.get("", response_model=list[ProjectRead])
def get_public_projects(
    category: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Rule 1: Public project discovery (only APPROVED projects are returned)."""
    return list_public_projects(db, category=category, skip=skip, limit=limit)


@projects_router.get("/{project_id}", response_model=ProjectRead)
def get_project_details(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """Fetch project details. Rejects unapproved projects from public view."""
    project = get_project_by_id(db, project_id)
    if not project or project.status != ProjectStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or is not open for public viewing.",
        )
    return project


# ==========================================
# PROJECT OWNER ROUTES
# ==========================================

@projects_router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def submit_project(
    request: ProjectCreateRequest,
    current_user: User = Depends(require_roles(UserRole.PROJECT_OWNER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Allows project owners and admins to submit a project for review."""
    return create_project(db, current_user.id, request)


@projects_router.patch("/{project_id}", response_model=ProjectRead)
def edit_project(
    project_id: uuid.UUID,
    request: ProjectUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rule 3: Project owners can only edit their own projects."""
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    is_admin = current_user.role == UserRole.ADMIN
    return update_project(db, project, current_user.id, is_admin, request)


# User/Owner dashboard route (lives at /api/my/projects)
my_projects_router = APIRouter(prefix="/my", tags=["User Dashboard"])

@my_projects_router.get("/projects", response_model=list[ProjectRead])
def get_my_projects(
    current_user: User = Depends(require_roles(UserRole.PROJECT_OWNER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Owner dashboard: fetch all projects owned by the authenticated user."""
    return list_owner_projects(db, current_user.id)


# ==========================================
# ADMIN REVIEW QUEUE ROUTES
# ==========================================

@admin_projects_router.get("/pending", response_model=list[ProjectRead])
def get_pending_projects_queue(
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Rule 5: Review queue of submitted projects (Admins only)."""
    return list_pending_projects(db)


@admin_projects_router.post("/{project_id}/review", response_model=ProjectReviewRead)
def review_project_decision(
    project_id: uuid.UUID,
    request: ProjectReviewRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Review action (approve, reject, request_changes, suspend) with audit logging.
    Enforces Rule 27 (owners cannot approve their own submissions).
    """
    project = get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return review_project(db, project, current_user.id, request)