from datetime import datetime, timezone
from enum import Enum
import uuid
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base


class DonationStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PaymentMethod(str, Enum):
    SIMULATED = "SIMULATED"
    CARD = "CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    USSD = "USSD"


class Donation(Base):
    __tablename__ = "donations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    donor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"),index=True, nullable=False
    )

    # Financial amount stored in integer minor units (e.g. kobo/cents)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="NGN", nullable=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[DonationStatus] = mapped_column(String(50), default=DonationStatus.PENDING, index=True, nullable=False)
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

    # Relationships
    donor = relationship("app.modules.identity.models.User")
    project = relationship("app.modules.projects.models.Project")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="donation", cascade="all, delete-orphan")



class Payment(Base):
    """Tracks payment gateway transaction attempts and references."""
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    donation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("donations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reference: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    provider_tx_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="NGN", nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        String(50), default=PaymentStatus.PENDING, index=True, nullable=False
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(String(50), default=PaymentMethod.SIMULATED, nullable=False)
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

    donation: Mapped["Donation"] = relationship("Donation", back_populates="payments")