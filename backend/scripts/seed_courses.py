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

    Gọi thẳng `courses.kiem_tra` chứ không giữ bản sao thứ hai của bộ luật. Trước
    đây luật nằm ở đây, và khi mở API quản trị thì thành hai cửa vào cùng một bảng
    với hai mức khắt khe khác nhau — cửa lỏng hơn sẽ nhận những dòng cửa kia từ
    chối, và bảng mất tính nhất quán mà không ai thấy ngay.
    """
    from app.db import courses

    courses.kiem_tra(entry)


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
