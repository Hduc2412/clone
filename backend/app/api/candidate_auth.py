"""Đăng nhập cho hệ khách hàng.

Router này công khai (chưa đăng nhập mới gọi được `login`), nhưng **không** nằm
dưới `/public/*` cùng nhóm với phần tư vấn: nhóm kia định danh bằng mã phiên
trình duyệt và không có khái niệm tài khoản. Để chung sẽ khiến người đọc mã
nguồn tưởng hai thứ cùng một mức bảo vệ.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.auth.candidate_security import create_candidate_token, get_current_candidate
from app.auth.security import verify_password
from app.core.config import settings
from app.core.phone import normalize_vietnamese_phone
from app.core.rate_limit import client_ip, rate_limiter
from app.db import candidate_accounts as accounts


router = APIRouter(prefix="/tai-khoan", tags=["Tài khoản khách hàng"])

MIN_PASSWORD_LENGTH = 8


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone: str = Field(min_length=6, max_length=20)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("phone", mode="before")
    @classmethod
    def _phone(cls, value: object) -> str:
        # Hàm này tự ném ValueError kèm câu tiếng Việt khi số sai, và pydantic
        # chuyển thẳng câu đó ra lỗi 422. Nhờ vậy `0912 345 678` với
        # `+84912345678` đăng nhập được vào cùng một tài khoản.
        return normalize_vietnamese_phone(str(value or ""))


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=200)

    @field_validator("new_password")
    @classmethod
    def _not_too_simple(cls, value: str) -> str:
        # Không dựng cả một bộ luật mật khẩu. Chỉ chặn đúng thứ hay gặp nhất:
        # gõ lặp một ký tự cho đủ độ dài.
        if len(set(value)) < 4:
            raise ValueError("Mật khẩu cần ít nhất 4 ký tự khác nhau.")
        return value


def _set_session_cookie(response: Response, account: dict[str, Any]) -> None:
    response.set_cookie(
        key=settings.candidate_cookie_name,
        value=create_candidate_token(account),
        max_age=settings.candidate_session_minutes * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/dang-nhap")
async def login(
    payload: LoginRequest,
    response: Response,
    http_request: Request,
) -> dict[str, Any]:
    # Giới hạn theo IP **và** theo số máy: chặn cả kiểu dò một số với nhiều mật
    # khẩu lẫn kiểu dò một mật khẩu qua nhiều số.
    rate_limiter.check(f"candidate-login:{client_ip(http_request)}", limit=10, window_seconds=300)
    rate_limiter.check(f"candidate-login-phone:{payload.phone}", limit=5, window_seconds=300)

    account = await accounts.get_account_by_phone(payload.phone)
    # Cùng một câu trả lời cho "chưa có tài khoản" và "sai mật khẩu". Tách hai
    # câu ra là biến trang đăng nhập thành công cụ dò xem số nào đã đăng ký.
    if (
        account is None
        or account.get("status") != accounts.STATUS_ACTIVE
        or not verify_password(payload.password, account.get("password_hash", ""))
    ):
        raise HTTPException(
            status_code=401,
            detail="Số điện thoại hoặc mật khẩu không đúng.",
        )

    await accounts.record_login(payload.phone)
    rate_limiter.reset(f"candidate-login-phone:{payload.phone}")
    _set_session_cookie(response, account)
    return accounts.public_view(account)


@router.post("/dang-xuat")
async def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(
        key=settings.candidate_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    return {"message": "Bạn đã đăng xuất."}


@router.get("/toi")
async def me(account: dict[str, Any] = Depends(get_current_candidate)) -> dict[str, Any]:
    return accounts.public_view(account)


@router.post("/doi-mat-khau")
async def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    http_request: Request,
    account: dict[str, Any] = Depends(get_current_candidate),
) -> dict[str, Any]:
    rate_limiter.check(
        f"candidate-password:{client_ip(http_request)}", limit=10, window_seconds=300
    )
    stored = await accounts.get_account_by_phone(account["phone"])
    if stored is None or not verify_password(
        payload.current_password, stored.get("password_hash", "")
    ):
        raise HTTPException(status_code=401, detail="Mật khẩu hiện tại không đúng.")
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=400, detail="Mật khẩu mới phải khác mật khẩu đang dùng."
        )

    updated = await accounts.set_password(account["phone"], payload.new_password)
    if updated is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    # Cấp lại cookie: token cũ vẫn hợp lệ tới khi hết hạn, nhưng phát lại ở đây
    # cho phiên hiện tại mang đúng trạng thái đã đổi mật khẩu.
    _set_session_cookie(response, updated)
    return accounts.public_view(updated)
