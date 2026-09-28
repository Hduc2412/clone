"""
Reference Resolver — Sprint 2
Đọc lịch sử session, thay thế từ mơ hồ ("vậy", "đó", "cái đó"...)
thành nội dung cụ thể trước khi gửi cho RAG tìm kiếm.

## Không ghi nội dung hội thoại ra log

Bản cũ in cả câu hỏi lẫn bốn dòng lịch sử vừa bồi vào. Khách nói "số của em là
09xx" hay "em bị viêm gan B" thì đúng câu ấy nằm trong log của máy chủ — nơi
không có kiểm soát truy cập nào, không có hạn lưu trữ, và thường được gom về một
chỗ tập trung. Đây là dữ liệu cá nhân, không phải dữ liệu vận hành.

Thứ cần cho việc chẩn đoán chỉ là: có bồi ngữ cảnh hay không, và bồi bao nhiêu.
Nội dung cụ thể đã nằm trong `messages` của MongoDB, nơi có kiểm soát.
"""
import logging

logger = logging.getLogger(__name__)

AMBIGUOUS_WORDS = [
    "vậy", "đó", "cái đó", "cái này", "cái kia",
    "thế", "thế thì", "vậy thì", "như vậy",
    "bao nhiêu đó", "chi phí đó", "khoản đó",
    "điều đó", "việc đó", "chương trình đó"
]

def resolve(query: str, history_text: str) -> str:
    """
    Nếu câu hỏi chứa từ mơ hồ VÀ có lịch sử hội thoại
    thì thêm ngữ cảnh từ lịch sử vào câu hỏi.
    Nếu không thì trả về câu hỏi gốc.
    """
    if not history_text:
        return query
    
    query_lower = query.lower()
    has_ambiguous = any(word in query_lower for word in AMBIGUOUS_WORDS)

    if not has_ambiguous:
        return query
     # Lấy 2 lượt cuối của lịch sử làm ngữ cảnh
    lines = history_text.strip().split("\n")
    recent = lines[-4:] if len(lines) >= 4 else lines
    context_snippet = " | ".join(recent)
    
    resolved = f"{query} (ngữ cảnh trước đó: {context_snippet})"
    logger.debug(
        "Bồi ngữ cảnh cho câu hỏi: %d dòng lịch sử, câu dài %d ký tự",
        len(recent),
        len(resolved),
    )
    return resolved
    