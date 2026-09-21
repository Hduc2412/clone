"""Quên mật khẩu: gửi yêu cầu, và người có quyền đặt lại.

Hai luồng đối xứng nhau, khác đúng một chỗ — ai được xử lý:

    ứng viên quên  → yêu cầu vào hàng đợi → **nhân viên** đặt lại
    nhân viên quên → yêu cầu vào hàng đợi → **quản trị viên** đặt lại

Không có bước tự phục hồi qua SMS hay email, và đó là chủ ý: hệ thống chưa có
cổng gửi tin. Người thật xác minh người thật — nhân viên vốn đã gọi cho ứng
viên, còn quản trị viên thì ngồi cùng công ty với nhân viên.

Đặt lại xong, mật khẩu trở về **dãy mặc định ai cũng biết**, nên bản ghi luôn
kèm cờ bắt buộc đổi. Hai thứ đó phải đi cùng nhau; tách ra là để ngỏ tài khoản.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.auth.security import get_current_user, hash_password, require_roles
from app.core.config import settings
from app.core.phone import normalize_vietnamese_phone
from app.core.rate_limit import client_ip, rate_limiter
from app.db import candidate_accounts as accounts
from app.db import password_resets as store
from app.db.database import (
    get_staff_user_by_email,
    set_staff_password_flag,
    update_staff_password,
)
from app.services.assignment import is_privileged
from app.services.audit_service import audit_action


public_router = APIRouter(prefix="/quen-mat-khau", tags=["Quên mật khẩu (công khai)"])
router = APIRouter(
    prefix="/yeu-cau-mat-khau",
    tags=["Yêu cầu đặt lại mật khẩu"],
    dependencies=[Depends(get_current_user)],
)

# Cùng một câu cho mọi trường hợp: gửi thành công, số không tồn tại, hoặc đã có
# yêu cầu đang chờ. Tách ba câu ra là biến ô này thành công cụ dò xem số nào đã
# có tài khoản.
SENT_MESSAGE = (
    "Đã gửi yêu cầu tới nhân viên. Bạn chờ được liên hệ rồi đăng nhập lại "
    "bằng mật khẩu mặc định nhé."
)
SENT_MESSAGE_STAFF = (
    "Đã gửi yêu cầu tới quản trị viên. Bạn chờ được cấp lại mật khẩu mặc định."
)


class CandidateResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone: str = Field(min_length=6, max_length=20)
    note: str | None = Field(default=None, max_length=300)

    @field_validator("phone", mode="before")
    @classmethod
    def _phone(cls, value: object) -> str:
        return normalize_vietnamese_phone(str(value or ""))


class StaffResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=150)
    note: str | None = Field(default=None, max_length=300)

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, value: object) -> str:
        return str(value or "").strip().lower()


# --- Gửi yêu cầu (chưa đăng nhập) ---


@public_router.post("/ung-vien")
async def request_candidate_reset(
    payload: CandidateResetRequest, http_request: Request
) -> dict[str, str]:
    rate_limiter.check(f"reset-request:{client_ip(http_request)}", limit=5, window_seconds=600)
    account = await accounts.get_account_by_phone(payload.phone)
    if account is not None:
        await store.create_request(
            subject_type=store.SUBJECT_CANDIDATE,
            subject_id=payload.phone,
            full_name=account.get("full_name"),
            note=payload.note,
        )
    return {"message": SENT_MESSAGE}


@public_router.post("/nhan-vien")
async def request_staff_reset(
    payload: StaffResetRequest, http_request: Request
) -> dict[str, str]:
    rate_limiter.check(f"reset-request:{client_ip(http_request)}", limit=5, window_seconds=600)
    user = await get_staff_user_by_email(payload.email)
    if user is not None:
        await store.create_request(
            subject_type=store.SUBJECT_STAFF,
            subject_id=payload.email,
            full_name=user.get("full_name"),
            note=payload.note,
        )
    return {"message": SENT_MESSAGE_STAFF}


# --- Xử lý yêu cầu (sau đăng nhập) ---


def _visible_types(current_user: dict[str, Any]) -> tuple[str, ...]:
    """Nhân viên thường chỉ thấy yêu cầu của ứng viên.

    Yêu cầu của đồng nghiệp là việc của quản trị viên: cho tư vấn viên đặt lại
    mật khẩu cho nhau là mở đường để một người mượn tài khoản người khác.
    """
    if is_privileged(current_user):
        return (store.SUBJECT_CANDIDATE, store.SUBJECT_STAFF)
    return (store.SUBJECT_CANDIDATE,)


@router.get("")
async def list_pending(
    status: str | None = Query(default=store.STATUS_PENDING, max_length=20),
    limit: int = Query(default=100, ge=1, le=300),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    items = await store.list_requests(
        subject_types=_visible_types(current_user), status=status, limit=limit
    )
    return {"items": items, "count": len(items)}


@router.post("/{code}/dat-lai")
async def handle_reset(
    code: str,
    http_request: Request,
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Đặt mật khẩu về dãy mặc định và bắt người đó đổi ở lần đăng nhập tới."""
    request = await store.get_request(code)
    if request is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu này.")
    if request.get("status") != store.STATUS_PENDING:
        raise HTTPException(status_code=409, detail="Yêu cầu này đã được xử lý rồi.")

    subject_type = request["subject_type"]
    subject_id = request["subject_id"]

    if subject_type == store.SUBJECT_STAFF and not is_privileged(current_user):
        raise HTTPException(
            status_code=403,
            detail="Chỉ Quản lý và Quản trị viên được đặt lại mật khẩu cho nhân viên.",
        )

    password = settings.default_password
    if subject_type == store.SUBJECT_CANDIDATE:
        updated = await accounts.reset_password(
            subject_id, password, by=current_user["email"]
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="Tài khoản ứng viên không còn tồn tại.")
    else:
        if not await update_staff_password(subject_id, hash_password(password)):
            raise HTTPException(status_code=404, detail="Tài khoản nhân viên không còn tồn tại.")
        # Bắt buộc đổi. Thiếu dòng này thì tài khoản có quyền thật nằm nguyên ở
        # mật khẩu mặc định cho tới khi người ta nhớ ra mà đổi.
        await set_staff_password_flag(subject_id, True)

    closed = await store.mark_done(code, handled_by=current_user["email"])
    if closed is None:
        # Người khác vừa xử lý xong giữa hai bước. Mật khẩu đã về mặc định rồi
        # nên không có gì hỏng, chỉ là không nên báo thành công hai lần.
        raise HTTPException(status_code=409, detail="Yêu cầu này vừa được người khác xử lý.")

    await audit_action(
        http_request,
        "password.reset",
        actor=current_user,
        target_type=f"{subject_type}_account",
        target_id=subject_id,
        details={"request_code": code},
    )
    return {
        "message": "Đã đặt lại mật khẩu về mặc định.",
        "subject_type": subject_type,
        "subject_id": subject_id,
        "full_name": request.get("full_name"),
        "default_password": password,
    }
