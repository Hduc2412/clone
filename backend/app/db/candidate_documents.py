"""Hồ sơ gốc ứng viên tải lên.

Một bản ghi ứng với một file. Tách khỏi `candidate_profiles` vì hai thứ có vòng
đời khác nhau: hồ sơ năng lực được sửa đi sửa lại suốt cuộc tư vấn, còn file gốc
thì **không bao giờ đổi** sau khi nhận — sửa nó là làm hỏng chính thứ dùng để đối
chứng.

Bản ghi ở đây chỉ giữ siêu dữ liệu và kết quả bóc tách. Nội dung file nằm trên
đĩa, đường dẫn lưu ở `stored_path`. Không nhét bytes vào MongoDB: một tài liệu
MongoDB bị chặn ở 16MB, mà truy vấn danh sách hồ sơ thì chẳng bao giờ cần tới nội
dung file.

`text` được lưu lại vì đoạn dẫn của từng trường phải đối chiếu được với bản đã
rút chữ. Nếu chỉ giữ file gốc thì mỗi lần muốn kiểm tra lại phải mở và rút chữ
lần nữa, mà bản rút lần sau chưa chắc trùng bản rút lần đầu.
"""
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from app.db.common import get_db, now, strip_id


COLLECTION = "candidate_documents"

STATUS_RECEIVED = "received"      # đã nhận file, chưa bóc tách xong
STATUS_EXTRACTED = "extracted"    # đã bóc tách và gộp vào hồ sơ
STATUS_UNREADABLE = "unreadable"  # file scan, không rút được chữ
STATUS_FAILED = "failed"          # bóc tách lỗi

# Chặn một phiên tải lên vô hạn. Ứng viên thật gửi một tới hai file; con số này
# rộng rãi cho cả trường hợp gửi thêm bằng cấp, mà vẫn chặn được kịch bản lạm dụng.
MAX_PER_SESSION = 5


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[COLLECTION].create_index("code", unique=True)
    await db[COLLECTION].create_index([("session_id", ASCENDING), ("created_at", DESCENDING)])
    await db[COLLECTION].create_index("profile_code")
    # Không đặt unique: hai ứng viên khác nhau gửi trùng một mẫu CV là chuyện có
    # thật. Index này chỉ để tra nhanh xem trong cùng một phiên đã có file đó chưa.
    await db[COLLECTION].create_index([("session_id", ASCENDING), ("sha256", ASCENDING)])


async def create(document: dict[str, Any]) -> dict[str, Any]:
    timestamp = now()
    full = {
        "status": STATUS_RECEIVED,
        "profile_code": None,
        "text": "",
        "page_count": 0,
        "extracted_fields": [],
        "rejected": {},
        "error": None,
        **document,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    await get_db()[COLLECTION].insert_one(full)
    return strip_id(full)


async def mark_extracted(
    code: str,
    *,
    profile_code: str,
    extracted_fields: list[str],
    rejected: dict[str, str],
) -> None:
    await _set(
        code,
        status=STATUS_EXTRACTED,
        profile_code=profile_code,
        extracted_fields=extracted_fields,
        rejected=rejected,
        error=None,
    )


async def mark_failed(code: str, status: str, error: str) -> None:
    await _set(code, status=status, error=error)


async def _set(code: str, **changes: Any) -> None:
    changes["updated_at"] = now()
    await get_db()[COLLECTION].update_one({"code": code}, {"$set": changes})


async def get_by_code(code: str) -> dict[str, Any] | None:
    return await get_db()[COLLECTION].find_one({"code": code}, {"_id": 0})


async def find_in_session(session_id: str, sha256: str) -> dict[str, Any] | None:
    return await get_db()[COLLECTION].find_one(
        {"session_id": session_id, "sha256": sha256}, {"_id": 0, "text": 0}
    )


async def count_in_session(session_id: str) -> int:
    return await get_db()[COLLECTION].count_documents({"session_id": session_id})


async def list_for_session(session_id: str) -> list[dict[str, Any]]:
    cursor = (
        get_db()[COLLECTION]
        .find({"session_id": session_id}, {"_id": 0, "text": 0})
        .sort("created_at", DESCENDING)
    )
    return await cursor.to_list(length=MAX_PER_SESSION)


async def list_all(
    *,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Toàn bộ tài liệu, không lọc theo hồ sơ.

    Cần thiết vì tài liệu **chưa đọc được thì chưa gắn vào hồ sơ nào** — ảnh chụp
    và bản scan đều rơi vào đó. Nếu chỉ tra được theo hồ sơ thì đúng những thứ
    cần nhìn nhất lại là những thứ không ai nhìn thấy.
    """
    query = {"status": status} if status else {}
    cursor = (
        get_db()[COLLECTION]
        .find(query, {"_id": 0, "text": 0})
        .sort("created_at", DESCENDING)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def count_by_status() -> dict[str, int]:
    """Đếm tài liệu theo trạng thái — cơ sở để biết có đáng làm phần đọc ảnh không."""
    pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    counts: dict[str, int] = {}
    async for row in get_db()[COLLECTION].aggregate(pipeline):
        counts[row["_id"]] = row["count"]
    return counts


async def count_images() -> int:
    """Số file ảnh đã nhận. Đây chính là con số dùng để ra quyết định."""
    return await get_db()[COLLECTION].count_documents(
        {"content_type": {"$regex": "^image/"}}
    )


async def list_for_profile(profile_code: str) -> list[dict[str, Any]]:
    cursor = (
        get_db()[COLLECTION]
        .find({"profile_code": profile_code}, {"_id": 0, "text": 0})
        .sort("created_at", DESCENDING)
    )
    return await cursor.to_list(length=MAX_PER_SESSION)


def public_view(document: dict[str, Any]) -> dict[str, Any]:
    """Bản cho ứng viên. Giấu đường dẫn thật trên đĩa và toàn văn đã rút."""
    hidden = {"_id", "stored_path", "text", "sha256"}
    return {key: value for key, value in document.items() if key not in hidden}
