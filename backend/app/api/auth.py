from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.auth.security import create_access_token, get_current_user, hash_password, verify_password
from app.db.database import get_staff_user_by_email, record_staff_login, update_staff_password
from app.core.rate_limit import login_ip_rate_key, login_rate_key, rate_limiter
from app.core.config import settings


router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=150)
    password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/login")
async def login(request: LoginRequest, http_request: Request, response: Response):
    email = request.email.strip().lower()
    limit_key = login_rate_key(http_request, email)
    rate_limiter.check(login_ip_rate_key(http_request), limit=20, window_seconds=300)
    rate_limiter.check(limit_key, limit=5, window_seconds=300)
    user = await get_staff_user_by_email(email)
    if (user is None or user.get("status") != "active" or not user.get("password_hash")
            or not verify_password(request.password, user["password_hash"])):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng.")
    await record_staff_login(email)
    rate_limiter.reset(limit_key)
    safe_user = {key: value for key, value in user.items() if key != "password_hash"}
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=create_access_token(user),
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    return {"user": safe_user}


@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return user


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user=Depends(get_current_user),
):
    user = await get_staff_user_by_email(current_user["email"])
    if user is None or not verify_password(request.current_password, user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng.")
    if request.current_password == request.new_password:
        raise HTTPException(status_code=400, detail="Mật khẩu mới phải khác mật khẩu hiện tại.")
    await update_staff_password(user["email"], hash_password(request.new_password))
    return {"message": "Đổi mật khẩu thành công."}
