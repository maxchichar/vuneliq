from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.modules.donations.models import DonationStatus, PaymentStatus, PaymentMethod


class DonationCreateRequest(BaseModel):
    # Rule 6: Amount must be greater than 0
    amount: int = Field(..., gt=0, description="Amount in integer uints (e.g. 500000 kobo = 5000 NGN)")
    currency: str = Field(default="NGN", max_length=10)
    is_anonymous: bool = Field(default=False)
    payment_method: PaymentMethod = Field(default=PaymentMethod.SIMULATED)


class PaymentSimulateRequest(BaseModel):
    status: PaymentStatus = Field(..., description="Target status: succeeded, failed, or cancelled")
    provider_tx_id: str | None = Field(default=None, description="Simulated gateway transaction ID")


class PaymentRead(BaseModel):
    id: uuid.UUID
    donation_id: uuid.UUID
    reference: str
    provider_tx_id: str | None
    amount: int
    currency: str
    status: PaymentStatus
    payment_method: PaymentMethod
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DonationRead(BaseModel):
    id: uuid.UUID
    idempotency_key: str
    donor_id: uuid.UUID
    project_id: uuid.UUID
    amount: int
    currency: str
    is_anonymous: bool
    status: DonationStatus
    created_at: datetime
    payments: list[PaymentRead] = []

    model_config = ConfigDict(from_attributes=True)

class ProjectDonationsSummary(BaseModel):
    project_id: uuid.UUID
    total_successful_donations: int
    total_amount_raised: int
    currency: str