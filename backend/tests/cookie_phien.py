"""Tiện ích dùng chung cho test: dựng cookie phiên tư vấn hợp lệ.

Từ 22/09/2026 mọi đường `/public/*` đòi một cookie đã ký gắn với mã phiên. Test
nào chạm vào các đường đó phải cầm cookie thật — **ký bằng đúng hàm mà mã sản
phẩm dùng**, không dựng chuỗi giả.

Lý do không dựng chuỗi giả: nếu test tự bịa một cookie theo định dạng nó tưởng
là đúng, thì ngày nào định dạng thật đổi, test vẫn xanh trong khi ứng dụng đã
hỏng. Ký bằng hàm thật khiến test gãy đúng lúc cần gãy.
"""
from app.auth.journey_security import create_journey_token
from app.core.config import settings


def cookie_cua(session_id: str) -> str:
    """Giá trị cookie cho một mã phiên — tức token đã ký."""
    return create_journey_token(session_id)


def cookies_cho(session_id: str) -> dict[str, str]:
    """Dạng dict để truyền thẳng vào `TestClient(..., cookies=...)`."""
    return {settings.journey_cookie_name: create_journey_token(session_id)}
