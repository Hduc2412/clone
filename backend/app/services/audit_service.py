import logging

from fastapi import Request

from app.core.rate_limit import client_ip
from app.db.database import record_audit_log


logger = logging.getLogger(__name__)


async def audit_action(
    request: Request,
    action: str,
    outcome: str = "success",
    actor: dict | None = None,
    actor_email: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict | None = None,
) -> None:
    """Best-effort audit logging that never breaks the primary business flow."""
    try:
        await record_audit_log(
            action=action,
            outcome=outcome,
            actor_email=actor.get("email") if actor else actor_email,
            actor_name=actor.get("full_name") if actor else None,
            actor_role=actor.get("role") if actor else None,
            target_type=target_type,
            target_id=target_id,
            ip_address=client_ip(request),
            details=details,
        )
    except Exception:
        logger.exception("Audit log write failed for action %s", action)
