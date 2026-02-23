from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class AdminKycListItem(BaseModel):
    id: str = Field(..., description="KYC submission ID.")
    user_id: str = Field(..., description="User ID.")
    user_email: EmailStr = Field(..., description="User email.")
    status: str = Field(..., description="KYC status.")
    submitted_at: datetime | None = Field(None, description="Submitted timestamp.")
    updated_at: datetime = Field(..., description="Updated timestamp.")


class AdminKycListResponse(BaseModel):
    items: list[AdminKycListItem] = Field(default_factory=list, description="KYC submissions.")
    total: int = Field(..., description="Total matching items.")


class AdminDecisionRequest(BaseModel):
    decision: str = Field(..., description="Decision: 'approve' or 'reject'.")
    rejection_reason: str | None = Field(None, description="Required when rejecting.")


class AdminUserUpdateRequest(BaseModel):
    is_active: bool | None = Field(None, description="Enable/disable user.")
    role: str | None = Field(None, description="Set role (user/admin).")


class AdminUserResponse(BaseModel):
    id: str = Field(..., description="User ID.")
    email: EmailStr = Field(..., description="User email.")
    role: str = Field(..., description="User role.")
    is_email_verified: bool = Field(..., description="Email verified.")
    is_active: bool = Field(..., description="Active flag.")
    created_at: datetime = Field(..., description="Created timestamp.")


class AuditLogItem(BaseModel):
    id: str = Field(..., description="Audit log ID.")
    actor_user_id: str | None = Field(None, description="Actor user id if present.")
    actor_role: str | None = Field(None, description="Actor role if present.")
    action: str = Field(..., description="Action code.")
    target_type: str | None = Field(None, description="Target type.")
    target_id: str | None = Field(None, description="Target id.")
    message: str | None = Field(None, description="Message.")
    ip_address: str | None = Field(None, description="IP address.")
    user_agent: str | None = Field(None, description="User agent.")
    created_at: datetime = Field(..., description="Timestamp.")
