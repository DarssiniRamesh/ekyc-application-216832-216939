from __future__ import annotations

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# PUBLIC_INTERFACE
def hash_password(plain_password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        plain_password: Raw password.

    Returns:
        Secure hash.
    """
    return _pwd_context.hash(plain_password)


# PUBLIC_INTERFACE
def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a password against a stored hash."""
    return _pwd_context.verify(plain_password, password_hash)
