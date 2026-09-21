"""Phiếu tóm tắt tư vấn.

Một phiếu ứng với một lần ứng viên xác nhận đăng ký. Đây là thứ nhân viên đọc
**trước khi nhấc máy gọi** cho ứng viên, nên nó phải trả lời được ba câu mà nhân
viên sẽ hỏi đầu tiên: người này là ai, họ chọn đơn nào, và vì sao hệ thống cho
rằng họ hợp với đơn đó.

## Vì sao phiếu là bản chụp, không phải bản tham chiếu

Phiếu **chép lại** thông tin hồ sơ và đơn hàng tại thời điểm đăng ký, thay vì chỉ
lưu mã rồi tra ngược lúc mở ra xem. Hồ sơ thì ứng viên còn sửa tiếp, đơn hàng thì
công ty còn đổi điều kiện hoặc đóng lại. Nếu phiếu chỉ trỏ tới chúng thì hai tuần
sau mở ra, nhân viên sẽ đọc một nội dung khác với thứ ứng viên đã nhìn thấy và
đồng ý — và không ai biết là nó đã khác.

Bản chụp làm phiếu nặng hơn, nhưng đây đúng là chỗ đáng đánh đổi: phiếu là bằng
chứng về một thỏa thuận tại một thời điểm.
"""
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from app.db.common import get_db, now, strip_id


COLLECTION = "consultation_reports"


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[COLLECTION].create_index("code", unique=True)
    # Một đăng ký sinh đúng một phiếu. Index duy nhất ở đây là chốt chặn cuối:
    # nếu hai request cùng lúc cùng tạo phiếu cho một đăng ký, cái thứ hai bị
    # database chặn chứ không tạo ra hai bản ghi cùng nội dung.
    await db[COLLECTION].create_index("application_code", unique=True)
    await db[COLLECTION].create_index("profile_code")
    await db[COLLECTION].create_index([("created_at", DESCENDING)])
    await db[COLLECTION].create_index([("job_order_code", ASCENDING)])


async def create(document: dict[str, Any]) -> dict[str, Any]:
    full = {**document, "created_at": now()}
    await get_db()[COLLECTION].insert_one(full)
    return strip_id(full)


async def get_by_code(code: str) -> dict[str, Any] | None:
    return await get_db()[COLLECTION].find_one({"code": code}, {"_id": 0})


async def get_by_application(application_code: str) -> dict[str, Any] | None:
    return await get_db()[COLLECTION].find_one(
        {"application_code": application_code}, {"_id": 0}
    )
