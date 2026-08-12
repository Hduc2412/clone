from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.auth.security import create_access_token, get_current_user, hash_password, verify_password
from app.db.database import get_staff_user_by_email, record_audit_log, record_staff_login, update_staff_password
from app.core.rate_limit import login_ip_rate_key, login_rate_key, rate_limiter
from app.core.config import settings


router = APIRouter(prefix="/auth", tags=["Authentication"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for") if "headers" in request.scope else None
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else None


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
        await record_audit_log(
            action="auth.login",
            outcome="failure",
            actor_email=email,
            target_type="staff_user",
            target_id=email,
            ip_address=_client_ip(http_request),
            details={"reason": "invalid_credentials"},
        )
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
    await record_audit_log(
        action="auth.login",
        outcome="success",
        actor_email=user["email"],
        actor_name=user["full_name"],
        actor_role=user["role"],
        target_type="staff_user",
        target_id=user["email"],
        ip_address=_client_ip(http_request),
    )
    return {"user": safe_user}


@router.post("/logout", status_code=204)
async def logout(
    http_request: Request,
    response: Response,
    current_user=Depends(get_current_user),
):
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    await record_audit_log(
        action="auth.logout",
        outcome="success",
        actor_email=current_user["email"],
        actor_name=current_user["full_name"],
        actor_role=current_user["role"],
        target_type="staff_user",
        target_id=current_user["email"],
        ip_address=_client_ip(http_request),
    )


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return user


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    http_request: Request,
    current_user=Depends(get_current_user),
):
    user = await get_staff_user_by_email(current_user["email"])
    if user is None or not verify_password(request.current_password, user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng.")
    if request.current_password == request.new_password:
        raise HTTPException(status_code=400, detail="Mật khẩu mới phải khác mật khẩu hiện tại.")
    await update_staff_password(user["email"], hash_password(request.new_password))
    await record_audit_log(
        action="auth.password_changed",
        outcome="success",
        actor_email=current_user["email"],
        actor_name=current_user["full_name"],
        actor_role=current_user["role"],
        target_type="staff_user",
        target_id=current_user["email"],
        ip_address=_client_ip(http_request),
    )
    return {"message": "Đổi mật khẩu thành công."}
