import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import Cookie, Depends, HTTPException

from app.core.config import settings
from app.db.database import get_staff_user_by_email


PASSWORD_ITERATIONS = 600_000


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
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET must be configured before using authentication.")
    return settings.jwt_secret.encode("utf-8")


def dau_tai_khoan(user: dict[str, Any]) -> int | None:
    """Dấu của **một bản ghi** tài khoản: thời điểm tạo, tính đến mili giây.

    Email không đủ để nhận diện tài khoản. Xóa một nhân viên rồi tạo tài khoản mới
    cùng email — cho người khác, hay chỉ là tạo lại — thì token cũ, vốn chỉ mang
    email, đăng nhập thẳng vào tài khoản mới với mọi quyền của nó. Kiểm trên trình
    duyệt ngày 06/10: cookie của một consultant tạm đã xóa dùng lại được ngay sau
    khi tạo lại tài khoản cùng email.

    Không dùng `_id` vì mọi hàm đọc nhân viên đều bỏ nó; `created_at` thì đổi mỗi
    lần tạo lại, và ai giữ token cũ cũng không đoán được nó tới từng mili giây.
    Mili giây chứ không micro giây: MongoDB chỉ lưu tới mili giây.
    """
    tao_luc = user.get("created_at")
    if not isinstance(tao_luc, datetime):
        return None
    if tao_luc.tzinfo is None:
        # MongoDB trả giờ UTC không gắn múi. Không gắn thì `timestamp()` hiểu nhầm
        # là giờ máy, và cùng một bản ghi cho hai dấu khác nhau trên hai máy chủ.
        tao_luc = tao_luc.replace(tzinfo=timezone.utc)
    return int(tao_luc.timestamp() * 1000)


def create_access_token(user: dict[str, Any]) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user["email"],
        "name": user["full_name"],
        "role": user["role"],
        "acc": dau_tai_khoan(user),
        "iat": now,
        "exp": now + settings.jwt_expire_minutes * 60,
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
        raise HTTPException(
            status_code=401,
            detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
        ) from exc


async def get_user_pending_password(
    token: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict[str, Any]:
    """Nhận diện nhân viên, **chưa** xét việc còn nợ đổi mật khẩu.

    Chỉ ba endpoint được dùng bản này: xem mình là ai, đổi mật khẩu, và đăng
    xuất. Nếu chúng cũng bị chặn như phần còn lại thì một tài khoản vừa bị đặt
    lại mật khẩu sẽ không có đường nào thoát ra — bị chặn vì chưa đổi, mà cũng
    không gọi được endpoint đổi.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Bạn cần đăng nhập để tiếp tục.")
    payload = decode_access_token(token)
    user = await get_staff_user_by_email(payload["sub"])
    if user is None or user.get("status") != "active":
        raise HTTPException(
            status_code=401,
            detail="Tài khoản không tồn tại hoặc đã bị khóa.",
        )
    # Token phải thuộc đúng bản ghi tài khoản này, không chỉ đúng email — xem
    # `dau_tai_khoan`. Token cấp trước bản sửa không mang `acc`, nên mọi phiên đang
    # mở phải đăng nhập lại một lần: cái giá chấp nhận được để đóng lỗ này.
    if payload.get("acc") != dau_tai_khoan(user):
        raise HTTPException(
            status_code=401,
            detail="Phiên đăng nhập này thuộc một tài khoản cũ. Bạn đăng nhập lại nhé.",
        )
    # Token cấp trước lần đổi mật khẩu gần nhất coi như đã chết. Không có chốt
    # này thì đặt lại mật khẩu chỉ chặn được lần đăng nhập sau, còn phiên đang
    # mở của người chiếm tài khoản vẫn chạy tiếp tới khi hết hạn.
    changed_at = user.get("password_changed_at")
    if changed_at is not None and int(payload.get("iat", 0)) < int(changed_at):
        raise HTTPException(
            status_code=401,
            detail="Mật khẩu đã được đổi. Bạn đăng nhập lại nhé.",
        )
    return {key: value for key, value in user.items() if key != "password_hash"}


async def get_current_user(
    user: dict[str, Any] = Depends(get_user_pending_password),
) -> dict[str, Any]:
    """Nhân viên đã đăng nhập **và** đã tự đặt mật khẩu riêng.

    Chặn ở đây, tại một chỗ duy nhất mà mọi router đều đi qua, thay vì gắn thêm
    một dependency vào từng router. Quản trị viên đặt lại mật khẩu cho ai thì
    người đó nhận mật khẩu mặc định — một dãy ai cũng biết — nên để họ dùng tiếp
    hệ thống trước khi đổi là để ngỏ tài khoản có quyền thật.
    """
    if user.get("must_change_password"):
        raise HTTPException(
            status_code=409,
            detail="Bạn phải đổi mật khẩu trước khi dùng hệ thống.",
        )
    return user


def require_roles(*roles: str):
    async def dependency(user: dict[str, Any] = Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(
                status_code=403,
                detail="Bạn không có quyền thực hiện thao tác này.",
            )
        return user

    return dependency
