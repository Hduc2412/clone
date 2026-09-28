"""Hàng đợi hỗ trợ — việc cần người, tách khỏi hàng đợi tuyển dụng.

## Vì sao là hàng đợi thứ hai chứ không gộp vào hàng đợi đang có

`/admin/queue` giữ những hồ sơ **đã đủ điều kiện sơ bộ và đã chọn đơn** — việc ở
đó là gọi điện xác nhận rồi chốt. Hàng đợi này giữ thứ khác hẳn: người chưa đủ
điều kiện muốn hỏi thêm, người muốn tư vấn chuyện học, người muốn gặp mặt.

Trộn hai loại vào một chỗ thì việc gấp lẫn với việc dài hạn. Một nhân viên mở
hàng đợi ra thấy hai mươi dòng, không phân biệt được dòng nào là hồ sơ sắp chốt
và dòng nào là câu hỏi có thể trả lời cuối ngày — nên họ sẽ xử theo thứ tự thời
gian, và hồ sơ sắp chốt nằm đợi sau một câu hỏi về học phí.

Quan trọng hơn: gộp chung sẽ buộc phải nới **chốt chặn đăng ký**. Chốt hiện tại
từ chối tạo hồ sơ đăng ký khi đơn chưa đạt điều kiện, và đó là thứ giữ cho hàng
đợi tuyển dụng chỉ chứa hồ sơ dùng được. Cho người chưa đủ điều kiện đi qua cửa
ấy là phá đúng cái chốt vừa siết.

## Không lưu dữ liệu sức khỏe

Loại `hoc_tap` và những yêu cầu phát sinh từ chuyện sức khỏe đều **không ghi bệnh
gì**. Hệ thống chỉ biết "người này muốn được tư vấn", không biết vì sao. Chẩn
đoán bệnh theo người ta đi rất xa nếu lộ, mà giá trị nghiệp vụ của việc lưu nó
bằng không — buổi khám mới là chỗ kết luận.

## Ảnh chụp kết quả đối chiếu đi kèm

Mỗi yêu cầu mang theo `advice_block`: đúng khối chữ ứng viên đã nhìn thấy lúc
bấm nút. Nhân viên gọi lại đọc được **chính thứ khách đã đọc**, thay vì phải tự
dựng lại rồi đoán xem khách đang hiểu thế nào. Đây là bản chụp cố định, không
đổi kể cả khi hồ sơ hay đơn thay đổi về sau.
"""
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.db.common import get_db, now, strip_id


COLLECTION = "support_requests"

# Ba loại việc. Tách ra vì chúng cần người khác nhau và gấp khác nhau: tư vấn
# học là việc của người phụ trách đào tạo, xin gặp là việc của người xếp lịch.
KIND_NHAN_TIN = "nhan_tin"
KIND_HOC_TAP = "hoc_tap"
KIND_GAP_MAT = "gap_mat"
KINDS = (KIND_NHAN_TIN, KIND_HOC_TAP, KIND_GAP_MAT)

STATUS_CHO = "cho_xu_ly"
STATUS_DANG_XU_LY = "dang_xu_ly"
STATUS_XONG = "da_xong"
STATUS_HUY = "da_huy"
STATUSES = (STATUS_CHO, STATUS_DANG_XU_LY, STATUS_XONG, STATUS_HUY)

PROJECTION = {"_id": 0}


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[COLLECTION].create_index([("code", ASCENDING)], unique=True)
    # Hàng đợi đọc theo trạng thái, ai chờ lâu nhất lên đầu.
    await db[COLLECTION].create_index([("status", ASCENDING), ("created_at", ASCENDING)])
    await db[COLLECTION].create_index([("assigned_to", ASCENDING), ("created_at", DESCENDING)])
    await db[COLLECTION].create_index([("session_id", ASCENDING), ("created_at", DESCENDING)])


async def create_request(document: dict[str, Any]) -> dict[str, Any]:
    full = {
        **document,
        "status": STATUS_CHO,
        "assigned_to": None,
        "handled_at": None,
        "reply": None,
        "created_at": now(),
        "updated_at": now(),
    }
    await get_db()[COLLECTION].insert_one(dict(full))
    return strip_id(full)


async def get_request(code: str) -> dict[str, Any] | None:
    return await get_db()[COLLECTION].find_one({"code": code}, PROJECTION)


async def list_requests(
    *,
    status: str | None = STATUS_CHO,
    kind: str | None = None,
    assigned_to: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if status is not None:
        query["status"] = status
    if kind is not None:
        query["kind"] = kind
    if assigned_to is not None:
        query["assigned_to"] = assigned_to
    cursor = (
        get_db()[COLLECTION]
        .find(query, PROJECTION)
        # Tăng dần: ai chờ lâu nhất lên đầu. Cùng lý do như hàng đợi tuyển dụng.
        .sort([("created_at", ASCENDING)])
        .limit(limit)
    )
    return [document async for document in cursor]


async def list_for_session(session_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """Yêu cầu của chính phiên này — để khách xem lại mình đã hỏi gì."""
    cursor = (
        get_db()[COLLECTION]
        .find({"session_id": session_id}, PROJECTION)
        .sort([("created_at", DESCENDING)])
        .limit(limit)
    )
    return [document async for document in cursor]


async def claim(code: str, *, email: str) -> dict[str, Any] | None:
    """Nhận xử lý. Trả `None` nếu người khác vừa nhận trước.

    Điều kiện `assigned_to: None` nằm ngay trong câu cập nhật, không phải đọc
    rồi ghi hai bước — hai người bấm cùng lúc thì một người nhận được, người kia
    biết ngay là trượt. Cùng cách với `/admin/queue`.
    """
    return await get_db()[COLLECTION].find_one_and_update(
        {"code": code, "assigned_to": None, "status": STATUS_CHO},
        {
            "$set": {
                "assigned_to": email,
                "status": STATUS_DANG_XU_LY,
                "updated_at": now(),
            }
        },
        projection=PROJECTION,
        return_document=ReturnDocument.AFTER,
    )


async def close_request(
    code: str, *, email: str, reply: str, status: str = STATUS_XONG
) -> dict[str, Any] | None:
    return await get_db()[COLLECTION].find_one_and_update(
        {"code": code},
        {
            "$set": {
                "status": status,
                "reply": reply,
                "handled_by": email,
                "handled_at": now(),
                "updated_at": now(),
            }
        },
        projection=PROJECTION,
        return_document=ReturnDocument.AFTER,
    )


async def count_waiting(kind: str | None = None) -> int:
    query: dict[str, Any] = {"status": STATUS_CHO}
    if kind is not None:
        query["kind"] = kind
    return await get_db()[COLLECTION].count_documents(query)
