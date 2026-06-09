#ghep context tu Qdrant + cau hoi user thanh 1 prompt hoan chinh de gui cho gemini
def build_context(hits: list) -> str:
    """Gộp các chunk tìm được thành 1 đoạn context"""
    parts = []
    for hit in hits:
        title = hit.payload.get("title", "")
        text = hit.payload.get("text", "")
        url = hit.payload.get("url", "")
        parts.append(f"[{title}]\n{text}\n(Nguồn: {url})")
    return "\n\n---\n\n".join(parts)

def build_prompt(context: str, user_query: str, chat_history: list) -> str:
   """Build prompt hoàn chỉnh cho Gemini"""
   history_section = f"\nLICH SU HOI THOAI:\n{chat_history}\n" if chat_history else ""

   return f"""Bạn là nhân viên - chuyên viên tư vấn xuất khẩu lao động điều dưỡng tại Nhật Bản của công ty DC.
Bạn đã có nhiều năm kinh nghiệm tư vấn và hiểu rõ tâm lý của các bạn muốn đi Nhật.
Hãy trả lời như một người anh đang trò chuyện trực tiếp — thân thiện, nhiệt tình, dùng ngôn ngữ tự nhiên.

Quy tắc:
- Dùng "mình/bạn" hoặc "anh/em" tùy ngữ cảnh
- Chỉ trả lời dựa trên thông tin bên dưới, KHÔNG ĐƯỢC BỊA ĐẶT HAY TÌM THÔNG TIN Ở BÊN NGOÀI 
- Nếu không đủ thông tin, gợi ý liên hệ: 0971.716.939
- Dùng emoji cho sinh động 
- Ngắn gọn, đi thẳng vào vấn đề
{history_section}
THÔNG TIN THAM KHẢO:
{context}

CÂU HỎI: {user_query}

TRẢ LỜI:""" 

                                