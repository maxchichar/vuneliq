import uuid
from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session


from app.modules.donations.models import (
    Donation, 
    DonationStatus, 
    Payment, 
    PaymentStatus, 
    PaymentMethod
)
from app.modules.donations.schemas import DonationCreateRequest, PaymentSimulateRequest
from app.modules.projects.models import Project, ProjectStatus

def initiate_donation(
        db: Session, 
        project_id: uuid.UUID, 
        donor_id: uuid.UUID, 
        data: DonationCreateRequest,
        idempotency_key: str
) -> tuple[Donation, Payment]:
    """
    Creates a pending donation and payment intent in an atomic transaction.
    If ANY error occurs during write, the entire transaction is rolled back.
    Enforces Rule 1 (approved only) and Rule 2 (not suspended).
    """

    # Idempotency Check: Return existing donation if key was already processed
    if idempotency_key:
        existing_stmt = select(Donation).where(Donation.idempotency_key == idempotency_key)
        existing_donation = db.scalar(existing_stmt)
        if existing_donation:
            return existing_donation, existing_donation.payments[0]

    # Check project eligibility
    stmt = select(Project).where(Project.id == project_id)
    project = db.scalar(stmt)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


    # Rule 1: Cannot donate to unapproved projects
    if project.status != ProjectStatus.APPROVED:
        if project.status == ProjectStatus.SUSPENDED:
            # Rule 2: Cannot donate to suspended projects
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot donate: This project has been suspended."
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot donate: Project is currently in '{project.status}' status and not open for public donations."
        )

    # Atomic Write Transaction
    try:
        # Create Donation record
        donation = Donation(
            idempotency_key=idempotency_key,
            donor_id=donor_id,
            project_id=project_id,
            amount=data.amount,
            currency=data.currency.upper().strip(),
            is_anonymous=data.is_anonymous,
            status=DonationStatus.PENDING
        )
        db.add(donation)
        db.flush()

        # Create Payment record with unique reference
        reference = f"VUN-{uuid.uuid4().hex[:12].upper()}"
        payment = Payment(
            donation_id=donation.id,
            reference=reference,
            amount=data.amount,
            currency=data.currency.upper().strip(),
            status=PaymentStatus.PENDING,
            payment_method=data.payment_method.value if hasattr(data.payment_method, "value") else str(data.payment_method),
        )
        db.add(payment)

        # Atomic commit
        db.commit()
        db.refresh(donation)
        db.refresh(payment)
        return donation, payment

    except Exception: 
        # Atomic rollback
        db.rollback()
        raise

def process_payment_confirmation(
        db: Session, payment_id: uuid.UUID, data: PaymentSimulateRequest
) -> Payment:
    """
    Processes payment status updates in an atomic ACID transaction.
    Guarantees that concurrent in-flight calls and sequential replays NEVER double-credit!
    """

    payment = db.scalar(select(Payment).where(Payment.id == payment_id))
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

    donation = payment.donation
    project = donation.project

    # Rule 9: Sequential replay check
    if payment.status == PaymentStatus.SUCCEEDED:
        return payment

    try:
        if data.status == PaymentStatus.SUCCEEDED:
            provider_tx = data.provider_tx_id or f"TX-SIM-{uuid.uuid4().hex[:8].upper()}"
            stmt = (
                update(Payment)
                .where(Payment.id == payment_id, Payment.status == PaymentStatus.PENDING)
                .values(status=PaymentStatus.SUCCEEDED, provider_tx_id=provider_tx)
            )
            result = db.execute(stmt)

            if result.rowcount == 1:
                donation.status = DonationStatus.SUCCEEDED
                project.amount_raised = Project.amount_raised + donation.amount

                db.add(donation)
                db.add(project)
                db.commit()
                db.refresh(payment)
                return payment

            else:
                db.rollback()
                db.refresh(payment)
                return payment

        elif data.status in (PaymentStatus.FAILED, PaymentStatus.CANCELLED):
            stmt = (
                update(Payment)
                .where(Payment.id == payment_id, Payment.status == PaymentStatus.PENDING)
                .values(status=data.status)
            )
            result = db.execute(stmt)
            if result.rowcount == 1:
                donation.status = (
                    DonationStatus.FAILED if data.status == PaymentStatus.FAILED else DonationStatus.CANCELLED
                )
                db.add(donation)
                db.commit()
                db.refresh(payment)

                return payment

            else:
                db.rollback()
                db.refresh(payment)
                return payment

        return payment

    except Exception:
        db.rollback()
        raise


def get_donation_by_id(db: Session, donation_id: uuid.UUID) -> Donation | None:
    stmt = select(Donation).where(Donation.id == donation_id)
    return db.scalar(stmt)

def list_donor_donations(db: Session, donor_id: uuid.UUID) -> list[Donation]:
    """Rule 4: Returns only donations belonging to the requesting donor."""
    stmt = select(Donation).where(Donation.donor_id == donor_id).order_by(Donation.created_at.desc())

    return list(db.scalars(stmt).all())

def get_project_donations_summary(db: Session, project_id: uuid.UUID) -> dict:
    stmt = select(
        func.count(Donation.id).label("total_count"),
        func.coalesce(func.sum(Donation.amount), 0).lable("total_amount")
    ).where(
        Donation.project_id == project_id,
        Donation.status == DonationStatus.SUCCEEDED
    )

    result  = db.execute(stmt).one()
    return {
        "project_id": project_id,
        "total_successful_donations": result.total_count,
        "total_amount_raised": result.total_amount,
        "currency": "NGN",
    }
