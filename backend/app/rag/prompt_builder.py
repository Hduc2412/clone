"""Tạo context và prompt thống nhất cho luồng RAG."""


def build_context(hits: list) -> str:
    """Gộp các chunk tìm được thành context có nguồn rõ ràng."""
    parts = []
    for hit in hits:
        title = hit.payload.get("title", "")
        text = hit.payload.get("text", "")
        url = hit.payload.get("url", "")
        parts.append(f"[{title}]\n{text}\n(Nguồn: {url})")
    return "\n\n---\n\n".join(parts)


def build_prompt(
    context: str,
    user_query: str,
    history_text: str = "",
) -> str:
    """Tạo một prompt dùng chung cho câu đầu và câu hỏi nối tiếp."""
    history_section = ""
    history_rule = (
        "- Không mở đầu bằng lời chào vì cuộc hội thoại đã bắt đầu."
        if history_text
        else "- Chỉ chào ngắn gọn nếu thật sự cần thiết."
    )
    if history_text:
        history_section = f"""
--- LỊCH SỬ HỘI THOẠI ---
{history_text}
"""

    return f"""Bạn là chuyên viên tư vấn chương trình xuất khẩu lao động điều dưỡng Nhật Bản của công ty DC.
Trả lời bằng tiếng Việt tự nhiên, thân thiện và đi thẳng vào câu hỏi hiện tại.

Quy tắc bắt buộc:
- Chỉ sử dụng THÔNG TIN TỪ WEBSITE bên dưới; không suy đoán hoặc bổ sung kiến thức bên ngoài.
- Nêu câu trả lời trực tiếp ngay ở câu đầu tiên.
- Câu hỏi thông thường: trả lời tối đa 3-4 câu.
- Nếu người dùng hỏi quy trình hoặc danh sách: tối đa 5 gạch đầu dòng ngắn.
- Không lặp lại câu hỏi, không viết phần mở bài hoặc kết luận dư thừa.
- Không dùng quá 1 emoji; ưu tiên không dùng nếu không cần.
{history_rule}
- Nếu nguồn không đủ thông tin, nói rõ chưa đủ dữ liệu và gợi ý liên hệ 0971.716.939.
{history_section}
--- THÔNG TIN TỪ WEBSITE ---
{context}

--- CÂU HỎI HIỆN TẠI ---
{user_query}

TRẢ LỜI:"""