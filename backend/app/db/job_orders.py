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
    # Thông tin cho tư vấn viên: chia sẻ trong nội bộ, không ra công khai, không vào
    # prompt phía khách (08/10).
    "consultant_note",
    "created_by",
    "updated_by",
    "hired_count",
)

ADMIN_PROJECTION: dict[str, Any] = {"_id": 0}

#: Chỉ Admin/Manager đọc (quyết định 08/10). Nhân viên tư vấn đọc `consultant_note`.
CHI_QUAN_LY_DOC = ("internal_note",)


def ban_cho_nhan_vien(order: dict[str, Any], current_user: dict) -> dict[str, Any]:
    """Bỏ trường chỉ quản lý được đọc khỏi bản trả cho nhân viên thường."""
    from app.services.assignment import is_privileged

    if is_privileged(current_user):
        return order
    return {k: v for k, v in order.items() if k not in CHI_QUAN_LY_DOC}
PUBLIC_PROJECTION: dict[str, Any] = {"_id": 0} | {
    field: 0 for field in PUBLIC_EXCLUDED_FIELDS
}

# Đọc cho công khai thì vẫn lấy `hired_count` để tính số chỉ tiêu còn lại, rồi bỏ nó
# trước khi trả ra (12/10). Khách thấy "còn 3/5", không thấy con số nội bộ thô.
_PUBLIC_FETCH: dict[str, Any] = {k: v for k, v in PUBLIC_PROJECTION.items() if k != "hired_count"}


def cho_cong_khai(order: dict[str, Any] | None) -> dict[str, Any] | None:
    """Bản công khai: thêm `con_lai` (chỉ tiêu còn trống), bỏ `hired_count`."""
    if order is None:
        return None
    ra = dict(order)
    da = int(ra.pop("hired_count", 0) or 0)
    quota = int(ra.get("quota") or 0)
    ra["con_lai"] = max(quota - da, 0)
    return ra

# Trường được phép xóa về rỗng. Những trường còn lại (trạng thái, tên đơn, tỉnh)
# phải luôn có giá trị nên `None` với chúng bị bỏ qua thay vì ghi đè.
NULLABLE_FIELDS = frozenset(
    {
        "description",
        "internal_note",
        "consultant_note",
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
    projection = _PUBLIC_FETCH if public else ADMIN_PROJECTION
    cursor = (
        get_db()[COLLECTION]
        .find(query, projection)
        .sort([("deadline", ASCENDING), ("code", ASCENDING)])
        .limit(limit)
    )
    rows = await cursor.to_list(length=limit)
    return [cho_cong_khai(r) for r in rows] if public else rows


async def get_job_order(
    code: str,
    *,
    public: bool = False,
) -> dict[str, Any] | None:
    query: dict[str, Any] = {"code": code}
    if public:
        query |= public_filter()
    if public:
        return cho_cong_khai(await get_db()[COLLECTION].find_one(query, _PUBLIC_FETCH))
    return await get_db()[COLLECTION].find_one(query, ADMIN_PROJECTION)


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
        # `unpublish=True`: cùng luật với lúc Admin đổi tay — rời "Đang tuyển" thì tắt công
        # khai. Thiếu nó (tới 12/10) đơn tự đủ chỉ tiêu vẫn mang `published`, và lúc Admin
        # mở lại thì đơn hiện ngay lên website mà không ai bấm bật.
        filled = await change_status(
            code,
            new_status="filled",
            expected_status="open",
            updated_by="system",
            unpublish=True,
        )
        return filled or order
    return order


async def decrement_hired(code: str) -> dict[str, Any] | None:
    """Trả lại một chỉ tiêu (người trúng tuyển rút hoặc bị hủy). Không bao giờ dưới 0.

    **Không** tự mở lại đơn "đã hoàn thành chỉ tiêu" — quyết định 12/10: trả chỉ tiêu
    rồi báo Admin, Admin tự mở lại nếu muốn tuyển bù.
    """
    return await get_db()[COLLECTION].find_one_and_update(
        {"code": code, "hired_count": {"$gt": 0}},
        {"$inc": {"hired_count": -1}, "$set": {"updated_at": now()}},
        return_document=ReturnDocument.AFTER,
        projection=ADMIN_PROJECTION,
    )


async def don_qua_han_chua_go(today: str | None = None) -> list[dict[str, Any]]:
    """Đơn vẫn để "Đang tuyển" mà đã qua hạn nộp — đã tự ẩn khỏi website, chờ Admin gỡ."""
    cursor = get_db()[COLLECTION].find(
        {"status": "open", "deadline": {"$lt": today or local_today_iso()}},
        {"_id": 0, "code": 1, "title": 1, "deadline": 1, "status": 1},
    ).sort("deadline", ASCENDING)
    return await cursor.to_list(length=500)


#: Trạng thái được nói cho khách khi họ hỏi về một đơn không còn trên website. Đơn
#: NHÁP không bao giờ nằm ở đây — chưa từng mở thì không được lộ cả tên.
TRANG_THAI_NOI_CHO_KHACH = ("open", "paused", "filled", "expired", "closed")


async def trang_thai_cho_khach(codes: list[str]) -> list[dict[str, Any]]:
    """Vài trường an toàn để chatbot giải thích vì sao một đơn không còn hiện (12/10).

    Chỉ lấy đúng các trường cần — không đọc cả bản ghi quản trị rồi lọc, để thêm một
    trường nội bộ sau này cũng không tự lọt vào prompt.
    """
    if not codes:
        return []
    cursor = get_db()[COLLECTION].find(
        {"code": {"$in": codes}, "status": {"$in": list(TRANG_THAI_NOI_CHO_KHACH)}},
        {"_id": 0, "code": 1, "title": 1, "prefecture": 1, "status": 1, "deadline": 1,
         "published": 1, "quota": 1, "hired_count": 1},
    )
    return [cho_cong_khai(r) for r in await cursor.to_list(length=len(codes))]


async def vua_ngung_nhan(
    *, prefecture: str | None = None, region_group: str | None = None, so_ngay: int = 30, gioi_han: int = 3,
) -> list[dict[str, Any]]:
    """Đơn ở một nơi vừa thôi hiện trên website trong `so_ngay` ngày (đủ chỉ tiêu, hết hạn,
    đóng, tạm dừng, hoặc vẫn "Đang tuyển" nhưng đã qua hạn). Không gồm đơn nháp."""
    from datetime import timedelta

    if not prefecture and not region_group:
        return []
    noi = {"prefecture": prefecture} if prefecture else {"region_group": region_group}
    hom_nay = local_today_iso()
    cursor = get_db()[COLLECTION].find(
        {
            **noi,
            "updated_at": {"$gte": now() - timedelta(days=so_ngay)},
            "$or": [
                {"status": {"$in": ["filled", "expired", "closed", "paused"]}},
                {"status": "open", "deadline": {"$lt": hom_nay}},
            ],
        },
        {"_id": 0, "code": 1, "title": 1, "prefecture": 1, "status": 1, "deadline": 1,
         "published": 1, "quota": 1, "hired_count": 1},
    ).sort("updated_at", DESCENDING).limit(gioi_han)
    return [cho_cong_khai(r) for r in await cursor.to_list(length=gioi_han)]


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
