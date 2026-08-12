from datetime import UTC, date, datetime, time

from fastapi import APIRouter, Depends, Query

from app.auth.security import require_roles
from app.db.database import list_audit_logs


router = APIRouter(prefix="/audit-logs", tags=["Audit logs"])


@router.get("")
async def audit_logs(
    actor_email: str | None = Query(default=None, max_length=150),
    action: str | None = Query(default=None, max_length=100),
    outcome: str | None = Query(default=None, pattern="^(success|failure)$"),
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    _current_user=Depends(require_roles("admin", "manager")),
):
    start = datetime.combine(date_from, time.min, tzinfo=UTC) if date_from else None
    end = datetime.combine(date_to, time.max, tzinfo=UTC) if date_to else None
    return await list_audit_logs(
        actor_email=actor_email,
        action=action,
        outcome=outcome,
        date_from=start,
        date_to=end,
        limit=limit,
    )
