from datetime import datetime, timezone
import uuid
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.identity.models import User, UserRole
from app.modules.impact.models import Expense, ProgressReport
from app.modules.impact.schemas import (
    ExpenseCreateRequest,
    ProgressReportCreateRequest,
)
from app.modules.projects.models import Project, ProjectStatus
from app.shared.logging import get_module_logger

logger = get_module_logger("impact")


def create_expense(
    db: Session,
    project_id: uuid.UUID,
    current_user: User,
    data: ExpenseCreateRequest,
) -> Expense:
    """
    Logs an expense against an approved project.
    Enforces Rule 10 (ownership), Rule 11 (overspend protection), and currency matching.
    """
    project = db.scalar(select(Project).where(Project.id == project_id))
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Rule 10: Only owner or admin can log expenses
    is_admin = current_user.role == UserRole.ADMIN
    if project.owner_id != current_user.id and not is_admin:
        logger.warning(
            "Unauthorized expense log attempt: user_id=%s project_id=%s owner_id=%s",
            current_user.id, project_id, project.owner_id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only the project owner or an admin can log expenses."
        )

    # Must be approved
    if project.status != ProjectStatus.APPROVED:
        logger.warning(
            "Expense rejected for unapproved project: project_id=%s status=%s",
            project_id, project.status
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot log expenses: Project is currently in '{project.status}' status."
        )

    # Currency matching
    normalized_currency = data.currency.upper().strip()
    if normalized_currency != project.currency.upper().strip():
        logger.warning(
            "Expense currency mismatch: project=%s requires %s, got %s",
            project_id, project.currency, data.currency
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Currency mismatch: Project currency is {project.currency}, but expense is {data.currency}."
        )

    # Rule 11: Overspend protection (cannot spend more than amount_raised)
    total_spent_query = select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.project_id == project_id)
    current_spent = db.scalar(total_spent_query) or 0
    remaining_balance = project.amount_raised - current_spent

    if current_spent + data.amount > project.amount_raised:
        logger.warning(
            "Overspend attempt rejected: project_id=%s requested=%s available_balance=%s amount_raised=%s",
            project_id, data.amount, remaining_balance, project.amount_raised
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot log expense: requested amount ({data.amount}) exceeds "
                f"remaining unspent balance ({remaining_balance} {project.currency})."
            )
        )

    try:
        expense = Expense(
            project_id=project_id,
            amount=data.amount,
            currency=normalized_currency,
            category=data.category.value if hasattr(data.category, "value") else str(data.category),
            description=data.description,
            receipt_url=data.receipt_url,
            spent_at=data.spent_at or datetime.now(timezone.utc),
        )
        db.add(expense)
        db.commit()
        db.refresh(expense)

        logger.info(
            "Expense logged successfully: expense_id=%s project_id=%s amount=%s category=%s",
            expense.id, project_id, expense.amount, expense.category
        )
        return expense

    except Exception as exc:
        db.rollback()
        logger.error("Transaction rollback during expense creation: error=%s", exc)
        raise


def list_project_expenses(db: Session, project_id: uuid.UUID) -> list[Expense]:
    """Returns all expenses for a project ordered by date spent."""
    project = db.scalar(select(Project).where(Project.id == project_id))
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    stmt = select(Expense).where(Expense.project_id == project_id).order_by(Expense.spent_at.desc())
    return list(db.scalars(stmt).all())


def create_progress_report(
    db: Session,
    project_id: uuid.UUID,
    current_user: User,
    data: ProgressReportCreateRequest,
) -> ProgressReport:
    """
    Publishes an impact progress update for an approved project.
    Enforces Rule 10 (ownership).
    """
    project = db.scalar(select(Project).where(Project.id == project_id))
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Rule 10: Only owner or admin can publish reports
    is_admin = current_user.role == UserRole.ADMIN
    if project.owner_id != current_user.id and not is_admin:
        logger.warning(
            "Unauthorized progress report attempt: user_id=%s project_id=%s owner_id=%s",
            current_user.id, project_id, project.owner_id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only the project owner or an admin can publish progress reports."
        )

    # Must be approved
    if project.status != ProjectStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot publish progress report: Project is currently in '{project.status}' status."
        )

    try:
        report = ProgressReport(
            project_id=project_id,
            title=data.title,
            content=data.content,
            milestone_completed=data.milestone_completed,
            media_url=data.media_url,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        logger.info(
            "Progress report published successfully: report_id=%s project_id=%s title=%s",
            report.id, project_id, report.title
        )
        return report

    except Exception as exc:
        db.rollback()
        logger.error("Transaction rollback during progress report creation: error=%s", exc)
        raise


def list_project_progress_reports(db: Session, project_id: uuid.UUID) -> list[ProgressReport]:
    """Returns all published progress reports for a project ordered by creation date."""
    project = db.scalar(select(Project).where(Project.id == project_id))
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    stmt = select(ProgressReport).where(ProgressReport.project_id == project_id).order_by(ProgressReport.created_at.desc())
    return list(db.scalars(stmt).all())


def get_financial_audit(db: Session, project_id: uuid.UUID) -> dict:
    """
    Calculates project-level financial transparency totals:
    total raised, total spent, remaining balance, and expenditure percentage.
    """
    project = db.scalar(select(Project).where(Project.id == project_id))
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    total_spent_query = select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.project_id == project_id)
    total_spent = db.scalar(total_spent_query) or 0

    amount_raised = project.amount_raised
    unspent_balance = max(0, amount_raised - total_spent)

    expenditure_pct = round((total_spent / amount_raised * 100), 2) if amount_raised > 0 else 0.0
    funding_pct = round((amount_raised / project.funding_target * 100), 2) if project.funding_target > 0 else 0.0

    return {
        "project_id": project_id,
        "funding_target": project.funding_target,
        "amount_raised": amount_raised,
        "total_spent": total_spent,
        "unspent_balance": unspent_balance,
        "expenditure_percentage": expenditure_pct,
        "funding_percentage": funding_pct,
        "currency": project.currency,
    }
