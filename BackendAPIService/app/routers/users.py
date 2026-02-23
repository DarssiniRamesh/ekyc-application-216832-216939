from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.schemas.auth import MeResponse
from app.security.deps import AuthContext, get_current_auth

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=MeResponse,
    status_code=status.HTTP_200_OK,
    summary="Alias for /auth/me",
    description="Convenience endpoint for frontend user profile retrieval.",
    operation_id="users_me",
)
# PUBLIC_INTERFACE
def users_me(ctx: AuthContext = Depends(get_current_auth)) -> MeResponse:
    """Return current user profile (alias)."""
    u = ctx.user
    return MeResponse(id=u.id, email=u.email, role=u.role.value, is_email_verified=u.is_email_verified, is_active=u.is_active)
