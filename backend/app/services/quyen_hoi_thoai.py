"""Nhân viên thường đọc được hội thoại khung chat nào — **một** quy tắc cho list và detail.

## Quy tắc (08/10/2026, bản 2)

Quản lý và quản trị viên đọc mọi hội thoại. Nhân viên tư vấn chỉ đọc hội thoại có
**liên kết rõ ràng** với việc mình đang giữ — không bao giờ suy qua số điện thoại.

Khung chat dùng chung mã phiên với hành trình tư vấn (cookie đã ký, `api/chat.py`), nên
một phiên chat là chính phiên của hồ sơ ứng viên, của hồ sơ đăng ký, của yêu cầu hỗ trợ.
Bốn liên kết được tính:

1. Phiên của hồ sơ ứng viên đang giao trực tiếp cho nhân viên (`candidate_profiles.assigned_to`).
2. Phiên của hồ sơ đăng ký **còn mở** do nhân viên giữ (`recruitment_applications.session_id`).
3. Phiên của yêu cầu hỗ trợ nhân viên **đang** giữ mà khách đã đồng ý bàn giao.
4. Phiên nguồn của lịch hẹn đang giao cho nhân viên (`consultation_appointments.conversation_id`).

Mọi thứ tính từ người phụ trách **hiện tại** lúc đọc, không lưu bản chụp quyền nào —
chuyển việc từ A sang B thì A mất quyền ngay.

## Vì sao bỏ số điện thoại (bản 1 dùng nó)

Bản 1 nối khách hàng ↔ phiên chat qua `sessions.booking_data.phone`. Số điện thoại không
phải khóa bền: hai người dùng chung một số (vợ chồng, người nhà đặt hộ), số được cập nhật,
số cũ cấp lại cho người khác — mỗi trường hợp là một nhân viên đọc được cuộc trò chuyện
của người không phải khách mình. Màn "hành trình khách" cũng từng ghép hội thoại theo số;
với nhân viên thường, nó nay lọc qua đúng tập phiên này.
"""
from typing import Any

from app.db.common import get_db
from app.db.database import list_recruitment_applications
from app.services.assignment import is_privileged

#: Trần mỗi lần tra — cùng lý do với `quyen_ho_so.TRAN`.
TRAN = 500


async def phien_duoc_xem(current_user: dict) -> set[str] | None:
    """Tập mã phiên chat người này được đọc. `None` nghĩa là không giới hạn (quản lý)."""
    if is_privileged(current_user):
        return None
    from app.services.quyen_ho_so import phien_qua_ho_tro

    email = (current_user.get("email") or "").strip().lower()
    db = get_db()
    phien: set[str] = set()

    async for row in db.candidate_profiles.find(
        {"assigned_to": email}, {"_id": 0, "session_id": 1}
    ).limit(TRAN):
        if row.get("session_id"):
            phien.add(row["session_id"])

    for don in await list_recruitment_applications(assigned_to=email, active_only=True, limit=TRAN):
        if don.get("session_id"):
            phien.add(don["session_id"])

    phien |= await phien_qua_ho_tro(email)

    async for row in db.consultation_appointments.find(
        {"assigned_to": email, "conversation_id": {"$nin": [None, ""]}},
        {"_id": 0, "conversation_id": 1},
    ).limit(TRAN):
        phien.add(row["conversation_id"])
    return phien


def loc_hoi_thoai(conversations: list[dict[str, Any]], duoc_xem: set[str] | None) -> list[dict[str, Any]]:
    """Giữ đúng những phiên được xem. Dùng cho màn "hành trình khách"."""
    if duoc_xem is None:
        return conversations
    return [c for c in conversations if c.get("session_id") in duoc_xem]
