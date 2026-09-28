"""Nhật ký giới thiệu đơn hàng.

Mỗi lần đối chiếu ghi lại **mọi đơn đã xét, kể cả đơn bị loại**, kèm lý do từng
tiêu chí. Đây là màn hình để trả lời câu hỏi mà hội đồng chắc chắn sẽ hỏi: "vì sao
hệ thống không giới thiệu đơn kia cho ứng viên này".

Phải lưu lại thay vì chạy lại khi cần, vì đơn hàng có thể đã đổi từ lúc đó: chạy
lại hôm nay cho ra kết quả hôm nay, không phải kết quả đã thực sự hiển thị cho
ứng viên hôm ấy.
"""
from datetime import datetime, timedelta
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
    # Nhật ký của phiên bỏ dở tự hết hạn.
    #
    # Đo ngày 22/09/2026: 18 trong 26 bản nhật ký thuộc những phiên chưa bao giờ
    # dẫn tới một hồ sơ đăng ký — người ta xem thử kết quả đối chiếu rồi đóng
    # trang. Mỗi bản nặng vài chục KB, và con số đó lớn lên theo số đơn trong
    # danh mục, nên đây là thứ phình nhanh nhất trong cả cơ sở dữ liệu.
    #
    # Chỉ những bản có `expires_at` mới bị xoá. Bản đã gắn với hồ sơ đăng ký
    # được gỡ mốc ấy đi (xem `attach_application`) nên sống vĩnh viễn — đó là
    # bằng chứng cho một quyết định có thật, không được phép biến mất.
    #
    # Đây cũng là chuyện giữ dữ liệu cá nhân: bản nhật ký chứa cả bảng đối chiếu
    # hồ sơ của một người. Không giữ thứ không còn ai cần.
    await db[COLLECTION].create_index("expires_at", expireAfterSeconds=0)


# Giữ bao lâu trước khi xoá, với nhật ký chưa dẫn tới hồ sơ đăng ký nào.
# Đủ dài để một người cân nhắc rồi quay lại trong vài tháng; đủ ngắn để những
# lần xem thử rồi thôi không nằm lại mãi.
GIU_NHAT_KY_NGAY = 90


async def create_log(document: dict[str, Any]) -> dict[str, Any]:
    luc_nay = now()
    full = {**document, "created_at": luc_nay}
    if not full.get("application_code"):
        full["expires_at"] = luc_nay + timedelta(days=GIU_NHAT_KY_NGAY)
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
    """Gắn nhật ký vào hồ sơ đăng ký, và gỡ luôn hạn xoá.

    Từ lúc này nó là bằng chứng cho một quyết định có thật: ứng viên đã chọn đơn
    nào, dựa trên kết quả đối chiếu nào. Thứ đó không được tự biến mất sau chín
    mươi ngày.
    """
    await get_db()[COLLECTION].update_one(
        {"code": code},
        {"$set": {"application_code": application_code}, "$unset": {"expires_at": ""}},
    )
