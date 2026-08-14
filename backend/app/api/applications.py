import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from app.auth.security import get_current_user, require_roles
from app.db.database import (
    create_application_event,
    create_recruitment_application,
    get_managed_lead,
    get_recruitment_application,
    get_staff_user_by_email,
    list_application_events,
    list_recruitment_applications,
    update_recruitment_application,
)
from app.services.audit_service import audit_action


router = APIRouter(prefix="/applications", tags=["Recruitment applications"])

APPLICATION_STATUSES = {
    "draft",
    "collecting_documents",
    "screening",
    "eligible",
    "training",
    "waiting_interview",
    "passed",
    "visa_processing",
    "ready_departure",
    "departed",
    "rejected",
    "withdrawn",
    "cancelled",
}
CLOSED_STATUSES = {"departed", "rejected", "withdrawn", "cancelled"}
STATUS_TRANSITIONS = {
    "draft": {"collecting_documents", "withdrawn", "cancelled"},
    "collecting_documents": {"screening", "withdrawn", "cancelled"},
    "screening": {"collecting_documents", "eligible", "rejected", "withdrawn", "cancelled"},
    "eligible": {"training", "waiting_interview", "withdrawn", "cancelled"},
    "training": {"waiting_interview", "withdrawn", "cancelled"},
    "waiting_interview": {"training", "passed", "rejected", "withdrawn", "cancelled"},
    "passed": {"visa_processing", "withdrawn", "cancelled"},
    "visa_processing": {"ready_departure", "withdrawn", "cancelled"},
    "ready_departure": {"departed", "withdrawn", "cancelled"},
    "departed": set(),
    "rejected": set(),
    "withdrawn": set(),
    "cancelled": set(),
}


class ApplicationCreateRequest(BaseModel):
    lead_code: str = Field(min_length=4, max_length=30)
    assigned_to: str | None = Field(default=None, max_length=150)
    destination: str | None = Field(default=None, max_length=100)
    japanese_level: str | None = Field(default=None, max_length=30)
    qualification: str | None = Field(default=None, max_length=150)
    note: str | None = Field(default=None, max_length=1000)


class ApplicationUpdateRequest(BaseModel):
    status: str | None = None
    assigned_to: str | None = Field(default=None, max_length=150)
    destination: str | None = Field(default=None, max_length=100)
    japanese_level: str | None = Field(default=None, max_length=30)
    qualification: str | None = Field(default=None, max_length=150)
    note: str | None = Field(default=None, max_length=1000)


def _can_access(application: dict, current_user: dict) -> bool:
    return current_user["role"] in {"admin", "manager"} or (
        application.get("assigned_to") == current_user["email"]
    )


def _validate_status_transition(current_status: str, next_status: str) -> None:
    if next_status == current_status:
        return
    if next_status not in STATUS_TRANSITIONS.get(current_status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Không thể chuyển hồ sơ từ {current_status} sang {next_status}.",
        )


async def _validate_assignee(email: str | None) -> str | None:
    if not email:
        return None
    normalized = email.strip().lower()
    user = await get_staff_user_by_email(normalized)
    if user is None or user.get("status") != "active":
        raise HTTPException(status_code=400, detail="Nhân viên phụ trách không hợp lệ.")
    return normalized


async def _record_event(
    application_code: str,
    action: str,
    current_user: dict,
    details: dict | None = None,
) -> None:
    await create_application_event(
        {
            "application_code": application_code,
            "action": action,
            "actor_email": current_user["email"],
            "actor_name": current_user["full_name"],
            "details": details or {},
        }
    )


@router.get("")
async def applications(
    status: str | None = None,
    lead_code: str | None = Query(default=None, max_length=30),
    assigned_to: str | None = Query(default=None, max_length=150),
    active_only: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    current_user=Depends(get_current_user),
):
    if status and status not in APPLICATION_STATUSES:
        raise HTTPException(status_code=400, detail="Trạng thái hồ sơ không hợp lệ.")
    if current_user["role"] == "consultant":
        assigned_to = current_user["email"]
    return await list_recruitment_applications(
        status=status,
        lead_code=lead_code,
        assigned_to=assigned_to,
        active_only=active_only,
        limit=limit,
    )


@router.get("/{application_code}")
async def application_detail(
    application_code: str,
    current_user=Depends(get_current_user),
):
    application = await get_recruitment_application(application_code)
    if application is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ tuyển dụng.")
    if not _can_access(application, current_user):
        raise HTTPException(status_code=403, detail="Bạn không được truy cập hồ sơ này.")
    return application


@router.get("/{application_code}/events")
async def application_history(
    application_code: str,
    current_user=Depends(get_current_user),
):
    application = await get_recruitment_application(application_code)
    if application is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ tuyển dụng.")
    if not _can_access(application, current_user):
        raise HTTPException(status_code=403, detail="Bạn không được truy cập hồ sơ này.")
    return await list_application_events(application_code)


@router.post("", status_code=201)
async def create_application(
    payload: ApplicationCreateRequest,
    http_request: Request,
    current_user=Depends(require_roles("admin", "manager")),
):
    lead = await get_managed_lead(payload.lead_code)
    if lead is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy khách hàng/lead.")
    assigned_to = await _validate_assignee(payload.assigned_to or lead.get("assigned_to"))
    application_code = f"HS-{secrets.token_hex(3).upper()}"
    document = {
        **payload.model_dump(),
        "application_code": application_code,
        "lead_code": lead["lead_code"],
        "customer_name": lead["customer_name"],
        "phone": lead["phone"],
        "assigned_to": assigned_to,
        "status": "draft",
        "is_active": True,
    }
    try:
        application = await create_recruitment_application(document)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=409,
            detail="Khách hàng đang có một hồ sơ tuyển dụng hoạt động.",
        ) from exc
    await _record_event(application_code, "created", current_user, {"status": "draft"})
    await audit_action(
        http_request, "application.created", actor=current_user,
        target_type="recruitment_application", target_id=application_code,
    )
    return application


@router.patch("/{application_code}")
async def update_application(
    application_code: str,
    payload: ApplicationUpdateRequest,
    http_request: Request,
    current_user=Depends(get_current_user),
):
    existing = await get_recruitment_application(application_code)
    if existing is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ tuyển dụng.")
    if not _can_access(existing, current_user):
        raise HTTPException(status_code=403, detail="Bạn không được cập nhật hồ sơ này.")
    fields = payload.model_dump(exclude_unset=True)
    if fields.get("status") and fields["status"] not in APPLICATION_STATUSES:
        raise HTTPException(status_code=400, detail="Trạng thái hồ sơ không hợp lệ.")
    if fields.get("status"):
        _validate_status_transition(existing["status"], fields["status"])
    if "assigned_to" in fields:
        if current_user["role"] not in {"admin", "manager"}:
            raise HTTPException(status_code=403, detail="Chỉ Admin/Manager được phân công hồ sơ.")
        fields["assigned_to"] = await _validate_assignee(fields["assigned_to"])
    if fields.get("status"):
        fields["is_active"] = fields["status"] not in CLOSED_STATUSES
    try:
        updated = await update_recruitment_application(
            application_code,
            fields,
            expected_status=existing["status"],
            owner_email=(
                current_user["email"] if current_user["role"] == "consultant" else None
            ),
        )
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=409,
            detail="Khách hàng đã có một hồ sơ tuyển dụng hoạt động khác.",
        ) from exc
    if updated is None:
        raise HTTPException(
            status_code=409,
            detail="Hồ sơ đã thay đổi hoặc không còn được giao cho bạn. Vui lòng tải lại.",
        )
    changed_fields = sorted(key for key in fields if key != "is_active")
    event_details = {"changed_fields": changed_fields}
    if "status" in fields:
        event_details.update({"old_status": existing["status"], "new_status": fields["status"]})
    await _record_event(application_code, "updated", current_user, event_details)
    await audit_action(
        http_request, "application.updated", actor=current_user,
        target_type="recruitment_application", target_id=application_code,
        details=event_details,
    )
    return updated
