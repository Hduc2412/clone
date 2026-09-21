"""Quy tắc dùng chung cho phân công và quyền sở hữu bản ghi nghiệp vụ.

Khách hàng, hồ sơ tuyển dụng và (sắp tới) đơn tuyển dụng đều theo cùng một
quy tắc: admin/manager thấy tất cả, nhân viên tư vấn chỉ thao tác trên bản ghi
được giao cho mình. Gom về đây để mỗi module không tự định nghĩa một kiểu.
"""
from fastapi import HTTPException

from app.db.database import get_staff_user_by_email

# Vai trò được xem và sửa mọi bản ghi, không giới hạn theo người phụ trách.
PRIVILEGED_ROLES = frozenset({"admin", "manager"})


def is_privileged(current_user: dict) -> bool:
    return current_user.get("role") in PRIVILEGED_ROLES


def can_access(record: dict, current_user: dict) -> bool:
    """Bản ghi có thuộc quyền xử lý của người đang đăng nhập không."""
    if is_privileged(current_user):
        return True
    return record.get("assigned_to") == current_user.get("email")


async def validate_assignee(email: str | None) -> str | None:
    """Chuẩn hóa email người phụ trách và bảo đảm tài khoản có thật, đang hoạt động.

    Thiếu bước này thì bản ghi có thể bị giao cho một email không tồn tại;
    lỗi chỉ lộ ra ở bước sau, lúc đã khó lần ngược nguyên nhân.
    """
    if not email:
        return None
    normalized = email.strip().lower()
    user = await get_staff_user_by_email(normalized)
    if user is None or user.get("status") != "active":
        raise HTTPException(status_code=400, detail="Nhân viên phụ trách không hợp lệ.")
    return normalized


def ensure_can_assign(current_user: dict, detail: str) -> None:
    """Chỉ admin/manager được đổi người phụ trách."""
    if not is_privileged(current_user):
        raise HTTPException(status_code=403, detail=detail)
