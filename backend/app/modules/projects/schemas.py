from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    title: str | None = Field(default=None, min_length=5, max_length=255)
    description: str | None = Field(default=None, min_length=20)
    category: str | None = Field(default=None, min_length=2, max_length=100)
    location: str | None = Field(default=None, min_length=2, max_length=255)
    beneficiary_target: str | None = Field(default=None, min_length=3, max_length=255)
    intended_outcomes: str | None = Field(default=None, min_length=10)
    budget_breakdown: str | None = Field(default=None, min_length=10)

    @field_validator("*", mode="before")
    @classmethod
    def reject_explicit_nulls(cls, value, info):
        """Reject explicit nulls (e.g. {'title': null}) so non-nullable columns never receive None."""
        if value is None:
            raise ValueError(f"Field '{info.field_name}' cannot be null. Omit the field if not updating.")
        return value


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