from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.models import User, UserRole
from app.db.session import get_db
from app.security.jwt import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@dataclass(frozen=True)
class AuthContext:
    """Authenticated request context."""
    user: User
    role: UserRole


def _http_401(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _http_403(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


# PUBLIC_INTERFACE
def get_current_auth(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AuthContext:
    """Resolve the current authenticated user from Authorization bearer token."""
    try:
        payload = decode_token(token)
    except Exception as e:
        raise _http_401("Invalid or expired token") from e

    user_id = payload.get("sub")
    role = payload.get("role")
    if not user_id or not role:
        raise _http_401("Invalid token payload")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _http_401("User not found or inactive")

    # Attach context for downstream audit logging
    request.state.actor_user_id = user.id
    request.state.actor_role = user.role.value

    return AuthContext(user=user, role=user.role)


# PUBLIC_INTERFACE
def require_admin(ctx: AuthContext = Depends(get_current_auth)) -> AuthContext:
    """Ensure current user has admin role."""
    if ctx.role != UserRole.admin:
        raise _http_403("Admin privileges required")
    return ctx
