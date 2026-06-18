"""
Reference Resolver — Sprint 2
Đọc lịch sử session, thay thế từ mơ hồ ("vậy", "đó", "cái đó"...)
thành nội dung cụ thể trước khi gửi cho RAG tìm kiếm.
"""

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
    print(f"[ReferenceResolver] '{query}' → '{resolved}'")
    return resolved
    