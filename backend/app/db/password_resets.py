"""Yêu cầu đặt lại mật khẩu, cho cả ứng viên lẫn nhân viên.

Một collection cho hai loại người thay vì hai bảng giống hệt nhau, phân biệt
bằng `subject_type`. Hai luồng chỉ khác nhau ở **ai xử lý được**:

- Ứng viên quên mật khẩu → nhân viên nào cũng đặt lại được.
- Nhân viên quên mật khẩu → chỉ quản trị viên.

Quy tắc đó nằm ở tầng API, không ở đây; file này chỉ lưu và tra.

Một điều cố ý: chỉ tạo bản ghi khi tài khoản **có thật**, nhưng phía API luôn
trả cùng một câu bất kể có hay không. Nhờ vậy hàng đợi không đầy yêu cầu cho số
điện thoại bịa, mà người gửi cũng không dò được số nào đã đăng ký.
"""
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.core.codes import PREFIX_RESET, new_code
from app.db.common import get_db, now


COLLECTION = "password_reset_requests"

SUBJECT_CANDIDATE = "candidate"
SUBJECT_STAFF = "staff"

STATUS_PENDING = "pending"
STATUS_DONE = "done"


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[COLLECTION].create_index("code", unique=True)
    await db[COLLECTION].create_index([("status", ASCENDING), ("created_at", DESCENDING)])
    # Chặn một người bấm quên mật khẩu mười lần thành mười dòng trong hàng đợi.
    # Chỉ áp cho yêu cầu đang chờ: xử lý xong thì họ được gửi yêu cầu mới.
    await db[COLLECTION].create_index(
        [("subject_type", ASCENDING), ("subject_id", ASCENDING)],
        unique=True,
        partialFilterExpression={"status": STATUS_PENDING},
    )


async def create_request(
    *,
    subject_type: str,
    subject_id: str,
    full_name: str | None,
    note: str | None,
) -> dict[str, Any] | None:
    """Ghi một yêu cầu đang chờ. Trả `None` khi người này đã có yêu cầu chờ sẵn."""
    existing = await get_db()[COLLECTION].find_one(
        {"subject_type": subject_type, "subject_id": subject_id, "status": STATUS_PENDING},
        {"_id": 0},
    )
    if existing is not None:
        return None

    document = {
        "code": new_code(PREFIX_RESET),
        "subject_type": subject_type,
        "subject_id": subject_id,
        "full_name": full_name,
        "note": note,
        "status": STATUS_PENDING,
        "created_at": now(),
        "handled_by": None,
        "handled_at": None,
    }
    await get_db()[COLLECTION].insert_one(dict(document))
    document.pop("_id", None)
    return document


async def list_requests(
    *, subject_types: tuple[str, ...], status: str | None = STATUS_PENDING, limit: int = 100
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {"subject_type": {"$in": list(subject_types)}}
    if status:
        query["status"] = status
    cursor = (
        get_db()[COLLECTION]
        .find(query, {"_id": 0})
        .sort("created_at", DESCENDING)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def get_request(code: str) -> dict[str, Any] | None:
    return await get_db()[COLLECTION].find_one({"code": code}, {"_id": 0})


async def mark_done(code: str, *, handled_by: str) -> dict[str, Any] | None:
    """Đóng yêu cầu. Lọc theo `status` để hai người bấm cùng lúc chỉ một người thắng."""
    return await get_db()[COLLECTION].find_one_and_update(
        {"code": code, "status": STATUS_PENDING},
        {"$set": {"status": STATUS_DONE, "handled_by": handled_by, "handled_at": now()}},
        projection={"_id": 0},
        return_document=ReturnDocument.AFTER,
    )


async def count_pending(subject_types: tuple[str, ...]) -> int:
    return await get_db()[COLLECTION].count_documents(
        {"subject_type": {"$in": list(subject_types)}, "status": STATUS_PENDING}
    )
