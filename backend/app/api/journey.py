"""Mở phiên tư vấn cho khách chưa đăng nhập.

Trang tư vấn cho phép gửi CV ngay, không bắt chat trước. Nhưng mọi đường
`/public/*` nay đòi cookie phiên đã ký, mà cookie ấy chỉ được phát ở lượt chat
đầu tiên. Cần một cửa để mở phiên mà không phải nói gì.

**Cửa này không nhận mã phiên từ client.** Đó là toàn bộ điểm của nó. Nếu nhận,
kẻ tấn công chỉ việc gửi lên mã của nạn nhân và được cấp một cookie hợp lệ cho
hồ sơ người khác — tức là vá xong vẫn thủng y như cũ, chỉ khác là bây giờ có
thêm một lớp cookie làm người ta yên tâm nhầm.

Gọi lại nhiều lần không sinh phiên mới: đã có cookie hợp lệ thì trả về đúng mã
cũ. Nếu không, mỗi lần tải lại trang là mất hết dữ liệu vừa khai.
"""
from fastapi import APIRouter, Cookie, Response
from pydantic import BaseModel

from app.auth.journey_security import (
    attach_cookie,
    new_session_id,
    session_from_cookie,
)
from app.core.config import settings


router = APIRouter(prefix="/public/phien", tags=["Phiên tư vấn (công khai)"])


class PhienResponse(BaseModel):
    session_id: str
    vua_mo: bool


@router.post("", response_model=PhienResponse)
async def mo_phien(
    response: Response,
    journey_cookie: str | None = Cookie(
        default=None, alias=settings.journey_cookie_name
    ),
) -> PhienResponse:
    """Trả về mã phiên hiện tại, mở phiên mới nếu chưa có."""
    session_id = session_from_cookie(journey_cookie)
    if session_id is not None:
        return PhienResponse(session_id=session_id, vua_mo=False)

    session_id = new_session_id()
    attach_cookie(response, session_id)
    return PhienResponse(session_id=session_id, vua_mo=True)


@router.post("/moi", response_model=PhienResponse)
async def mo_phien_moi(response: Response) -> PhienResponse:
    """Bỏ phiên đang có, bắt đầu lại từ đầu.

    Dùng cho nút "làm lại từ đầu" trên giao diện. Cookie là `httponly` nên
    JavaScript không tự xoá được — phải nhờ máy chủ ghi đè.

    Không xoá dữ liệu của phiên cũ ở đây. Người bấm nút này thường chỉ muốn khai
    lại cho một người khác (nhân viên tư vấn hộ, hay hai anh em dùng chung máy),
    không có nghĩa là muốn xoá hồ sơ đã gửi. Muốn xoá thì có đường riêng.
    """
    session_id = new_session_id()
    attach_cookie(response, session_id)
    return PhienResponse(session_id=session_id, vua_mo=True)
