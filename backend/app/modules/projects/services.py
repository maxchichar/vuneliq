import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.projects.models import Project, ProjectReview, ProjectStatus, ReviewAction
from app.modules.projects.schemas import ProjectCreateRequest, ProjectReviewRequest, ProjectUpdateRequest



def create_project(db: Session, owner_id: uuid.UUID, data: ProjectCreateRequest) -> Project:
    project = Project(
        owner_id=owner_id,
        title=data.title.strip(),
        description=data.description.strip(),
        category=data.category.strip(),
        location=data.location.strip(),
        funding_target=data.funding_target,
        amount_raised=0,
        currency=data.currency.upper().strip(),
        beneficiary_target=data.beneficiary_target.strip(),
        intended_outcomes=data.intended_outcomes.strip(),
        budget_breakdown=data.budget_breakdown.strip(),
        status=ProjectStatus.PENDING_REVIEW,
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return project


def get_project_by_id(db: Session, project_id: uuid.UUID) -> Project | None:
    stmt = select(Project).where(Project.id == project_id)
    return db.scalar(stmt)


def list_public_projects(db: Session, category: str | None = None, location: str | None = None, skip: int = 0, limit: int = 20) -> list[Project]:
    """Rule 1: Public discovery returns Only projects with status APPROVED."""
    stmt = select(Project).where(Project.status == ProjectStatus.APPROVED)

    # Adding filters
    if category:
        stmt = stmt.where(Project.category == category)
    if location:
        stmt = stmt.where(Project.location == location)

    # Pagination
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt).all())

def list_owner_projects(db: Session, owner_id: uuid.UUID) -> list[Project]:
    """Returns all projects owned by a specific project owner."""
    stmt = select(Project).where(Project.owner_id == owner_id)
    return list(db.scalars(stmt).all())

def list_pending_projects(db: Session) -> list[Project]:
    """Admin queue: returns projects waiting for reviewer assessment."""
    stmt = select(Project).where(Project.status == ProjectStatus.PENDING_REVIEW)
    return list(db.scalars(stmt).all())

def update_project(
    db: Session, project: Project, current_user_id: uuid.UUID, is_admin: bool, data: ProjectUpdateRequest
) -> Project:
    """Rule 3: Only the project owner or an admin can edit a Project."""
    if project.owner_id != current_user_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to modify this project.",
        )

    update_dict = data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(project, field, value)


    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def review_project(
    db: Session, project: Project, reviewer_id: uuid.UUID, review_data: ProjectReviewRequest
) -> ProjectReview:
    """
    Enforces review governance:
    - Rule 27: A project owner cannot approve their own submission!
    - Updates project status and logs decision in project_reviews.
    """

    if project.owner_id == reviewer_id and review_data.action == ReviewAction.APPROVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conflict of interest: Project owners cannot approve their own submissions.",
        )

     # State machine transition
    status_map = {
        ReviewAction.APPROVE: ProjectStatus.APPROVED,
        ReviewAction.REJECT: ProjectStatus.REJECTED,
        ReviewAction.REQUEST_CHANGES: ProjectStatus.CHANGES_REQUESTED,
        ReviewAction.SUSPEND: ProjectStatus.SUSPENDED,
    }
    project.status = status_map[review_data.action]

    # Create audit record
    review = ProjectReview(
        project_id=project.id,
        reviewer_id=reviewer_id,
        action=review_data.action,
        reason=review_data.reason.strip(),
    )
    db.add(review)
    db.add(project)
    db.commit()
    db.refresh(review)
    return review

     
