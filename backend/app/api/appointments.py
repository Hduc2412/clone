from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from pymongo.errors import DuplicateKeyError

from app.db.database import (
    assign_appointment,
    find_appointment_conflict,
    get_appointment_by_code,
    get_staff_user_by_email,
    list_appointment_events,
    list_appointments,
    list_notifications,
    list_staff_users,
    mark_notification_read,
    reschedule_appointment,
    update_appointment_status,
)
from app.auth.security import get_current_user, require_roles


appointment_router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"],
    dependencies=[Depends(get_current_user)],
)
notification_router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
    dependencies=[Depends(get_current_user)],
)

ALLOWED_STATUSES = {
    "confirmed",
    "completed",
    "unreachable",
    "cancelled",
}


class AppointmentStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    result_note: str | None = Field(default=None, max_length=1000)


class AppointmentAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assigned_to: str = Field(min_length=5, max_length=150)


class AppointmentRescheduleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    appointment_date: date
    appointment_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    note: str | None = Field(default=None, max_length=1000)


def validate_appointment_slot(appointment_date: date, appointment_time: str) -> None:
    local_today = datetime.now(timezone(timedelta(hours=7))).date()
    if appointment_date < local_today:
        raise HTTPException(status_code=400, detail="Không thể đổi sang ngày đã qua.")
    if appointment_date.weekday() == 6:
        raise HTTPException(status_code=400, detail="Chủ Nhật không nhận lịch tư vấn.")
    try:
        hour, minute = (int(value) for value in appointment_time.split(":"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Giờ hẹn không hợp lệ.") from exc
    total_minutes = hour * 60 + minute
    in_morning = 8 * 60 <= total_minutes <= 11 * 60 + 30
    in_afternoon = 13 * 60 + 30 <= total_minutes <= 17 * 60
    if minute > 59 or not (in_morning or in_afternoon):
        raise HTTPException(
            status_code=400,
            detail="Giờ nhận lịch là 08:00–11:30 hoặc 13:30–17:00.",
        )


async def require_appointment_access(
    appointment_code: str,
    current_user: dict,
) -> dict:
    appointment = await get_appointment_by_code(appointment_code)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch hẹn.")
    if (
        current_user["role"] == "consultant"
        and appointment.get("assigned_to") != current_user["email"]
    ):
        raise HTTPException(
            status_code=403,
            detail="Bạn chỉ được thao tác trên lịch hẹn được giao cho mình.",
        )
    return appointment


@appointment_router.get("")
async def get_appointments(
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    assigned_to: str | None = Query(default=None, max_length=150),
    limit: int = Query(default=100, ge=1, le=500),
    current_user=Depends(get_current_user),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="Ngày bắt đầu phải trước ngày kết thúc.")
    effective_assigned_to = (
        current_user["email"]
        if current_user["role"] == "consultant"
        else assigned_to
    )
    return await list_appointments(
        status=status,
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
        assigned_to=effective_assigned_to,
        limit=limit,
    )


@appointment_router.patch("/{appointment_code}/status")
async def change_appointment_status(
    appointment_code: str,
    request: AppointmentStatusRequest,
    current_user=Depends(get_current_user),
):
    if request.status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Trạng thái không hợp lệ: {request.status}",
        )

    await require_appointment_access(appointment_code, current_user)
    appointment = await update_appointment_status(
        appointment_code=appointment_code,
        status=request.status,
        actor=current_user,
        result_note=request.result_note,
        required_assigned_to=(
            current_user["email"] if current_user["role"] == "consultant" else None
        ),
    )
    if appointment is None:
        raise HTTPException(
            status_code=409,
            detail="Lịch không tồn tại hoặc không thể chuyển sang trạng thái này.",
        )
    return appointment


@appointment_router.get("/assignees")
async def get_assignees(
    _current_user=Depends(require_roles("admin", "manager")),
):
    users = await list_staff_users(limit=500)
    return [
        user
        for user in users
        if user.get("status") == "active"
        and user.get("role") in {"manager", "consultant"}
    ]


@appointment_router.patch("/{appointment_code}/assignment")
async def change_appointment_assignment(
    appointment_code: str,
    request: AppointmentAssignmentRequest,
    current_user=Depends(require_roles("admin", "manager")),
):
    assignee = await get_staff_user_by_email(request.assigned_to.strip().lower())
    if assignee is None or assignee.get("role") not in {"manager", "consultant"}:
        raise HTTPException(status_code=400, detail="Nhân viên được phân công không hợp lệ.")
    appointment = await assign_appointment(
        appointment_code=appointment_code,
        assignee=assignee,
        actor=current_user,
    )
    if appointment is None:
        raise HTTPException(
            status_code=409,
            detail="Lịch không tồn tại hoặc đã kết thúc nên không thể phân công.",
        )
    return appointment


@appointment_router.patch("/{appointment_code}/reschedule")
async def change_appointment_schedule(
    appointment_code: str,
    request: AppointmentRescheduleRequest,
    current_user=Depends(get_current_user),
):
    appointment_date = request.appointment_date.isoformat()
    await require_appointment_access(appointment_code, current_user)
    validate_appointment_slot(request.appointment_date, request.appointment_time)
    conflict = await find_appointment_conflict(
        appointment_code,
        appointment_date,
        request.appointment_time,
    )
    if conflict is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Trùng với lịch {conflict['appointment_code']} trong cùng khung giờ.",
        )
    try:
        appointment = await reschedule_appointment(
            appointment_code=appointment_code,
            appointment_date=appointment_date,
            appointment_time=request.appointment_time,
            actor=current_user,
            note=request.note,
            required_assigned_to=(
                current_user["email"] if current_user["role"] == "consultant" else None
            ),
        )
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Khách hàng đã có lịch ở khung giờ này.") from exc
    if appointment is None:
        raise HTTPException(
            status_code=409,
            detail="Lịch không tồn tại hoặc đã kết thúc nên không thể đổi.",
        )
    return appointment


@appointment_router.get("/{appointment_code}/events")
async def get_appointment_events(
    appointment_code: str,
    limit: int = Query(default=100, ge=1, le=500),
    current_user=Depends(get_current_user),
):
    await require_appointment_access(appointment_code, current_user)
    return await list_appointment_events(appointment_code, limit=limit)


@notification_router.get("")
async def get_notifications(
    unread_only: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    current_user=Depends(get_current_user),
):
    assigned_to = (
        current_user["email"] if current_user["role"] == "consultant" else None
    )
    return await list_notifications(
        unread_only=unread_only,
        assigned_to=assigned_to,
        limit=limit,
    )


@notification_router.patch("/{appointment_code}/read")
async def read_notification(
    appointment_code: str,
    current_user=Depends(get_current_user),
):
    await require_appointment_access(appointment_code, current_user)
    updated = await mark_notification_read(appointment_code)
    if not updated:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo chưa đọc.")
    return {"appointment_code": appointment_code, "is_read": True}
