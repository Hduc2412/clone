"""Nạp danh mục khóa học tiếng Nhật vào MongoDB.

    python -m scripts.seed_courses            # thêm mới hoặc cập nhật theo mã khóa
    python -m scripts.seed_courses --dry-run  # chỉ in ra, không ghi

Khác `seed_job_orders.py` ở một điểm quan trọng: đây **không phải dữ liệu mẫu**.
Đơn hàng mẫu là mười chín đơn bịa ra để demo bộ lọc; còn đây là khóa học thật của
trung tâm, mỗi ô truy được về một nguồn ghi trong `scripts/seed_data/courses_seed.py`.

Vì vậy không có cờ `--reset`: xóa bảng này là xóa dữ liệu thật. Muốn sửa thì sửa
qua màn hình quản trị, hoặc sửa file nguồn rồi chạy lại — mã khóa cố định nên
chạy lại chỉ cập nhật, không sinh bản trùng.
"""
import argparse
import asyncio

from app.db import courses
from app.db.common import get_db, now
from app.db.database import close_db, init_db
from app.learning import path
from scripts.seed_data.courses_seed import COURSES


def kiem_tra(entry: dict) -> None:
    """Chặn dữ liệu hỏng ngay ở cửa nạp, không để nó vào bảng.

    Một khóa khai ngược trình độ sẽ bị bộ ghép lộ trình bỏ qua trong im lặng —
    triệu chứng duy nhất là ứng viên không bao giờ nhận được lộ trình, mà không
    ai hiểu vì sao. Thà đổ ở đây kèm lý do rõ ràng.
    """
    code = entry.get("code") or "(thiếu mã)"
    for truong in ("code", "title", "level_from", "level_to", "months_min", "status"):
        if entry.get(truong) in (None, ""):
            raise ValueError(f"{code}: thiếu trường bắt buộc {truong!r}")

    tu = path.JAPANESE_RANK.get(entry["level_from"])
    toi = path.JAPANESE_RANK.get(entry["level_to"])
    if tu is None:
        raise ValueError(f"{code}: level_from không có trong danh mục: {entry['level_from']!r}")
    if toi is None:
        raise ValueError(f"{code}: level_to không có trong danh mục: {entry['level_to']!r}")
    if tu >= toi:
        raise ValueError(
            f"{code}: khóa phải nâng trình độ lên — đang khai "
            f"{entry['level_from']!r} → {entry['level_to']!r}"
        )

    thang_min = entry["months_min"]
    thang_max = entry.get("months_max")
    if thang_min <= 0:
        raise ValueError(f"{code}: months_min phải lớn hơn 0")
    if thang_max is not None and thang_max < thang_min:
        raise ValueError(f"{code}: months_max ({thang_max}) nhỏ hơn months_min ({thang_min})")

    tong = entry.get("package_total_vnd")
    hoc_phi = entry.get("tuition_vnd")
    if tong is not None and hoc_phi is not None and tong < hoc_phi:
        raise ValueError(
            f"{code}: tổng gói ({tong:,}) nhỏ hơn học phí ({hoc_phi:,}) — "
            "một trong hai con số đang sai"
        )


def mo_ta(entry: dict) -> str:
    thang = entry["months_min"]
    if entry.get("months_max") and entry["months_max"] != thang:
        thang = f"{thang}–{entry['months_max']}"
    hoc_phi = entry.get("tuition_vnd")
    tien = f"{hoc_phi:,}đ".replace(",", ".") if hoc_phi else "chưa có học phí"
    return (
        f"{entry['code']}  {path.label(entry['level_from'])} → "
        f"{path.label(entry['level_to'])}  ·  {thang} tháng  ·  {tien}"
    )


async def nap(dry_run: bool) -> int:
    for entry in COURSES:
        kiem_tra(entry)
        print(mo_ta(entry))

    if dry_run:
        print(f"\n[dry-run] Không ghi gì. {len(COURSES)} khóa đã qua kiểm tra.")
        return 0

    await init_db()
    try:
        db = get_db()
        for entry in COURSES:
            await db[courses.COLLECTION].update_one(
                {"code": entry["code"]},
                {
                    "$set": {**entry, "updated_at": now()},
                    "$setOnInsert": {"created_at": now()},
                },
                upsert=True,
            )
        tong = await courses.count_courses()
        print(f"\nĐã nạp. Bảng khóa học hiện có {tong} khóa.")
    finally:
        await close_db()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Chỉ in ra, không ghi.")
    args = parser.parse_args()
    return asyncio.run(nap(args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
