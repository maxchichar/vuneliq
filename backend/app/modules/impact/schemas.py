import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.modules.impact.models import ExpenseCategory


class ExpenseCreateRequest(BaseModel):
    amount: int = Field(
        ...,
        gt=0,
        le=10_000_000_000,
        description="Amount in integer minor units (e.g. 500000 kobo = 5000 NGN)"
    )
    currency: str = Field(default="NGN", min_length=3, max_length=10)
    category: ExpenseCategory = Field(default=ExpenseCategory.OTHER)
    description: str = Field(..., min_length=5, max_length=1000)
    receipt_url: str | None = Field(default=None, max_length=500)
    spent_at: datetime | None = Field(default=None)


class ExpenseRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    amount: int
    currency: str
    category: ExpenseCategory
    description: str
    receipt_url: str | None
    spent_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProgressReportCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    content: str = Field(..., min_length=10)
    milestone_completed: str | None = Field(default=None, max_length=255)
    media_url: str | None = Field(default=None, max_length=500)


class ProgressReportRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    content: str
    milestone_completed: str | None
    media_url: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinancialAuditRead(BaseModel):
    project_id: uuid.UUID
    funding_target: int
    amount_raised: int
    total_spent: int
    unspent_balance: int
    expenditure_percentage: float
    funding_percentage: float
    currency: str
