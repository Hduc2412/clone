import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from app.db.database import (
    create_managed_lead,
    create_staff_user,
    get_management_overview,
    get_staff_user_by_email,
    get_messages,
    list_conversations,
    list_managed_leads,
    list_staff_users,
    record_audit_log,
    update_managed_lead,
    update_staff_user,
)
from app.auth.security import get_current_user, hash_password, require_roles


router = APIRouter(
    prefix="/management",
    tags=["Management"],
    dependencies=[Depends(get_current_user)],
)

LEAD_STATUSES = {
    "new",
    "assigned",
    "contacted",
    "consulting",
    "qualified",
    "preparing_documents",
    "training",
    "waiting_interview",
    "passed",
    "visa_processing",
    "departed",
    "unreachable",
    "unqualified",
    "interview_failed",
    "paused",
    "cancelled",
}
USER_ROLES = {"admin", "manager", "consultant"}
USER_STATUSES = {"active", "inactive"}


class LeadCreateRequest(BaseModel):
    customer_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(pattern=r"^0\d{9,10}$")
    source: str = Field(default="manual", max_length=50)
    assigned_to: str | None = Field(default=None, max_length=100)


class LeadUpdateRequest(BaseModel):
    customer_name: str | None = Field(default=None, min_length=2, max_length=100)
    phone: str | None = Field(default=None, pattern=r"^0\d{9,10}$")
    status: str | None = None
    assigned_to: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=1000)


class StaffCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=150)
    role: str = "consultant"
    password: str = Field(min_length=8, max_length=128)


class StaffUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    role: str | None = None
    status: str | None = None


def _validate_email(email: str) -> str:
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=400, detail="Email không hợp lệ.")
    return email.lower()


async def _audit_management(
    http_request: Request,
    current_user: dict,
    action: str,
    target_type: str,
    target_id: str,
    details: dict | None = None,
) -> None:
    await record_audit_log(
        action=action,
        outcome="success",
        actor_email=current_user["email"],
        actor_name=current_user["full_name"],
        actor_role=current_user["role"],
        target_type=target_type,
        target_id=target_id,
        ip_address=http_request.client.host if http_request.client else None,
        details=details,
    )


@router.get("/overview")
async def overview():
    return await get_management_overview()


@router.get("/conversations")
async def conversations(limit: int = Query(default=100, ge=1, le=500)):
    return await list_conversations(limit=limit)


@router.get("/conversations/{session_id}")
async def conversation_detail(session_id: str):
    messages = await get_messages(session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại.")
    return {"session_id": session_id, "messages": messages}


@router.get("/leads")
async def leads(
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    return await list_managed_leads(status=status, limit=limit)


@router.post("/leads", status_code=201)
async def create_lead(
    request: LeadCreateRequest,
    http_request: Request,
    current_user=Depends(get_current_user),
):
    lead_code = f"LD-{secrets.token_hex(3).upper()}"
    lead = await create_managed_lead(
        {
            "lead_code": lead_code,
            **request.model_dump(),
        }
    )
    await _audit_management(http_request, current_user, "lead.created", "lead", lead_code)
    return lead


@router.patch("/leads/{lead_code}")
async def update_lead(
    lead_code: str,
    request: LeadUpdateRequest,
    http_request: Request,
    current_user=Depends(get_current_user),
):
    fields = request.model_dump(exclude_unset=True)
    if fields.get("status") and fields["status"] not in LEAD_STATUSES:
        raise HTTPException(status_code=400, detail="Trạng thái lead không hợp lệ.")
    lead = await update_managed_lead(lead_code, fields)
    if lead is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lead.")
    await _audit_management(
        http_request,
        current_user,
        "lead.updated",
        "lead",
        lead_code,
        {"changed_fields": sorted(fields)},
    )
    return lead


@router.get("/users", dependencies=[Depends(require_roles("admin", "manager"))])
async def users(limit: int = Query(default=100, ge=1, le=500)):
    return await list_staff_users(limit=limit)


@router.post("/users", status_code=201)
async def create_user(
    request: StaffCreateRequest,
    http_request: Request,
    current_user=Depends(require_roles("admin", "manager")),
):
    if request.role not in USER_ROLES:
        raise HTTPException(status_code=400, detail="Vai trò không hợp lệ.")
    if request.role == "admin" and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin được tạo tài khoản Admin.")
    data = request.model_dump(exclude={"password"})
    data["email"] = _validate_email(data["email"])
    data["password_hash"] = hash_password(request.password)
    try:
        user = await create_staff_user(data)
        await _audit_management(
            http_request,
            current_user,
            "staff_user.created",
            "staff_user",
            data["email"],
            {"role": data["role"]},
        )
        return user
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Email đã tồn tại.") from exc


@router.patch("/users/{email}")
async def update_user(
    email: str,
    request: StaffUpdateRequest,
    http_request: Request,
    current_user=Depends(require_roles("admin", "manager")),
):
    fields = request.model_dump(exclude_unset=True)
    if fields.get("role") and fields["role"] not in USER_ROLES:
        raise HTTPException(status_code=400, detail="Vai trò không hợp lệ.")
    if fields.get("status") and fields["status"] not in USER_STATUSES:
        raise HTTPException(status_code=400, detail="Trạng thái tài khoản không hợp lệ.")
    target = await get_staff_user_by_email(_validate_email(email))
    if target and target.get("role") == "admin" and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Manager không được sửa tài khoản Admin.")
    if fields.get("role") == "admin" and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin được cấp vai trò Admin.")
    user = await update_staff_user(_validate_email(email), fields)
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")
    await _audit_management(
        http_request,
        current_user,
        "staff_user.updated",
        "staff_user",
        _validate_email(email),
        {"changed_fields": sorted(fields)},
    )
    return user
