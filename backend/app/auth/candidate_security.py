"""Xác thực cho hệ khách hàng — tách hẳn khỏi xác thực nhân viên.

Hai hệ thống, hai loại danh tính, nên hai bộ token và hai cookie. Dùng chung sẽ
hỏng theo hai hướng cùng lúc: đăng nhập bên này đá văng phiên bên kia, và một
token cấp cho ứng viên có thể bị đem thử ở cửa quản trị.

Hai chốt chặn khiến token không dùng lẫn được, và cả hai đều đã có sẵn ở một
phía nên chỉ cần dựng phía còn lại cho khớp:

- Token **nhân viên** bắt buộc có `role` thuộc {admin, manager, consultant}
  (`decode_access_token`). Token ứng viên không mang `role`, nên đem sang cửa
  quản trị là bị từ chối ngay.
- Token **ứng viên** bắt buộc có `typ == "candidate"` trong phần payload. Token
  nhân viên không có khóa đó — `typ: "JWT"` nằm ở header, không phải payload —
  nên đem sang cửa khách hàng cũng bị từ chối.

Ký bằng cùng một `JWT_SECRET`. Điều đó an toàn vì phần phân biệt nằm ở nội dung
đã được ký, không phải ở khóa.
"""
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import Cookie, Depends, HTTPException

from app.auth.security import _b64decode, _b64encode, _secret
from app.core.config import settings
from app.db.candidate_accounts import get_account_by_phone


TOKEN_TYPE = "candidate"


def create_candidate_token(account: dict[str, Any]) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": account["phone"],
        "typ": TOKEN_TYPE,
        "lead": account.get("lead_code"),
        "name": account.get("full_name"),
        "iat": now,
        "exp": now + settings.candidate_session_minutes * 60,
    }
    encoded_header = _b64encode(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _b64encode(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    )
    content = f"{encoded_header}.{encoded_payload}"
    signature = _b64encode(hmac.new(_secret(), content.encode(), hashlib.sha256).digest())
    return f"{content}.{signature}"


def decode_candidate_token(token: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, signature = token.split(".")
        content = f"{encoded_header}.{encoded_payload}"
        expected = _b64encode(hmac.new(_secret(), content.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid signature")
        payload = json.loads(_b64decode(encoded_payload))
        if int(payload.get("exp", 0)) <= int(time.time()):
            raise ValueError("Expired token")
        # Không có dòng này thì một token nhân viên hợp lệ sẽ mở được cửa khách hàng.
        if payload.get("typ") != TOKEN_TYPE or not payload.get("sub"):
            raise ValueError("Invalid claims")
        return payload
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=401,
            detail="Phiên đăng nhập đã hết hạn. Bạn đăng nhập lại nhé.",
        ) from exc


async def get_current_candidate(
    token: str | None = Cookie(default=None, alias=settings.candidate_cookie_name),
) -> dict[str, Any]:
    if not token:
        raise HTTPException(status_code=401, detail="Bạn cần đăng nhập để xem hồ sơ của mình.")
    payload = decode_candidate_token(token)
    account = await get_account_by_phone(payload["sub"])
    if account is None or account.get("status") != "active":
        raise HTTPException(
            status_code=401,
            detail="Tài khoản không còn hoạt động. Bạn gọi nhân viên để được hỗ trợ nhé.",
        )
    return {key: value for key, value in account.items() if key != "password_hash"}


async def require_usable_password(
    account: dict[str, Any] = Depends(get_current_candidate),
) -> dict[str, Any]:
    """Chặn mọi trang khác khi tài khoản còn dùng mật khẩu nhân viên cấp.

    Mật khẩu ban đầu do nhân viên đọc qua điện thoại, nghĩa là ít nhất hai người
    biết nó. Để nguyên mà dùng tiếp thì tài khoản không thật sự là của riêng ứng
    viên nữa, nên bắt đổi trước khi xem được gì.
    """
    if account.get("must_change_password"):
        raise HTTPException(
            status_code=409,
            detail="Bạn đổi mật khẩu trước khi tiếp tục nhé.",
        )
    return account
