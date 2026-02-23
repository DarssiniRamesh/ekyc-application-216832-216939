from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.db.models import AuditAction, KycDocument, KycStatus, KycSubmission
from app.db.session import get_db
from app.schemas.kyc import (
    DocumentInfo,
    KycDetailResponse,
    KycDraftUpsertRequest,
    KycSubmitResponse,
)
from app.security.deps import AuthContext, get_current_auth
from app.services.audit_service import write_audit_log

router = APIRouter(prefix="/kyc", tags=["KYC"])


def _get_or_create_draft(db: Session, user_id: str) -> KycSubmission:
    draft = (
        db.query(KycSubmission)
        .filter(KycSubmission.user_id == user_id)
        .order_by(KycSubmission.created_at.desc())
        .first()
    )
    if draft is None:
        draft = KycSubmission(user_id=user_id, status=KycStatus.draft)
        db.add(draft)
        db.flush()
    return draft


@router.get(
    "/current",
    response_model=KycDetailResponse,
    summary="Get current user's latest KYC submission",
    description="Returns the latest KYC submission (draft/submitted/reviewed) for the authenticated user.",
    operation_id="kyc_get_current",
)
# PUBLIC_INTERFACE
def get_current_kyc(ctx: AuthContext = Depends(get_current_auth), db: Session = Depends(get_db)) -> KycDetailResponse:
    """Return the latest KYC submission for the current user."""
    sub = (
        db.query(KycSubmission)
        .filter(KycSubmission.user_id == ctx.user.id)
        .order_by(KycSubmission.created_at.desc())
        .first()
    )
    if sub is None:
        sub = _get_or_create_draft(db, ctx.user.id)

    documents = [
        DocumentInfo(
            id=d.id,
            filename=d.filename,
            content_type=d.content_type,
            size_bytes=d.size_bytes,
            uploaded_at=d.uploaded_at,
        )
        for d in sub.documents
    ]

    return KycDetailResponse(
        id=sub.id,
        user_id=sub.user_id,
        status=sub.status.value,
        full_name=sub.full_name,
        date_of_birth=sub.date_of_birth,
        address=sub.address,
        rejection_reason=sub.rejection_reason,
        submitted_at=sub.submitted_at,
        reviewed_at=sub.reviewed_at,
        created_at=sub.created_at,
        updated_at=sub.updated_at,
        documents=documents,
    )


@router.put(
    "/draft",
    response_model=KycDetailResponse,
    summary="Create/update KYC draft details",
    description="Upserts the authenticated user's latest draft submission with personal details.",
    operation_id="kyc_upsert_draft",
)
# PUBLIC_INTERFACE
def upsert_draft(
    payload: KycDraftUpsertRequest,
    request: Request,
    ctx: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
) -> KycDetailResponse:
    """Upsert KYC draft details for current user."""
    sub = _get_or_create_draft(db, ctx.user.id)
    if sub.status not in {KycStatus.draft, KycStatus.rejected}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot edit after submission")

    sub.full_name = payload.full_name
    sub.date_of_birth = payload.date_of_birth
    sub.address = payload.address
    db.add(sub)
    db.flush()

    write_audit_log(db=db, request=request, action=AuditAction.kyc_save_draft, target_type="kyc_submission", target_id=sub.id)

    return get_current_kyc(ctx=ctx, db=db)


@router.post(
    "/documents",
    response_model=DocumentInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a KYC document",
    description="Uploads a document file and attaches it to the current user's latest draft submission.",
    operation_id="kyc_upload_document",
)
# PUBLIC_INTERFACE
def upload_document(
    request: Request,
    file: UploadFile = File(...),
    ctx: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
) -> DocumentInfo:
    """Upload a KYC document for the current user."""
    sub = _get_or_create_draft(db, ctx.user.id)
    if sub.status not in {KycStatus.draft, KycStatus.rejected}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot upload after submission")

    blob = file.file.read()
    if not blob:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(blob) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File too large (max 10MB)")

    doc = KycDocument(
        submission_id=sub.id,
        filename=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(blob),
        blob=blob,
    )
    db.add(doc)
    db.flush()

    write_audit_log(
        db=db,
        request=request,
        action=AuditAction.kyc_upload_document,
        target_type="kyc_document",
        target_id=doc.id,
        message=f"Uploaded document filename={doc.filename} content_type={doc.content_type} size={doc.size_bytes}",
    )

    return DocumentInfo(
        id=doc.id,
        filename=doc.filename,
        content_type=doc.content_type,
        size_bytes=doc.size_bytes,
        uploaded_at=doc.uploaded_at,
    )


@router.post(
    "/submit",
    response_model=KycSubmitResponse,
    summary="Submit KYC for review",
    description="Transitions the current user's draft to submitted; requires email verification and basic fields.",
    operation_id="kyc_submit",
)
# PUBLIC_INTERFACE
def submit_kyc(
    request: Request,
    ctx: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
) -> KycSubmitResponse:
    """Submit a KYC draft for review."""
    if not ctx.user.is_email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email must be verified before submission")

    sub = _get_or_create_draft(db, ctx.user.id)
    if sub.status == KycStatus.submitted:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already submitted")
    if sub.status not in {KycStatus.draft, KycStatus.rejected}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid status transition")

    # Minimal server-side validation (requirements do not specify exact KYC fields)
    missing = []
    if not sub.full_name:
        missing.append("full_name")
    if not sub.date_of_birth:
        missing.append("date_of_birth")
    if not sub.address:
        missing.append("address")
    if len(sub.documents) == 0:
        missing.append("documents")
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"missing_fields": missing})

    sub.status = KycStatus.submitted
    sub.submitted_at = datetime.utcnow()
    db.add(sub)
    db.flush()

    write_audit_log(db=db, request=request, action=AuditAction.kyc_submit, target_type="kyc_submission", target_id=sub.id)

    return KycSubmitResponse(id=sub.id, status=sub.status.value, submitted_at=sub.submitted_at)
