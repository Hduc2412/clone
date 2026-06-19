"""
Lead Service — Sprint 3
Quản lý logic thu thập lead: phát hiện thời điểm cần hỏi,
trích xuất thông tin, lưu vào MongoDB.
"""
from app.conversation.entity_extractor import extract_lead_info
from app.db.database import save_lead

ASK_LEAD_MESSAGE = (
    "\n\n📞 Để được tư vấn chi tiết và hỗ trợ nhanh nhất, "
    "anh/chị vui lòng để lại **tên và số điện thoại** giúp mình nhé!"
)

def should_ask_lead(intent:str, already_asked: bool) -> bool:
    """
    Quyết định có nên hỏi xin thông tin lead không.
    Chỉ hỏi khi intent = lead VÀ session này chưa hỏi lần nào.
    """
    return intent == "lead" and not already_asked

async def try_capture_lead(session_id: str, user_query: str, intent: str) -> dict | None:
    """
    Thử trích xuất tên/SĐT từ tin nhắn user.
    Nếu có ít nhất 1 trong 2 (ưu tiên có phone) thì lưu vào DB.
    Trả về dict thông tin đã lưu, hoặc None nếu không trích xuất được gì.
    """
    info = extract_lead_info(user_query)

    if not info["phone"] and not info["name"]:
        return None
    await save_lead(
        session_id=session_id,
        name=info["name"],
        phone=info["phone"],
        note=f"Captured from intent: {intent}",
    )

    print(f"[LeadService] Đã lưu lead cho session {session_id}: {info}")
    return info
