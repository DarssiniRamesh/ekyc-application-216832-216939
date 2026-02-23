from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()


# PUBLIC_INTERFACE
def create_access_token(*, subject: str, role: str, expires_minutes: int | None = None) -> str:
    """Create a signed JWT access token.

    Contract:
      - Inputs: subject (user_id), role (string), optional expiration override
      - Output: compact JWT string
      - Errors: raises ValueError on invalid params

    Args:
        subject: User identifier.
        role: Role string (e.g., 'user', 'admin').
        expires_minutes: Optional expiration.

    Returns:
        Encoded JWT access token.
    """
    if not subject:
        raise ValueError("subject is required")
    if not role:
        raise ValueError("role is required")

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes if expires_minutes is not None else settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


# PUBLIC_INTERFACE
def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Raises:
        JWTError: if invalid/expired.
    """
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
