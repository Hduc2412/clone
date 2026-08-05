import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.database import get_staff_user_by_email


JWT_SECRET = os.getenv("JWT_SECRET", "").strip()
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
PASSWORD_ITERATIONS = 600_000
bearer_scheme = HTTPBearer(auto_error=False)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _b64decode(salt), int(iterations)
        )
        return hmac.compare_digest(_b64encode(digest), expected)
    except (TypeError, ValueError):
        return False


def _secret() -> bytes:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET must be configured before using authentication.")
    return JWT_SECRET.encode("utf-8")


def create_access_token(user: dict[str, Any]) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user["email"], "name": user["full_name"], "role": user["role"],
        "iat": now, "exp": now + JWT_EXPIRE_MINUTES * 60,
    }
    encoded_header = _b64encode(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _b64encode(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    )
    content = f"{encoded_header}.{encoded_payload}"
    signature = _b64encode(hmac.new(_secret(), content.encode(), hashlib.sha256).digest())
    return f"{content}.{signature}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, signature = token.split(".")
        content = f"{encoded_header}.{encoded_payload}"
        expected = _b64encode(hmac.new(_secret(), content.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid signature")
        payload = json.loads(_b64decode(encoded_payload))
        if int(payload.get("exp", 0)) <= int(time.time()):
            raise ValueError("Expired token")
        if not payload.get("sub") or payload.get("role") not in {"admin", "manager", "consultant"}:
            raise ValueError("Invalid claims")
        return payload
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.") from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bạn cần đăng nhập để tiếp tục.")
    payload = decode_access_token(credentials.credentials)
    user = await get_staff_user_by_email(payload["sub"])
    if user is None or user.get("status") != "active":
        raise HTTPException(status_code=401, detail="Tài khoản không tồn tại hoặc đã bị khóa.")
    return {key: value for key, value in user.items() if key != "password_hash"}


def require_roles(*roles: str):
    async def dependency(user: dict[str, Any] = Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Bạn không có quyền thực hiện thao tác này.")
        return user
    return dependency
