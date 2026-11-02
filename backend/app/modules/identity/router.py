from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.modules.identity.models import User, UserRole
from app.modules.identity.schemas import (
    LogoutRequest,
    TokenRefreshRequest,
    TokenRefreshResponse,
    TokenResponse,
    UserLoginRequest,
    UserRead,
    UserRegisterRequest
)
from app.modules.identity.services import (
    authenticate_user,
    cleanup_stale_tokens,
    create_refresh_token,
    create_user,
    get_user_by_email,
    revoke_all_user_tokens,
    revoke_refresh_token,
    verify_and_use_refresh_token,
)
from app.shared.database import get_db
from app.shared.dependencies import get_current_user, require_roles
from app.shared.security import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new user (donor or project_owner)."""
    existing_user = get_user_by_email(db, request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists",
        )
    return create_user(db, request)

@router.post("/login", response_model=TokenResponse)
def login(request: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticates user and returns both an access token and a refresh token."""
    user = authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": role_str, "email": user.email}
    )
    refresh_token = create_refresh_token(db, user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user,
    )

@router.post("/refresh", response_model=TokenRefreshResponse)
def refresh_token(request: TokenRefreshRequest, db: Session = Depends(get_db)):
    """Exchanges a valid refresh token for a fresh access token."""
    user = verify_and_use_refresh_token(db, request.refresh_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked refresh token",
        )

    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    
    new_access_token = create_access_token(
        data={"sub": str(user.id), "role": role_str, "email": user.email}
    )
    return TokenRefreshResponse(access_token=new_access_token, token_type="bearer")

@router.post("/logout", response_model=dict)
def logout(request: LogoutRequest, db: Session = Depends(get_db)):
    """Revokes the specified refresh token so it cannot be used again."""
    revoke_refresh_token(db, request.refresh_token)
    return {"message": "Successfully logged out of this session."}


@router.post("/logout-all", response_model=dict)
def logout_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revokes all active refresh tokens for the authenticated user (all devices)."""
    revoked_count = revoke_all_user_tokens(db, current_user.id)
    return {"message": f"Successfully logged out of all devices ({revoked_count} sessions revoked)"}


@router.get("/me", response_model=UserRead)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Returns profile of currently authenticated user."""
    return current_user

@router.delete("/stale-tokens", response_model=dict)
def prune_stale_tokens(
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Admin maintenance endpoint: prunes expired and revoked tokens from the database."""
    deleted_count = cleanup_stale_tokens(db)
    return {"message": f"Prunes {deleted_count} stale tokens"}


@router.get("/admin-only-test", response_model=dict)
def admin_only_check(current_user: User = Depends(require_roles(UserRole.ADMIN))):
    """Test endpoint demonstratinf RBAC: accessible exclusively by Admins."""
    return {"message": "Welcome Admin", "admin_email": current_user.email}