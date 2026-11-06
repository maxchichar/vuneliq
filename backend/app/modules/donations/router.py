import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.modules.donations.schemas import (
    DonationCreateRequest,
    DonationRead,
    PaymentRead,
    PaymentSimulateRequest,
    ProjectDonationsSummary
)
from app.modules.donations.services import (
    get_donation_by_id,
    get_project_donations_summary,
    initiate_donation,
    list_donor_donations,
    process_payment_confirmation
)
from app.modules.identity.models import User, UserRole
from app.shared.database import get_db
from app.shared.dependencies import get_current_user

donations_router = APIRouter(tags=["Donations"])


@donations_router.post(
    "/projects/{project_id}/donations",
    response_model=DonationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_donation(
    project_id: uuid.UUID,
    request: DonationCreateRequest,
    idempotency_key: str = Header(
        ..., 
        alias="Idempotency-key",
        min_length=8,
        description="Mandatory client-generated UUID to guarantee transaction idempotency",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Initiates a donation with Iempotency-Key protection and ACID rollback.
    """
    donation, _ = initiate_donation(
        db, project_id, current_user.id, request, idempotency_key=idempotency_key
    )
    return donation


@donations_router.post("/payments/{payment_id}/simulate-result", response_model=PaymentRead)
def simulate_payment_result(
    payment_id: uuid.UUID,
    request: PaymentSimulateRequest,
    db: Session = Depends(get_db),
): 
    """
    Simulates sandbox payment result with atomic state transition and idempotency.
    """
    return process_payment_confirmation(db, payment_id, request)

@donations_router.get("/my/donations", response_model=list[DonationRead])
def get_my_donations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rule 4: Returns private donation history for the authenticated user."""
    return list_donor_donations(db, current_user.id)


@donations_router.get("/donations/{donation_id}", response_model=DonationRead)
def get_donation_details(
    donation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rule 4: Enforces that donors can only access their own donations."""
    donation = get_donation_by_id(db, donation_id)
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")

    is_admin = current_user.role == UserRole.ADMIN
    if donation.donor_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You cannot view another donor's private donation details."
        )

    return donation


@donations_router.get(
    "/projects/{project_id}/donations/summary",
    response_model=ProjectDonationsSummary,
)
def get_project_summary(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """Publicly visible aggregate totals of verified donations for a project."""
    return get_project_donations_summary(db, project_id)