from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.modules.projects.models import ProjectStatus, ReviewAction

class ProjectCreateRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=20)
    category: str = Field(..., min_length=2, max_length=100)
    location: str = Field(..., min_length=2, max_length=255)
    funding_target: int = Field(..., gt=0, description="Funding target in minor units (e.g. kobo/cents)")
    currency: str = Field(default="NGN", max_length=10)
    beneficiary_target: str = Field(..., min_length=3, max_length=255)
    intended_outcomes: str = Field(..., min_length=10)
    budget_breakdown: str = Field(..., min_length=10)


class ProjectUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=5, max_length=255)
    description: str | None = Field(None, min_length=20)
    category: str | None = Field(None, min_length=2, max_length=100)
    location: str | None = Field(None, min_length=2, max_length=255)
    beneficiary_target: str | None = Field(None, min_length=3, max_length=255)
    intended_outcomes: str | None = Field(None, min_length=10)
    budget_breakdown: str | None = Field(None, min_length=10)


# Updating the funding target and currency is not allowed
class ProjectUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=5, max_length=255)
    description: str | None = Field(None, min_length=20)
    category: str | None = Field(None, min_length=2, max_length=100)
    location: str | None = Field(None, min_length=2, max_length=255)
    beneficiary_target: str | None = Field(None, min_length=3, max_length=255)
    intended_outcomes: str | None = Field(None, min_length=10)
    budget_breakdown: str | None = Field(None, min_length=10)


class ProjectReviewRequest(BaseModel):
    action: ReviewAction
    reason: str = Field(..., min_length=5, description="Auditable explanation for reviewer decision")


class ProjectReviewRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    reviewer_id: uuid.UUID
    action: ReviewAction
    reason: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProjectRead(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    description: str
    category: str
    location: str
    funding_target: int
    amount_raised: int
    currency: str
    beneficiary_target: str
    intended_outcomes: str
    budget_breakdown: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)