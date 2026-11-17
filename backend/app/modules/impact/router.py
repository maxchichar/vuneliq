import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.modules.identity.models import User
from app.modules.impact.schemas import (
    ExpenseCreateRequest,
    ExpenseRead,
    FinancialAuditRead,
    ProgressReportCreateRequest,
    ProgressReportRead,
)
from app.modules.impact.services import (
    create_expense,
    create_progress_report,
    get_financial_audit,
    list_project_expenses,
    list_project_progress_reports,
)
from app.shared.database import get_db
from app.shared.dependencies import get_current_user

impact_router = APIRouter(tags=["Impact & Transparency"])


@impact_router.post(
    "/projects/{project_id}/expenses",
    response_model=ExpenseRead,
    status_code=status.HTTP_201_CREATED,
)
def log_project_expense(
    project_id: uuid.UUID,
    request: ExpenseCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Logs an expense against raised project funds.
    Restricted to project owner or platform admin.
    """
    return create_expense(db, project_id, current_user, request)


@impact_router.get(
    "/projects/{project_id}/expenses",
    response_model=list[ExpenseRead],
)
def get_project_expenses(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Publicly lists all expenses and receipt proofs logged for a project."""
    return list_project_expenses(db, project_id)


@impact_router.post(
    "/projects/{project_id}/reports",
    response_model=ProgressReportRead,
    status_code=status.HTTP_201_CREATED,
)
def publish_progress_report(
    project_id: uuid.UUID,
    request: ProgressReportCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Publishes an impact progress update for a project.
    Restricted to project owner or platform admin.
    """
    return create_progress_report(db, project_id, current_user, request)


@impact_router.get(
    "/projects/{project_id}/reports",
    response_model=list[ProgressReportRead],
)
def get_project_reports(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Publicly lists all progress reports and milestones published for a project."""
    return list_project_progress_reports(db, project_id)


@impact_router.get(
    "/projects/{project_id}/financial-audit",
    response_model=FinancialAuditRead,
)
def get_project_financial_audit(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Public financial health check of a project:
    amount raised, total spent, remaining unspent balance, and expenditure %.
    """
    return get_financial_audit(db, project_id)
