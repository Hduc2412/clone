"""Danh mục khóa học tiếng Nhật.

## Vì sao phải là một bảng, không phải mấy dòng chữ trong mã nguồn

Khi hồ sơ chưa đủ điều kiện vì thiếu tiếng Nhật, câu hỏi thật của ứng viên là
*"tôi phải học bao lâu, tốn bao nhiêu"*. Trả lời được câu đó thì cuộc tư vấn mới
có ích — nhưng con số đó phải có thật ở đâu đó.

Kho tri thức (Qdrant) lưu **đoạn văn để trả lời câu hỏi**, không lưu **bảng để
tính toán**. Tra được một đoạn nói "khóa học 6–7 tháng" không cho biết học xong
thì đạt trình độ nào, nên không bắc được cầu tới yêu cầu của đơn. Bảng này làm
việc đó: mỗi dòng ghi khóa nhận người ở trình độ nào, dạy tới trình độ nào.

## Mỗi dòng phải chỉ được chỗ nó lấy ra

`source_url` và `source_note` không phải trang trí. Một con số sai về học phí
không phải lỗi hiển thị: nó là lời hứa với người đang tính chuyện vay tiền đi
nước ngoài. Nên mỗi ô số phải truy được về nguồn, và ô nào không có nguồn thì để
trống chứ không điền phỏng đoán.

## Thời lượng là một khoảng, không phải một số

Nguồn ghi "6–7 tháng". Lưu thành đúng một số 6 hay 7 là tự thêm độ chính xác mà
nguồn không có. `months_min`/`months_max` giữ nguyên khoảng ấy, và phần diễn đạt
nói lại đúng khoảng đó.

## Học phí nằm trong một tổng lớn hơn

Ở chương trình hiện tại, 35 triệu học phí là **một chặng** của tổng 90 triệu
(10 đăng ký + 35 học tiếng + 45 xuất cảnh). Nói "học phí 35 triệu" trơ trọi là
để khách hiểu sai số tiền phải chuẩn bị, nên bảng giữ `package_total_vnd` và
phần tư vấn bắt buộc nêu cả tổng.
"""
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, ReturnDocument

from app.db.common import flatten_update, get_db, now, strip_id


COLLECTION = "courses"

STATUS_PUBLISHED = "published"
STATUS_DRAFT = "draft"

# Trường được phép xóa về rỗng. Những trường còn lại mà nhận `None` thì bỏ qua,
# vì bảng này tồn tại để giữ con số có nguồn — ghi rỗng lên một ô đang có số là
# âm thầm làm mất nguồn.
NULLABLE = frozenset({"months_max", "tuition_vnd", "package_total_vnd", "source_note"})

PROJECTION = {"_id": 0}


class KhoaHocKhongHopLe(ValueError):
    """Dữ liệu khóa học sai luật. Mang câu tiếng Việt nói rõ sai ở đâu."""


def kiem_tra(entry: dict[str, Any]) -> None:
    """Luật hợp lệ của một dòng khóa học. Thuần, không chạm database.

    Đặt ở tầng dữ liệu để **bộ nạp và API dùng chung một bộ luật**. Trước đây luật
    này chỉ nằm trong `scripts/seed_courses.py`, nên khi mở API quản trị thì có
    ngay hai cửa vào bảng với hai mức khắt khe khác nhau — và cửa lỏng hơn sẽ nhận
    những dòng mà cửa kia từ chối.

    Sai nguy hiểm nhất là **khai ngược trình độ**. Bộ ghép lộ trình sẽ bỏ qua khóa
    ấy trong im lặng, và triệu chứng duy nhất là ứng viên không bao giờ nhận được
    lộ trình học — không lỗi, không cảnh báo, không ai hiểu vì sao.
    """
    from app.matching.catalog import JAPANESE_RANK

    code = entry.get("code") or "(thiếu mã)"
    for truong in ("code", "title", "level_from", "level_to", "months_min", "status"):
        if entry.get(truong) in (None, ""):
            raise KhoaHocKhongHopLe(f"{code}: thiếu trường bắt buộc {truong!r}")

    tu = JAPANESE_RANK.get(entry["level_from"])
    toi = JAPANESE_RANK.get(entry["level_to"])
    if tu is None:
        raise KhoaHocKhongHopLe(
            f"{code}: trình độ nhận vào không có trong danh mục: {entry['level_from']!r}"
        )
    if toi is None:
        raise KhoaHocKhongHopLe(
            f"{code}: trình độ đầu ra không có trong danh mục: {entry['level_to']!r}"
        )
    if tu >= toi:
        raise KhoaHocKhongHopLe(
            f"{code}: khóa phải nâng trình độ lên — đang khai "
            f"{entry['level_from']!r} → {entry['level_to']!r}"
        )

    thang_min = entry["months_min"]
    thang_max = entry.get("months_max")
    if thang_min <= 0:
        raise KhoaHocKhongHopLe(f"{code}: số tháng tối thiểu phải lớn hơn 0")
    if thang_max is not None and thang_max < thang_min:
        raise KhoaHocKhongHopLe(
            f"{code}: số tháng tối đa ({thang_max}) nhỏ hơn tối thiểu ({thang_min})"
        )

    tong = entry.get("package_total_vnd")
    hoc_phi = entry.get("tuition_vnd")
    if tong is not None and hoc_phi is not None and tong < hoc_phi:
        raise KhoaHocKhongHopLe(
            f"{code}: tổng gói ({tong:,}) nhỏ hơn học phí ({hoc_phi:,}) — "
            "một trong hai con số đang sai"
        )

    if entry["status"] not in (STATUS_PUBLISHED, STATUS_DRAFT):
        raise KhoaHocKhongHopLe(
            f"{code}: trạng thái phải là {STATUS_PUBLISHED!r} hoặc {STATUS_DRAFT!r}"
        )


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[COLLECTION].create_index([("code", ASCENDING)], unique=True)
    # Bộ ghép lộ trình luôn tra theo "nhận người ở trình độ nào", nên đánh index
    # đúng cặp đó thay vì quét cả bảng mỗi lần tư vấn.
    await db[COLLECTION].create_index([("level_from", ASCENDING), ("status", ASCENDING)])
    await db[COLLECTION].create_index([("status", ASCENDING), ("level_to", ASCENDING)])


async def list_courses(
    *,
    status: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if status is not None:
        query["status"] = status
    cursor = (
        get_db()[COLLECTION]
        .find(query, PROJECTION)
        .sort([("level_from", ASCENDING), ("code", ASCENDING)])
        .limit(limit)
    )
    return [document async for document in cursor]


async def list_published() -> list[dict[str, Any]]:
    """Kho khóa đem đi tư vấn. Khóa nháp không bao giờ lọt ra ngoài."""
    return await list_courses(status=STATUS_PUBLISHED, limit=200)


async def get_course(code: str) -> dict[str, Any] | None:
    return await get_db()[COLLECTION].find_one({"code": code}, PROJECTION)


async def create_course(document: dict[str, Any]) -> dict[str, Any]:
    full = {**document, "created_at": now(), "updated_at": now()}
    await get_db()[COLLECTION].insert_one(dict(full))
    return strip_id(full)


async def update_course(code: str, fields: dict[str, Any]) -> dict[str, Any] | None:
    payload = flatten_update(
        {key: value for key, value in fields.items() if value is not None or key in NULLABLE}
    )
    if not payload:
        return await get_course(code)
    payload["updated_at"] = now()
    return await get_db()[COLLECTION].find_one_and_update(
        {"code": code},
        {"$set": payload},
        projection=PROJECTION,
        return_document=ReturnDocument.AFTER,
    )


async def delete_course(code: str) -> bool:
    result = await get_db()[COLLECTION].delete_one({"code": code})
    return result.deleted_count == 1


async def count_courses(status: str | None = None) -> int:
    query = {} if status is None else {"status": status}
    return await get_db()[COLLECTION].count_documents(query)
