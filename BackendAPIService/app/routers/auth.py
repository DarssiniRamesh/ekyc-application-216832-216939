from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.models import AuditAction, User, UserRole
from app.db.session import get_db
from app.schemas.auth import MeResponse, RegisterRequest, TokenResponse
from app.security.deps import AuthContext, get_current_auth
from app.security.jwt import create_access_token
from app.security.passwords import hash_password, verify_password
from app.services.audit_service import write_audit_log

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=MeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new end-user account",
    description="Creates a new user account with role=user. Email verification is tracked but delivery is out of scope.",
    operation_id="register_user",
)
# PUBLIC_INTERFACE
def register_user(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)) -> MeResponse:
    """Register an end-user.

    Raises:
        409 if email already exists.
    """
    existing = db.query(User).filter(User.email == payload.email).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=payload.email, password_hash=hash_password(payload.password), role=UserRole.user)
    db.add(user)
    db.flush()

    # Set actor context for audit
    request.state.actor_user_id = user.id
    request.state.actor_role = user.role.value
    write_audit_log(db=db, request=request, action=AuditAction.register, target_type="user", target_id=user.id)

    return MeResponse(
        id=user.id,
        email=user.email,
        role=user.role.value,
        is_email_verified=user.is_email_verified,
        is_active=user.is_active,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and obtain JWT access token",
    description="Authenticates a user and returns a bearer JWT.",
    operation_id="login",
)
# PUBLIC_INTERFACE
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Login endpoint using OAuth2PasswordRequestForm (username=email).

    Raises:
        401 on invalid credentials or inactive user.
    """
    user = db.query(User).filter(User.email == form.username).one_or_none()
    if user is None or not user.is_active or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Set actor for audit
    request.state.actor_user_id = user.id
    request.state.actor_role = user.role.value
    write_audit_log(db=db, request=request, action=AuditAction.login, target_type="user", target_id=user.id)

    token = create_access_token(subject=user.id, role=user.role.value)
    return TokenResponse(access_token=token, token_type="bearer")


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Get current user",
    description="Returns the current authenticated user's profile.",
    operation_id="auth_me",
)
# PUBLIC_INTERFACE
def me(ctx: AuthContext = Depends(get_current_auth)) -> MeResponse:
    """Return the current authenticated user's profile."""
    u = ctx.user
    return MeResponse(id=u.id, email=u.email, role=u.role.value, is_email_verified=u.is_email_verified, is_active=u.is_active)


@router.post(
    "/verify-email",
    response_model=MeResponse,
    summary="Mark current user's email as verified (placeholder)",
    description=(
        "Marks the user's email as verified. Real email delivery/token verification is not available from current sources, "
        "so this endpoint acts as a placeholder for the workflow state."
    ),
    operation_id="verify_email_placeholder",
)
# PUBLIC_INTERFACE
def verify_email_placeholder(
    request: Request, ctx: AuthContext = Depends(get_current_auth), db: Session = Depends(get_db)
) -> MeResponse:
    """Mark the current user's email as verified.

    Note: In production, this should validate a signed verification token delivered via email.
    """
    user = ctx.user
    user.is_email_verified = True
    db.add(user)
    db.flush()

    write_audit_log(db=db, request=request, action=AuditAction.email_verify, target_type="user", target_id=user.id)
    return MeResponse(
        id=user.id,
        email=user.email,
        role=user.role.value,
        is_email_verified=user.is_email_verified,
        is_active=user.is_active,
    )
