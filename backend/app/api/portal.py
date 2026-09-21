"""Hệ khách hàng: ứng viên đã đăng nhập xem hồ sơ của **chính mình**.

Nguyên tắc duy nhất chi phối toàn bộ file này: **mọi truy vấn đều bị khóa vào
`lead_code` lấy từ token**, không bao giờ lấy từ tham số người gọi gửi lên. Nhận
mã hồ sơ từ client rồi đi tra là mở đường cho một ứng viên đọc hồ sơ của người
khác chỉ bằng cách đổi con số trên thanh địa chỉ.

Cũng vì thế không có endpoint nào ở đây nhận `lead_code`, `session_id` hay
`application_code` để lọc. Muốn xem chi tiết một hồ sơ thì vẫn phải nằm trong
danh sách đã lọc sẵn theo chủ tài khoản.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.auth.candidate_security import require_usable_password
from app.db import candidate_profiles as profiles
from app.db.database import list_recruitment_applications


router = APIRouter(prefix="/tai-khoan", tags=["Hệ khách hàng"])

# Những trường của hồ sơ đăng ký mà ứng viên được thấy. Danh sách cho phép chứ
# không phải danh sách loại trừ: thêm một trường nội bộ vào collection sau này
# sẽ không vô tình lọt ra ngoài.
_VISIBLE_FIELDS = (
    "application_code",
    "job_order_code",
    "job_order_title",
    "status",
    "is_active",
    "destination",
    "created_at",
    "updated_at",
)


def _visible(application: dict[str, Any]) -> dict[str, Any]:
    return {key: application.get(key) for key in _VISIBLE_FIELDS}


@router.get("/ho-so")
async def my_applications(
    account: dict[str, Any] = Depends(require_usable_password),
) -> dict[str, Any]:
    """Các đơn ứng viên này đã đăng ký, kèm trạng thái hiện tại."""
    lead_code = account.get("lead_code")
    if not lead_code:
        # Tài khoản chưa gắn với khách hàng nào thì không có gì để xem, và cũng
        # không được rơi vào nhánh "không lọc" của hàm truy vấn bên dưới.
        return {"items": []}
    items = await list_recruitment_applications(lead_code=lead_code, limit=50)
    return {"items": [_visible(item) for item in items]}


@router.get("/nang-luc")
async def my_profile(
    account: dict[str, Any] = Depends(require_usable_password),
) -> dict[str, Any] | None:
    """Hồ sơ năng lực đã khai: tiếng Nhật, bằng cấp, nguyện vọng."""
    lead_code = account.get("lead_code")
    if not lead_code:
        return None
    profile = await profiles.get_by_lead(lead_code)
    if profile is None:
        return None
    return profiles.decorate(profiles.public_view(profile))


@router.get("/tong-quan")
async def overview(
    account: dict[str, Any] = Depends(require_usable_password),
) -> dict[str, Any]:
    """Gói một lượt cho màn hình chính, đỡ ba lượt gọi từ điện thoại yếu sóng."""
    applications = await my_applications(account)
    profile = await my_profile(account)
    return {
        "account": {
            "full_name": account.get("full_name"),
            "phone": account.get("phone"),
        },
        "profile": profile,
        "applications": applications["items"],
    }


@router.get("/ho-so/{application_code}")
async def my_application_detail(
    application_code: str,
    account: dict[str, Any] = Depends(require_usable_password),
) -> dict[str, Any]:
    """Chi tiết một đơn — chỉ khi nó thuộc về chính người đang đăng nhập.

    Lọc theo `lead_code` trước rồi mới so mã, chứ không tra thẳng theo mã rồi
    kiểm chủ sở hữu sau. Hai cách cho cùng kết quả khi viết đúng, nhưng cách này
    thì viết sai cũng không lộ được hồ sơ người khác.
    """
    lead_code = account.get("lead_code")
    if not lead_code:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ này.")
    items = await list_recruitment_applications(lead_code=lead_code, limit=50)
    for item in items:
        if item.get("application_code") == application_code:
            return _visible(item)
    raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ này.")
