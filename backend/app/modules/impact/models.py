import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base


class ExpenseCategory(str, Enum):
    EQUIPMENT = "EQUIPMENT"
    LABOR = "LABOR"
    MATERIALS = "MATERIALS"
    LOGISTICS = "LOGISTICS"
    PERMITS = "PERMITS"
    OTHER = "OTHER"


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Stored in integer minor units (e.g. kobo/cents)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="NGN", nullable=False)
    category: Mapped[ExpenseCategory] = mapped_column(String(50), default=ExpenseCategory.OTHER, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    spent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    project = relationship("app.modules.projects.models.Project")


class ProgressReport(Base):
    __tablename__ = "progress_reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    milestone_completed: Mapped[str | None] = mapped_column(String(255), nullable=True)
    media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    project = relationship("app.modules.projects.models.Project")
