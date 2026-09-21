"""Sổ điểm hiệu suất nhân viên.

Một bản ghi là **một dòng trong sổ**, không phải một con số tổng. Tổng điểm luôn
được cộng lại từ các dòng, và không có đường nào ghi thẳng vào tổng. Nhờ vậy câu
hỏi "sao tháng này tôi ít điểm" luôn có câu trả lời mở ra xem được, thay vì thành
một cuộc cãi nhau với con số.

## Vì sao ghi lại điểm thay vì tính lại mỗi lần

Điểm hoàn toàn suy ra được từ `application_events` và `appointment_events`. Nhưng
tính lại mỗi lần hiển thị thì **bảng điểm tháng trước sẽ tự đổi** vào ngày ai đó
sửa bảng quy tắc. Điểm đã trao là một sự việc đã xảy ra; sửa quy tắc là chuyện từ
nay về sau. Ghi lại giữ đúng ranh giới đó, và cũng là chỗ duy nhất chứa được
những dòng sửa tay của quản lý.

## Chặn cộng trùng ở tầng database

Index duy nhất `(staff_email, action, reference_code)` cho các dòng tự động. Một
request bị gửi lại, một lần thử lại sau timeout, hay hai worker cùng xử lý một sự
kiện — tất cả đều dẫn tới cộng điểm hai lần cho cùng một việc. Chặn ở tầng ứng
dụng thì vẫn lọt khi có hai tiến trình; chặn ở index thì không.
"""
from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from app.db.common import get_db, now, strip_id


COLLECTION = "employee_score_events"

SOURCE_AUTO = "auto"
SOURCE_MANUAL = "manual"


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[COLLECTION].create_index("code", unique=True)
    await db[COLLECTION].create_index(
        [("staff_email", ASCENDING), ("occurred_at", DESCENDING)]
    )
    await db[COLLECTION].create_index([("occurred_at", DESCENDING)])
    # Chỉ áp cho dòng tự động. Sửa tay thì quản lý có quyền cộng hai lần cho cùng
    # một hồ sơ, vì đó là hai quyết định khác nhau của con người.
    await db[COLLECTION].create_index(
        [("staff_email", ASCENDING), ("action", ASCENDING), ("reference_code", ASCENDING)],
        unique=True,
        name="unique_auto_score_event",
        partialFilterExpression={"source": SOURCE_AUTO},
    )


async def record(document: dict[str, Any]) -> dict[str, Any] | None:
    """Ghi một dòng. Trả `None` nếu dòng này đã có (cộng trùng bị chặn)."""
    full = {
        "source": SOURCE_AUTO,
        "note": None,
        "created_by": None,
        "occurred_at": now(),
        **document,
        "created_at": now(),
    }
    try:
        await get_db()[COLLECTION].insert_one(full)
    except DuplicateKeyError:
        return None
    return strip_id(full)


def build_query(
    *,
    staff_email: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if staff_email:
        query["staff_email"] = staff_email.strip().lower()
    window: dict[str, Any] = {}
    if date_from:
        window["$gte"] = date_from
    if date_to:
        window["$lte"] = date_to
    if window:
        query["occurred_at"] = window
    return query


async def list_events(query: dict[str, Any], *, limit: int = 200) -> list[dict[str, Any]]:
    cursor = (
        get_db()[COLLECTION]
        .find(query, {"_id": 0})
        .sort("occurred_at", DESCENDING)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def totals(query: dict[str, Any]) -> list[dict[str, Any]]:
    """Tổng điểm và số lượt theo từng nhân viên, xếp từ cao xuống thấp."""
    pipeline = [
        {"$match": query},
        {
            "$group": {
                "_id": "$staff_email",
                "points": {"$sum": "$points"},
                "events": {"$sum": 1},
                "last_at": {"$max": "$occurred_at"},
            }
        },
        {"$sort": {"points": -1, "_id": 1}},
    ]
    rows: list[dict[str, Any]] = []
    async for row in get_db()[COLLECTION].aggregate(pipeline):
        rows.append(
            {
                "staff_email": row["_id"],
                "points": row["points"],
                "events": row["events"],
                "last_at": row["last_at"],
            }
        )
    return rows


async def breakdown(query: dict[str, Any]) -> list[dict[str, Any]]:
    """Điểm tách theo loại việc — để biết điểm đến từ đâu, không chỉ bao nhiêu."""
    pipeline = [
        {"$match": query},
        {
            "$group": {
                "_id": "$action",
                "points": {"$sum": "$points"},
                "events": {"$sum": 1},
            }
        },
        {"$sort": {"points": -1}},
    ]
    rows: list[dict[str, Any]] = []
    async for row in get_db()[COLLECTION].aggregate(pipeline):
        rows.append({"action": row["_id"], "points": row["points"], "events": row["events"]})
    return rows
