"""Tài khoản đăng nhập của ứng viên vào hệ khách hàng.

Khác `staff_users` ở ba điểm đáng nhớ:

- **Định danh bằng số điện thoại**, không phải email. Ứng viên đi điều dưỡng
  Nhật phần lớn là lao động trẻ ở tỉnh; số điện thoại thì ai cũng có và nhân
  viên vốn đã gọi, còn email thì nhiều người không lập hoặc không bao giờ mở.
- **Không tự đăng ký được.** Tài khoản chỉ sinh ra khi nhân viên bấm cấp, sau
  khi hồ sơ đã được tiếp nhận. Mở cho tự đăng ký thì bảng khách hàng đầy tài
  khoản rác không gắn với hồ sơ nào.
- **Mật khẩu đầu tiên là do nhân viên đọc qua điện thoại**, nên bắt buộc đổi ở
  lần đăng nhập đầu (`must_change_password`).

Số điện thoại lưu ở dạng đã chuẩn hóa để `0912 345 678`, `+84912345678` và
`0912345678` không thành ba tài khoản khác nhau.
"""
import secrets
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, ReturnDocument

from app.auth.security import hash_password
from app.db.common import get_db, now


COLLECTION = "candidate_accounts"

STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"

# Bỏ 0/O/1/I/l khỏi bộ ký tự. Mật khẩu này được **đọc qua điện thoại**, và
# "số không hay chữ O" là câu hỏi lại tốn thêm một phút mỗi cuộc gọi.
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
INITIAL_PASSWORD_LENGTH = 8


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[COLLECTION].create_index("phone", unique=True)
    await db[COLLECTION].create_index("lead_code")
    await db[COLLECTION].create_index([("created_at", ASCENDING)])


def generate_initial_password() -> str:
    """Mật khẩu ban đầu, đủ để đọc qua điện thoại mà không đoán được.

    Tám ký tự từ bộ 31 ký tự cho khoảng 10^12 khả năng — quá thừa cho một mật
    khẩu dùng đúng một lần rồi bắt đổi, mà vẫn đọc xong trong một hơi.
    """
    return "".join(secrets.choice(_ALPHABET) for _ in range(INITIAL_PASSWORD_LENGTH))


async def get_account_by_phone(phone: str) -> dict[str, Any] | None:
    return await get_db()[COLLECTION].find_one({"phone": phone}, {"_id": 0})


async def get_account_by_lead(lead_code: str) -> dict[str, Any] | None:
    return await get_db()[COLLECTION].find_one({"lead_code": lead_code}, {"_id": 0})


async def create_account(
    *,
    phone: str,
    lead_code: str | None,
    full_name: str | None,
    password: str,
    created_by: str,
) -> dict[str, Any]:
    document = {
        "phone": phone,
        "lead_code": lead_code,
        "full_name": full_name,
        "password_hash": hash_password(password),
        "must_change_password": True,
        "status": STATUS_ACTIVE,
        "created_by": created_by,
        "created_at": now(),
        "updated_at": now(),
        "last_login_at": None,
    }
    await get_db()[COLLECTION].insert_one(dict(document))
    document.pop("_id", None)
    return document


async def reset_password(phone: str, password: str, *, by: str) -> dict[str, Any] | None:
    """Nhân viên cấp lại mật khẩu cho ứng viên quên mật khẩu.

    Đặt lại `must_change_password` để lần đăng nhập sau ứng viên phải tự chọn
    mật khẩu mới — nếu không thì mật khẩu nhân viên đọc qua điện thoại sẽ ở lại
    vĩnh viễn.
    """
    return await get_db()[COLLECTION].find_one_and_update(
        {"phone": phone},
        {
            "$set": {
                "password_hash": hash_password(password),
                "must_change_password": True,
                "status": STATUS_ACTIVE,
                "updated_at": now(),
                "password_reset_by": by,
            }
        },
        projection={"_id": 0},
        return_document=ReturnDocument.AFTER,
    )


async def set_password(phone: str, password: str) -> dict[str, Any] | None:
    """Ứng viên tự đổi mật khẩu. Sau bước này tài khoản mới thật sự của riêng họ."""
    return await get_db()[COLLECTION].find_one_and_update(
        {"phone": phone},
        {
            "$set": {
                "password_hash": hash_password(password),
                "must_change_password": False,
                "updated_at": now(),
            }
        },
        projection={"_id": 0},
        return_document=ReturnDocument.AFTER,
    )


async def record_login(phone: str) -> None:
    await get_db()[COLLECTION].update_one(
        {"phone": phone}, {"$set": {"last_login_at": now()}}
    )


def public_view(account: dict[str, Any]) -> dict[str, Any]:
    """Thứ trả về cho chính ứng viên. Không bao giờ kèm băm mật khẩu."""
    return {
        "phone": account.get("phone"),
        "full_name": account.get("full_name"),
        "must_change_password": bool(account.get("must_change_password")),
    }
