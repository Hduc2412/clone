"""Nhật ký giới thiệu đơn hàng.

Mỗi lần đối chiếu ghi lại **mọi đơn đã xét, kể cả đơn bị loại**, kèm lý do từng
tiêu chí. Đây là màn hình để trả lời câu hỏi mà hội đồng chắc chắn sẽ hỏi: "vì sao
hệ thống không giới thiệu đơn kia cho ứng viên này".

Phải lưu lại thay vì chạy lại khi cần, vì đơn hàng có thể đã đổi từ lúc đó: chạy
lại hôm nay cho ra kết quả hôm nay, không phải kết quả đã thực sự hiển thị cho
ứng viên hôm ấy.
"""
from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from app.db.common import get_db, now, strip_id


COLLECTION = "recommendation_logs"

# Danh sách không kéo theo `items`: mỗi bản ghi chứa toàn bộ bảng tiêu chí của
# hàng chục đơn, tải hết về chỉ để hiện một bảng tóm tắt là lãng phí.
LIST_PROJECTION: dict[str, Any] = {"_id": 0, "items": 0}
DETAIL_PROJECTION: dict[str, Any] = {"_id": 0}


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[COLLECTION].create_index("code", unique=True)
    # Đường tra bộ nhớ đệm: bốn yếu tố quyết định kết quả có lặp lại được không.
    await db[COLLECTION].create_index(
        [
            ("profile_code", ASCENDING),
            ("profile_version", ASCENDING),
            ("orders_fingerprint", ASCENDING),
            ("created_at", DESCENDING),
        ]
    )
    await db[COLLECTION].create_index([("session_id", ASCENDING), ("created_at", DESCENDING)])
    await db[COLLECTION].create_index([("assigned_to", ASCENDING), ("created_at", DESCENDING)])
    await db[COLLECTION].create_index([("created_at", DESCENDING)])


async def create_log(document: dict[str, Any]) -> dict[str, Any]:
    full = {**document, "created_at": now()}
    await get_db()[COLLECTION].insert_one(full)
    return strip_id(full)


async def get_log(code: str) -> dict[str, Any] | None:
    return await get_db()[COLLECTION].find_one({"code": code}, DETAIL_PROJECTION)


async def find_cached(
    *,
    profile_code: str,
    profile_version: int,
    orders_fingerprint: str,
    weights_fingerprint: str,
    since: datetime,
) -> dict[str, Any] | None:
    """Bản ghi gần nhất có cùng bốn yếu tố đầu vào và còn trong thời hạn.

    Cùng bốn yếu tố này thì kết quả chắc chắn giống hệt, nên dùng lại chỉ tiết
    kiệm công chứ không thể làm đổi câu trả lời.
    """
    return await get_db()[COLLECTION].find_one(
        {
            "profile_code": profile_code,
            "profile_version": profile_version,
            "orders_fingerprint": orders_fingerprint,
            "weights_fingerprint": weights_fingerprint,
            "created_at": {"$gte": since},
        },
        DETAIL_PROJECTION,
        sort=[("created_at", DESCENDING)],
    )


async def latest_for_profile(profile_code: str) -> dict[str, Any] | None:
    return await get_db()[COLLECTION].find_one(
        {"profile_code": profile_code},
        DETAIL_PROJECTION,
        sort=[("created_at", DESCENDING)],
    )


def build_query(
    *,
    profile_code: str | None = None,
    session_id: str | None = None,
    assigned_to: str | None = None,
    trigger: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if profile_code:
        query["profile_code"] = profile_code
    if session_id:
        query["session_id"] = session_id
    if assigned_to:
        query["assigned_to"] = assigned_to.strip().lower()
    if trigger:
        query["trigger"] = trigger
    if date_from or date_to:
        window: dict[str, Any] = {}
        if date_from:
            window["$gte"] = date_from
        if date_to:
            window["$lte"] = date_to
        query["as_of"] = window
    return query


async def list_logs(query: dict[str, Any], *, limit: int = 50) -> list[dict[str, Any]]:
    cursor = (
        get_db()[COLLECTION]
        .find(query, LIST_PROJECTION)
        .sort("created_at", DESCENDING)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def attach_application(code: str, application_code: str) -> None:
    await get_db()[COLLECTION].update_one(
        {"code": code}, {"$set": {"application_code": application_code}}
    )
