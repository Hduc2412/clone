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
import time
from typing import Any

import secrets

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, ReturnDocument

from app.auth.security import hash_password
from app.core.config import settings
from app.db.common import get_db, now


COLLECTION = "candidate_accounts"

STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"

# Bộ chữ để sinh mật khẩu cấp tài khoản.
#
# Cố ý bỏ những ký tự nghe giống nhau hoặc nhìn giống nhau: `0/O`, `1/l/I`, `5/S`,
# `2/Z`. Dãy này được **đọc qua điện thoại**, nên một ký tự nghe nhầm là ứng viên
# gõ sai ba lần rồi gọi lại — và nhân viên thì không đọc lại được, vì máy chủ không
# lưu bản rõ.
_CHU_DE_DOC = "34679ACDEFGHJKLMNPQRTUVWXY"
DAI_MAT_KHAU_CAP = 10


def default_password() -> str:
    """Mật khẩu **một lần, sinh ngẫu nhiên** khi cấp tài khoản hoặc đặt lại.

    ## Vì sao không còn là một dãy cố định

    Trước 30/09 hàm này trả `settings.default_password`, một dãy tám số ai cũng
    biết. Nó được bù bằng hai thứ: `must_change_password` chặn tài khoản cho tới khi
    tự đặt mật khẩu mới, và hạn 72 giờ.

    Cả hai đều không bịt được lỗ thật, và chú thích trong `config.py` đã tự nhận
    điều đó: chúng bắt người đăng nhập phải đổi mật khẩu, nhưng **không xác minh
    được người đăng nhập là ai**. Ai biết số điện thoại của một tài khoản vừa cấp
    cũng gõ đúng dãy ấy, và nếu họ vào trước chủ tài khoản thì họ là người đặt mật
    khẩu mới — tức là chiếm được tài khoản, kèm CV và số điện thoại của người khác.
    Bản rà soát 30/09 xếp đây là việc phải xong **trước khi dùng dữ liệu thật**.

    Một dãy ngẫu nhiên thì người không có nó không đăng nhập được, dù biết số điện
    thoại. Đó là khác biệt duy nhất đáng kể, và nó đủ.

    ## Vẫn đọc được qua điện thoại

    `secrets.choice` trên bộ chữ đã bỏ ký tự dễ nghe nhầm. Mười ký tự là đủ để
    không đoán được mà vẫn đọc xong trong một hơi.

    ## Máy chủ không lưu bản rõ

    Giá trị này chỉ tồn tại trong đúng một phản hồi API cho nhân viên đang gọi điện.
    Không đọc lại được, và đó là chủ ý — một mật khẩu tra lại được thì không còn là
    mật khẩu. `must_change_password` vẫn giữ nguyên: sửa ở đây không được bỏ nó.
    """
    return "".join(secrets.choice(_CHU_DE_DOC) for _ in range(DAI_MAT_KHAU_CAP))


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[COLLECTION].create_index("phone", unique=True)
    await db[COLLECTION].create_index("lead_code")
    await db[COLLECTION].create_index([("created_at", ASCENDING)])


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
        "password_changed_at": int(time.time()),
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
                "password_changed_at": int(time.time()),
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
                "password_changed_at": int(time.time()),
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
