from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import AuditAction, AuditLog

logger = get_logger(__name__)


# PUBLIC_INTERFACE
def write_audit_log(
    *,
    db: Session,
    request: Request,
    action: AuditAction,
    target_type: str | None = None,
    target_id: str | None = None,
    message: str | None = None,
) -> AuditLog:
    """Persist an audit log entry for compliance-relevant actions.

    Contract:
      - Inputs: db session, request (for actor/ip/ua context), action code, optional target and message
      - Output: persisted AuditLog ORM object
      - Side effects: inserts row into audit_logs

    Data minimization:
      - `message` must not contain secrets or raw KYC document contents.
    """
    actor_user_id = getattr(request.state, "actor_user_id", None)
    actor_role = getattr(request.state, "actor_role", None)
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    row = AuditLog(
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action=action,
        target_type=target_type,
        target_id=target_id,
        message=message,
        ip_address=ip,
        user_agent=ua[:300] if ua else None,
    )
    db.add(row)
    db.flush()  # ensures ID available

    logger.info(
        "audit_log_written",
        extra={
            "action": action.value,
            "actor_user_id": actor_user_id,
            "actor_role": actor_role,
            "target_type": target_type,
            "target_id": target_id,
        },
    )
    return row
