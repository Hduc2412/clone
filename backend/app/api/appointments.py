from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.db.database import (
    list_appointments,
    list_notifications,
    mark_notification_read,
    update_appointment_status,
)
from app.auth.security import get_current_user


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
    "rescheduled",
    "cancelled",
}


class AppointmentStatusRequest(BaseModel):
    status: str
    employee_name: str = Field(min_length=2, max_length=100)
    result_note: str | None = Field(default=None, max_length=1000)


@appointment_router.get("")
async def get_appointments(
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    return await list_appointments(status=status, limit=limit)


@appointment_router.patch("/{appointment_code}/status")
async def change_appointment_status(
    appointment_code: str,
    request: AppointmentStatusRequest,
):
    if request.status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Trạng thái không hợp lệ: {request.status}",
        )

    appointment = await update_appointment_status(
        appointment_code=appointment_code,
        status=request.status,
        employee_name=request.employee_name,
        result_note=request.result_note,
    )
    if appointment is None:
        raise HTTPException(
            status_code=409,
            detail="Lịch không tồn tại hoặc không thể chuyển sang trạng thái này.",
        )
    return appointment


@notification_router.get("")
async def get_notifications(
    unread_only: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
):
    return await list_notifications(unread_only=unread_only, limit=limit)


@notification_router.patch("/{appointment_code}/read")
async def read_notification(appointment_code: str):
    updated = await mark_notification_read(appointment_code)
    if not updated:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo chưa đọc.")
    return {"appointment_code": appointment_code, "is_read": True}
