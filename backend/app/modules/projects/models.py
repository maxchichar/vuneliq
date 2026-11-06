from datetime import datetime, timezone
from enum import Enum
import uuid
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class ReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"
    SUSPEND = "suspend"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    location: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    
    # Financial target stored in integer minor units (e.g. 5000000 kobo = 50,000 NGN)
    funding_target: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount_raised: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="NGN", nullable=False)

    beneficiary_target: Mapped[str] = mapped_column(String(255), nullable=False)
    intended_outcomes: Mapped[str] = mapped_column(Text, nullable=False)
    budget_breakdown: Mapped[str] = mapped_column(Text, nullable=False)  # JSON or itemized text
    
    status: Mapped[ProjectStatus] = mapped_column(
        String(50), default=ProjectStatus.PENDING_REVIEW, index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    owner = relationship("app.modules.identity.models.User")
    reviews = relationship("ProjectReview", back_populates="project", cascade="all, delete-orphan")


class ProjectReview(Base):
    """Audit log of decisions made by reviewers on a project."""
    __tablename__ = "project_reviews"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    action: Mapped[ReviewAction] = mapped_column(String(50), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    project = relationship("Project", back_populates="reviews")
    reviewer = relationship("app.modules.identity.models.User")