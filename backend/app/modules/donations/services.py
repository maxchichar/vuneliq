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
from app.shared.logging import get_module_logger

logger = get_module_logger("donations")

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

    # Idempotency Check & Payload Mutation Guard: Return existing donation if key was already processed
    if idempotency_key:
        existing_stmt = select(Donation).where(Donation.idempotency_key == idempotency_key)
        existing_donation = db.scalar(existing_stmt)
        if existing_donation:
            if existing_donation.donor_id != donor_id:
                logger.warning(
                    "Idempotency key collision/hijack attempt: key=%s requester=%s owner=%s",
                    idempotency_key, donor_id, existing_donation.donor_id
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Idempotency key belongs to another user."
                )

            normalised_currency = data.currency.upper().strip()
            if (
                existing_donation.project_id != project_id
                or existing_donation.amount != data.amount
                or existing_donation.currency != normalised_currency
            ):
                logger.warning(
                    "Idempotency payload mutation rejected: key=%s amount=%s project=%s",
                    idempotency_key, data.amount, project_id
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key already used with different request parameters."
                )

            logger.info("Idempotent replay: returning existing donation id=%s", existing_donation.id)
            return existing_donation, existing_donation.payments[0]

    # Check project eligibility
    stmt = select(Project).where(Project.id == project_id)
    project = db.scalar(stmt)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


    # Currency match validation
    normalised_currency = data.currency.upper().strip()
    if normalised_currency != project.currency.upper().strip():
        logger.warning(
            "Currency mismatch: project=%s accepts %s, but received %s",
            project_id, project.currency, data.currency
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Currency mismatch: Project accepts {project.currency}, but received {data.currency}."
        )

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
            currency=normalised_currency,
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
            currency=normalised_currency,
            status=PaymentStatus.PENDING,
            payment_method=data.payment_method.value if hasattr(data.payment_method, "value") else str(data.payment_method),
        )
        db.add(payment)

        # Atomic commit
        db.commit()
        db.refresh(donation)
        db.refresh(payment)
        logger.info(
            "Donation initiated successfully: donation_id=%s payment_id=%s amount=%s currency=%s project_id=%s",
            donation.id, payment.id, donation.amount, donation.currency, project_id
        )
        return donation, payment

    except Exception as exc: 
        # Atomic rollback
        db.rollback()
        logger.error("Atomic transaction rollback during donation initiation: error=%s", exc)
        raise

def process_payment_confirmation(
        db: Session, payment_id: uuid.UUID, data: PaymentSimulateRequest
) -> Payment:
    """
    Processes payment status updates in an atomic ACID transaction.
    Guarantees that concurrent in-flight calls and sequential replays NEVER double-credit!
    Guards against mutating already-terminal failed/cancelled payments.
    """

    payment = db.scalar(select(Payment).where(Payment.id == payment_id))
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

    donation = payment.donation
    project = donation.project

    # Rule 9: Sequential replay check for succeede payment
    if payment.status == PaymentStatus.SUCCEEDED:
        return payment

    # Guard: Terminal failure/cancellation cannot be overwritten
    if payment.status in (PaymentStatus.FAILED, PaymentStatus.CANCELLED):
        if data.status != payment.status:
            logger.warning(
                "Invalid terminal state transition rejected: payment_id=%s current=%s requested=%s",
                payment.id, payment.status, data.status
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition payment from terminal status '{payment.status}'."
            )
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
                logger.info(
                    "Payment succeeded and project credited: payment_id=%s amount=%s project_id=%s amount_raised=%s",
                    payment.id, donation.amount, project.id, project.amount_raised
                )
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
                logger.info("Payment marked as %s: payment_id=%s", data.status.value, payment.id)

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
    """Calculates public verified aggregates. Checks project existence and fixes typo."""
    project = db.scalar(select(Project).where(Project.id == project_id))
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    stmt = select(
        func.count(Donation.id).label("total_count"),
        func.coalesce(func.sum(Donation.amount), 0).label("total_amount")
    ).where(
        Donation.project_id == project_id,
        Donation.status == DonationStatus.SUCCEEDED
    )

    result  = db.execute(stmt).one()
    return {
        "project_id": project_id,
        "total_successful_donations": result.total_count,
        "total_amount_raised": result.total_amount,
        "currency": project.currency,
    }
