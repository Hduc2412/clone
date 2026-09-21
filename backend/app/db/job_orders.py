"""Danh mục đơn tuyển dụng.

Đây là điều kiện tiên quyết của toàn bộ chuỗi nghiệp vụ: chưa có đơn hàng thì bộ
đối chiếu không có gì để so và kênh khách hàng không có gì để giới thiệu.

Một đơn hàng tách làm hai nhóm dữ liệu rành mạch:

- `requirements` và `deadline` — **điều kiện bắt buộc**, dùng để loại trừ. Mỗi
  trường sinh ra đúng một dòng đạt hoặc không đạt khi đối chiếu.
- `reference` — **thông tin tham khảo**, dùng để xếp hạng và hiển thị, không bao
  giờ dùng để loại ứng viên.

Tách ngay từ tầng dữ liệu là điều làm cho phần giới thiệu về sau giải trình được.

`deadline` để ở cấp ngoài cùng thay vì nằm trong `requirements` vì nó tham gia
vào index lọc đơn công khai; về mặt nghiệp vụ nó vẫn là một điều kiện bắt buộc.
"""
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.core.timeutil import local_today_iso
from app.db.common import flatten_update, get_db, keep_allowed_nulls, now, strip_id


COLLECTION = "job_orders"
EVENT_COLLECTION = "job_order_events"
COUNTER_COLLECTION = "counters"

# Trường chỉ dành cho nội bộ, không bao giờ ra khỏi endpoint công khai.
PUBLIC_EXCLUDED_FIELDS = (
    "internal_note",
    "created_by",
    "updated_by",
    "hired_count",
)

ADMIN_PROJECTION: dict[str, Any] = {"_id": 0}
PUBLIC_PROJECTION: dict[str, Any] = {"_id": 0} | {
    field: 0 for field in PUBLIC_EXCLUDED_FIELDS
}

# Trường được phép xóa về rỗng. Những trường còn lại (trạng thái, tên đơn, tỉnh)
# phải luôn có giá trị nên `None` với chúng bị bỏ qua thay vì ghi đè.
NULLABLE_FIELDS = frozenset(
    {
        "description",
        "internal_note",
        "city",
        "requirements.education_required",
        "requirements.age_min",
        "requirements.age_max",
        "reference.salary_min",
        "reference.salary_max",
        "reference.cost_total_vnd",
        "reference.interview_date",
        "reference.departure_expected",
    }
)


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[COLLECTION].create_index("code", unique=True)
    # Truy vấn đơn công khai luôn lọc theo đúng ba trường này.
    await db[COLLECTION].create_index(
        [("published", ASCENDING), ("status", ASCENDING), ("deadline", ASCENDING)]
    )
    await db[COLLECTION].create_index(
        [("region_group", ASCENDING), ("prefecture", ASCENDING)]
    )
    await db[COLLECTION].create_index(
        [("program", ASCENDING), ("status", ASCENDING)]
    )
    await db[COLLECTION].create_index([("updated_at", DESCENDING)])
    await db[EVENT_COLLECTION].create_index(
        [("job_order_code", ASCENDING), ("created_at", ASCENDING)]
    )


async def next_job_order_code() -> str:
    """Sinh mã tăng dần `DH-0001`.

    Đơn hàng dùng mã tuần tự chứ không ngẫu nhiên như các bản ghi khác, vì nhân
    viên nghiệp vụ đọc và gõ mã này hằng ngày; số tăng dần dễ nhớ và dễ đối chiếu
    với file Excel của công ty.
    """
    counter = await get_db()[COUNTER_COLLECTION].find_one_and_update(
        {"_id": COLLECTION},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"DH-{counter['seq']:04d}"


def public_filter(today: str | None = None) -> dict[str, Any]:
    """Điều kiện để một đơn được hiển thị công khai.

    Ba điều kiện phải đồng thời đúng: đã bật công khai, đang tuyển, và còn hạn
    nộp. Lọc lúc truy vấn thay vì chạy tác vụ định kỳ đổi trạng thái, để đơn quá
    hạn tự biến mất khỏi website mà không cần ai thao tác.
    """
    return {
        "published": True,
        "status": "open",
        "deadline": {"$gte": today or local_today_iso()},
    }


def build_query(
    *,
    status: str | None = None,
    published: bool | None = None,
    program: str | None = None,
    employer_type: str | None = None,
    prefecture: str | None = None,
    region_group: str | None = None,
    japanese_required: str | None = None,
    only_public: bool = False,
) -> dict[str, Any]:
    query: dict[str, Any] = dict(public_filter()) if only_public else {}
    if status:
        query["status"] = status
    if published is not None:
        query["published"] = published
    if program:
        query["program"] = program
    if employer_type:
        query["employer_type"] = employer_type
    if prefecture:
        query["prefecture"] = prefecture
    if region_group:
        query["region_group"] = region_group
    if japanese_required:
        query["requirements.japanese_required"] = japanese_required
    return query


async def list_job_orders(
    query: dict[str, Any],
    *,
    limit: int = 100,
    public: bool = False,
) -> list[dict[str, Any]]:
    projection = PUBLIC_PROJECTION if public else ADMIN_PROJECTION
    cursor = (
        get_db()[COLLECTION]
        .find(query, projection)
        .sort([("deadline", ASCENDING), ("code", ASCENDING)])
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def get_job_order(
    code: str,
    *,
    public: bool = False,
) -> dict[str, Any] | None:
    query: dict[str, Any] = {"code": code}
    if public:
        query |= public_filter()
    projection = PUBLIC_PROJECTION if public else ADMIN_PROJECTION
    return await get_db()[COLLECTION].find_one(query, projection)


async def get_job_orders_by_codes(codes: list[str]) -> list[dict[str, Any]]:
    if not codes:
        return []
    cursor = get_db()[COLLECTION].find({"code": {"$in": codes}}, ADMIN_PROJECTION)
    return await cursor.to_list(length=len(codes))


async def create_job_order(data: dict[str, Any]) -> dict[str, Any]:
    timestamp = now()
    document = {
        **data,
        "hired_count": data.get("hired_count", 0),
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    await get_db()[COLLECTION].insert_one(document)
    return strip_id(document)


async def update_job_order(
    code: str,
    fields: dict[str, Any],
    *,
    updated_by: str | None = None,
) -> dict[str, Any] | None:
    """Sửa nội dung đơn hàng, giữ nguyên những trường không được gửi lên."""
    flat = keep_allowed_nulls(flatten_update(fields), NULLABLE_FIELDS)
    flat["updated_at"] = now()
    if updated_by:
        flat["updated_by"] = updated_by
    return await get_db()[COLLECTION].find_one_and_update(
        {"code": code},
        {"$set": flat},
        return_document=ReturnDocument.AFTER,
        projection=ADMIN_PROJECTION,
    )


async def change_status(
    code: str,
    *,
    new_status: str,
    expected_status: str,
    updated_by: str | None = None,
    unpublish: bool = False,
) -> dict[str, Any] | None:
    """Đổi trạng thái có kiểm tra trạng thái hiện tại.

    Điều kiện `status: expected_status` trong bộ lọc là khóa lạc quan: hai người
    cùng mở một đơn và bấm hai nút khác nhau thì người sau nhận `None` và được
    yêu cầu tải lại, thay vì ghi đè lên thao tác của người trước.
    """
    changes: dict[str, Any] = {
        "status": new_status,
        "updated_at": now(),
    }
    if updated_by:
        changes["updated_by"] = updated_by
    if unpublish:
        changes["published"] = False
    return await get_db()[COLLECTION].find_one_and_update(
        {"code": code, "status": expected_status},
        {"$set": changes},
        return_document=ReturnDocument.AFTER,
        projection=ADMIN_PROJECTION,
    )


async def set_published(
    code: str,
    *,
    published: bool,
    updated_by: str | None = None,
) -> dict[str, Any] | None:
    changes: dict[str, Any] = {"published": published, "updated_at": now()}
    if updated_by:
        changes["updated_by"] = updated_by
    return await get_db()[COLLECTION].find_one_and_update(
        {"code": code},
        {"$set": changes},
        return_document=ReturnDocument.AFTER,
        projection=ADMIN_PROJECTION,
    )


async def increment_hired(code: str) -> dict[str, Any] | None:
    """Tăng số đã tuyển; tự chuyển sang đủ số lượng khi chạm hạn mức.

    Gọi khi một ứng viên trúng tuyển. Không tự đóng đơn — đóng hay mở lại là
    quyết định của người phụ trách nghiệp vụ.
    """
    order = await get_db()[COLLECTION].find_one_and_update(
        {"code": code},
        {"$inc": {"hired_count": 1}, "$set": {"updated_at": now()}},
        return_document=ReturnDocument.AFTER,
        projection=ADMIN_PROJECTION,
    )
    if order is None:
        return None
    if order["status"] == "open" and order["hired_count"] >= order["quota"]:
        filled = await change_status(
            code,
            new_status="filled",
            expected_status="open",
            updated_by="system",
        )
        return filled or order
    return order


async def delete_job_order(code: str) -> bool:
    """Chỉ xóa được đơn còn ở trạng thái nháp; đơn đã công bố thì đóng, không xóa."""
    result = await get_db()[COLLECTION].delete_one({"code": code, "status": "draft"})
    return result.deleted_count == 1


async def record_event(
    job_order_code: str,
    action: str,
    *,
    actor_email: str | None = None,
    actor_name: str | None = None,
    old_status: str | None = None,
    new_status: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    await get_db()[EVENT_COLLECTION].insert_one(
        {
            "job_order_code": job_order_code,
            "action": action,
            "actor_email": actor_email,
            "actor_name": actor_name,
            "old_status": old_status,
            "new_status": new_status,
            "details": details or {},
            "created_at": now(),
        }
    )


async def list_events(job_order_code: str, limit: int = 200) -> list[dict[str, Any]]:
    cursor = (
        get_db()[EVENT_COLLECTION]
        .find({"job_order_code": job_order_code}, {"_id": 0})
        .sort("created_at", ASCENDING)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def public_facets() -> dict[str, list[str]]:
    """Các giá trị thực sự có đơn công khai, để website chỉ hiện bộ lọc dùng được."""
    query = public_filter()
    collection = get_db()[COLLECTION]
    return {
        "prefectures": sorted(await collection.distinct("prefecture", query)),
        "region_groups": sorted(await collection.distinct("region_group", query)),
        "employer_types": sorted(await collection.distinct("employer_type", query)),
        "programs": sorted(await collection.distinct("program", query)),
        "japanese_levels": sorted(
            await collection.distinct("requirements.japanese_required", query)
        ),
    }


async def count_job_orders(query: dict[str, Any] | None = None) -> int:
    return await get_db()[COLLECTION].count_documents(query or {})
