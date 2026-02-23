from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import AuditAction, AuditLog, KycStatus, KycSubmission, User, UserRole
from app.db.session import get_db
from app.schemas.admin import (
    AdminDecisionRequest,
    AdminKycListItem,
    AdminKycListResponse,
    AdminUserResponse,
    AdminUserUpdateRequest,
    AuditLogItem,
)
from app.security.deps import AuthContext, require_admin
from app.services.audit_service import write_audit_log

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/kyc",
    response_model=AdminKycListResponse,
    summary="List KYC submissions (admin)",
    description="Lists KYC submissions with basic filtering and search.",
    operation_id="admin_list_kyc",
)
# PUBLIC_INTERFACE
def list_kyc(
    request: Request,
    status_filter: str | None = Query(None, description="Filter by status."),
    q: str | None = Query(None, description="Search by user email or submission id."),
    limit: int = Query(50, ge=1, le=200, description="Page size."),
    offset: int = Query(0, ge=0, description="Offset for pagination."),
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminKycListResponse:
    """List KYC submissions for admin dashboard."""
    query = db.query(KycSubmission, User).join(User, KycSubmission.user_id == User.id)

    if status_filter:
        try:
            status_enum = KycStatus(status_filter)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status filter") from e
        query = query.filter(KycSubmission.status == status_enum)

    if q:
        query = query.filter(or_(User.email.ilike(f"%{q}%"), KycSubmission.id.ilike(f"%{q}%")))

    total = query.count()
    rows = query.order_by(KycSubmission.updated_at.desc()).limit(limit).offset(offset).all()

    write_audit_log(db=db, request=request, action=AuditAction.admin_list_kyc, target_type="kyc_submission", target_id=None)

    items = [
        AdminKycListItem(
            id=sub.id,
            user_id=user.id,
            user_email=user.email,
            status=sub.status.value,
            submitted_at=sub.submitted_at,
            updated_at=sub.updated_at,
        )
        for sub, user in rows
    ]
    return AdminKycListResponse(items=items, total=total)


@router.post(
    "/kyc/{submission_id}/decision",
    summary="Approve or reject a KYC submission",
    description="Records an approval/rejection decision. If rejecting, requires rejection_reason.",
    operation_id="admin_decide_kyc",
)
# PUBLIC_INTERFACE
def decide_kyc(
    submission_id: str,
    payload: AdminDecisionRequest,
    request: Request,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Approve or reject a KYC submission."""
    sub = db.get(KycSubmission, submission_id)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    if sub.status not in {KycStatus.submitted, KycStatus.under_review}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Submission not in reviewable state")

    decision = payload.decision.strip().lower()
    sub.reviewed_at = datetime.utcnow()

    if decision == "approve":
        sub.status = KycStatus.approved
        sub.rejection_reason = None
        db.add(sub)
        db.flush()
        write_audit_log(
            db=db,
            request=request,
            action=AuditAction.admin_approve,
            target_type="kyc_submission",
            target_id=sub.id,
        )
        return {"id": sub.id, "status": sub.status.value}

    if decision == "reject":
        if not payload.rejection_reason:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rejection_reason is required")
        sub.status = KycStatus.rejected
        sub.rejection_reason = payload.rejection_reason
        db.add(sub)
        db.flush()
        write_audit_log(
            db=db,
            request=request,
            action=AuditAction.admin_reject,
            target_type="kyc_submission",
            target_id=sub.id,
            message="Rejected submission (reason captured)",
        )
        return {"id": sub.id, "status": sub.status.value, "rejection_reason": sub.rejection_reason}

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="decision must be 'approve' or 'reject'")


@router.get(
    "/users",
    response_model=list[AdminUserResponse],
    summary="List users",
    description="Lists user accounts for admin user management.",
    operation_id="admin_list_users",
)
# PUBLIC_INTERFACE
def list_users(
    request: Request,
    q: str | None = Query(None, description="Search by email or id."),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminUserResponse]:
    """List users for admin management."""
    query = db.query(User)
    if q:
        query = query.filter(or_(User.email.ilike(f"%{q}%"), User.id.ilike(f"%{q}%")))
    rows = query.order_by(User.created_at.desc()).limit(limit).offset(offset).all()

    write_audit_log(db=db, request=request, action=AuditAction.admin_user_update, target_type="user", target_id=None, message="Listed users")

    return [
        AdminUserResponse(
            id=u.id,
            email=u.email,
            role=u.role.value,
            is_email_verified=u.is_email_verified,
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in rows
    ]


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Update a user account",
    description="Allows admins to set active flag and/or role.",
    operation_id="admin_update_user",
)
# PUBLIC_INTERFACE
def update_user(
    user_id: str,
    payload: AdminUserUpdateRequest,
    request: Request,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserResponse:
    """Update user account properties (admin)."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.is_active is not None:
        user.is_active = payload.is_active

    if payload.role is not None:
        try:
            user.role = UserRole(payload.role)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role") from e

    db.add(user)
    db.flush()

    write_audit_log(
        db=db,
        request=request,
        action=AuditAction.admin_user_update,
        target_type="user",
        target_id=user.id,
        message="Updated user account",
    )

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        role=user.role.value,
        is_email_verified=user.is_email_verified,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.get(
    "/audit-logs",
    response_model=list[AuditLogItem],
    summary="List audit logs",
    description="Returns recent audit log entries for compliance/investigation.",
    operation_id="admin_list_audit_logs",
)
# PUBLIC_INTERFACE
def list_audit_logs(
    request: Request,
    action: str | None = Query(None, description="Filter by action."),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AuditLogItem]:
    """List audit logs (admin only)."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)

    rows = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset).all()

    write_audit_log(
        db=db,
        request=request,
        action=AuditAction.admin_audit_list,
        target_type="audit_log",
        target_id=None,
        message="Listed audit logs",
    )

    return [
        AuditLogItem(
            id=r.id,
            actor_user_id=r.actor_user_id,
            actor_role=r.actor_role,
            action=r.action.value,
            target_type=r.target_type,
            target_id=r.target_id,
            message=r.message,
            ip_address=r.ip_address,
            user_agent=r.user_agent,
            created_at=r.created_at,
        )
        for r in rows
    ]
