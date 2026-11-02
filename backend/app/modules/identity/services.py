from datetime import datetime, timedelta, timezone
import uuid
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.modules.identity.models import RefreshToken, User, UserRole
from app.modules.identity.schemas import UserRegisterRequest
from app.shared.config import settings
from app.shared.security import generate_secure_token, hash_password, verify_password


def get_user_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(User.email == email.lower().strip())
    return db.scalar(stmt)

def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    stmt = select(User).where(User.id == user_id)
    return db.scalar(stmt)

def create_user(db: Session, request: UserRegisterRequest) -> User:
    assigned_role = request.role
    if assigned_role == UserRole.ADMIN:
        assigned_role = UserRole.DONOR

    user = User(
        email=request.email.lower().strip(),
        hashed_password=hash_password(request.password),
        full_name=request.full_name.strip(),
        role=assigned_role
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user

def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_refresh_token(db: Session, user_id: uuid.UUID) -> str:
    """Generates a secure refresh token and arecords it in the database."""
    token_str = generate_secure_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    token_record = RefreshToken(
        user_id=user_id,
        token=token_str,
        expires_at=expires_at
    )
    db.add(token_record)
    db.commit()
    return token_str

def verify_and_use_refresh_token(db: Session, token_str: str) -> User | None:
    """
    Validates that a refresh token exists, is not revoked, and has not expired.
    Returns the associated User if valid, None otherwise.
    """
    stmt = select(RefreshToken).where(
        RefreshToken.token == token_str,
        RefreshToken.revoked.is_(False)
    )
    record = db.scalar(stmt)
    if not record:
        return None

    # Check expiration
    now = datetime.now(timezone.utc)
    expires_at = record.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        return None

    return record.user

def revoke_refresh_token(db: Session, token_str: str) -> bool:
    """Marks a single refresh token as revoked (used on logout)."""
    stmt = (
        update(RefreshToken)
        .where(RefreshToken.token == token_str)
        .values(revoked=True)
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount > 0

def revoke_all_user_tokens(db: Session, user_id: uuid.UUID) -> int:
    """Revokes all active refresh tokens for a user (used on logout-all)."""
    stmt = (
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )
    result = db.execute(stmt)
    db.commit()

    return result.rowcount

def cleanup_stale_tokens(db: Session) -> int:
    """Deletes all expired or revoked refresh tokens from the database."""
    now = datetime.now(timezone.utc)
    stmt = delete(RefreshToken).where(
        (RefreshToken.expires_at <= now) | (RefreshToken.revoked.is_(True))
    )
    result = db.execute(stmt)
    db.commit()

    return result.rowcount