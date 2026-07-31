import re
import secrets

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from app.db.database import (
    create_managed_lead,
    create_staff_user,
    get_management_overview,
    get_messages,
    list_conversations,
    list_managed_leads,
    list_staff_users,
    update_managed_lead,
    update_staff_user,
)


router = APIRouter(prefix="/management", tags=["Management"])

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


class StaffUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    role: str | None = None
    status: str | None = None


def _validate_email(email: str) -> str:
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=400, detail="Email không hợp lệ.")
    return email.lower()


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
async def create_lead(request: LeadCreateRequest):
    lead_code = f"LD-{secrets.token_hex(3).upper()}"
    return await create_managed_lead(
        {
            "lead_code": lead_code,
            **request.model_dump(),
        }
    )


@router.patch("/leads/{lead_code}")
async def update_lead(lead_code: str, request: LeadUpdateRequest):
    fields = request.model_dump(exclude_unset=True)
    if fields.get("status") and fields["status"] not in LEAD_STATUSES:
        raise HTTPException(status_code=400, detail="Trạng thái lead không hợp lệ.")
    lead = await update_managed_lead(lead_code, fields)
    if lead is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lead.")
    return lead


@router.get("/users")
async def users(limit: int = Query(default=100, ge=1, le=500)):
    return await list_staff_users(limit=limit)


@router.post("/users", status_code=201)
async def create_user(request: StaffCreateRequest):
    if request.role not in USER_ROLES:
        raise HTTPException(status_code=400, detail="Vai trò không hợp lệ.")
    data = request.model_dump()
    data["email"] = _validate_email(data["email"])
    try:
        return await create_staff_user(data)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Email đã tồn tại.") from exc


@router.patch("/users/{email}")
async def update_user(email: str, request: StaffUpdateRequest):
    fields = request.model_dump(exclude_unset=True)
    if fields.get("role") and fields["role"] not in USER_ROLES:
        raise HTTPException(status_code=400, detail="Vai trò không hợp lệ.")
    if fields.get("status") and fields["status"] not in USER_STATUSES:
        raise HTTPException(status_code=400, detail="Trạng thái tài khoản không hợp lệ.")
    user = await update_staff_user(_validate_email(email), fields)
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")
    return user
