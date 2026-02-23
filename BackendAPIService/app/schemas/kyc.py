from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class KycDraftUpsertRequest(BaseModel):
    full_name: str | None = Field(None, description="Full legal name.")
    date_of_birth: str | None = Field(None, description="Date of birth (ISO string).")
    address: str | None = Field(None, description="Residential address.")


class KycSubmissionResponse(BaseModel):
    id: str = Field(..., description="KYC submission ID.")
    user_id: str = Field(..., description="Owner user ID.")
    status: str = Field(..., description="KYC status.")
    full_name: str | None = Field(None, description="Full legal name.")
    date_of_birth: str | None = Field(None, description="DOB (ISO string).")
    address: str | None = Field(None, description="Residential address.")
    rejection_reason: str | None = Field(None, description="Rejection reason if rejected.")
    submitted_at: datetime | None = Field(None, description="Time submitted.")
    reviewed_at: datetime | None = Field(None, description="Time reviewed.")
    created_at: datetime = Field(..., description="Created timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class DocumentInfo(BaseModel):
    id: str = Field(..., description="Document ID.")
    filename: str = Field(..., description="Original filename.")
    content_type: str = Field(..., description="MIME type.")
    size_bytes: int = Field(..., description="Size in bytes.")
    uploaded_at: datetime = Field(..., description="Upload timestamp.")


class KycDetailResponse(KycSubmissionResponse):
    documents: list[DocumentInfo] = Field(default_factory=list, description="Documents attached to the submission.")


class KycSubmitResponse(BaseModel):
    id: str = Field(..., description="KYC submission ID.")
    status: str = Field(..., description="New status (submitted).")
    submitted_at: datetime = Field(..., description="Submission timestamp.")
