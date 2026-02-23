from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address (unique).")
    password: str = Field(..., min_length=8, description="User password (min 8 chars).")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address.")
    password: str = Field(..., description="User password.")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token.")
    token_type: str = Field("bearer", description="Token type (bearer).")


class MeResponse(BaseModel):
    id: str = Field(..., description="User ID.")
    email: EmailStr = Field(..., description="User email.")
    role: str = Field(..., description="User role.")
    is_email_verified: bool = Field(..., description="Whether email is verified.")
    is_active: bool = Field(..., description="Whether account is active.")
