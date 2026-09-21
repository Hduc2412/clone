"""Đăng ký index cho các collection nghiệp vụ mới.

`init_db()` trong `database.py` tạo index cho những collection đã có. Thay vì
thêm tiếp vào đó, mỗi module dữ liệu mới tự khai báo index của mình qua hàm
`ensure_indexes(db)`, và file này gọi tất cả trong một lượt. Nhờ vậy thêm một
nghiệp vụ mới không phải sửa file lõi, và đọc module nào là thấy ngay index của
module đó.
"""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import (
    candidate_documents,
    candidate_profiles,
    consultation_reports,
    employee_scores,
    job_orders,
    recommendation_logs,
)


# Thêm module mới vào đây khi tạo collection mới.
_MODULES = (
    job_orders,
    candidate_profiles,
    candidate_documents,
    consultation_reports,
    employee_scores,
    recommendation_logs,
)


async def ensure_domain_indexes(db: AsyncIOMotorDatabase) -> None:
    for module in _MODULES:
        await module.ensure_indexes(db)
