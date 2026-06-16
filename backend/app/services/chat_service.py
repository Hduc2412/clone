
#điều phối toàn bộ luồng xử lý từ câu hỏi đến câu trả lời
from app.rag.retriever import search
from app.rag.prompt_builder import build_context, build_prompt
from app.llm.gemini import generate_response
from app.conversation.session_manager import session_manager

def process_message(user_query: str, session_id: str) -> dict:
    # 1. Load / tạo session
    session = session_manager.get_or_create(session_id)
    session.add_message("user", user_query)

    # 2. Tìm context RAG
    hits = search(user_query)
    if not hits:
        answer = (
            "Xin lỗi, tôi không tìm thấy thông tin liên quan. "
            "Vui lòng liên hệ 0971.716.939 để được tư vấn trực tiếp."
        )
        session.add_message("assistant", answer)
        return {"answer": answer, "sources": [], "session_id": session_id}

    # 3. Build prompt có lịch sử
    context = build_context(hits)
    history_text = session.get_history_text()
    prompt = _build_prompt_with_history(context, user_query, history_text)

    # 4. Gọi Gemini
    answer = generate_response(prompt)

    # 5. Lưu câu trả lời vào session
    session.add_message("assistant", answer)

    # 6. Tổng hợp sources
    sources = []
    seen = set()
    for hit in hits:
        url = hit.payload.get("url", "")
        if url and url not in seen:
            seen.add(url)
            sources.append({
                "title": hit.payload.get("title", ""),
                "url": url,
                "image": hit.payload.get("image", ""),
                "score": round(hit.score, 3),
            })

    return {"answer": answer, "sources": sources, "session_id": session_id}


def _build_prompt_with_history(context: str, user_query: str, history_text: str) -> str:
    if not history_text:
        return build_prompt(context, user_query)

    return f"""Bạn là trợ lý tư vấn xuất khẩu lao động điều dưỡng sang Nhật Bản của xklddieuduong.vn.
Trả lời thân thiện, chính xác, dựa trên thông tin được cung cấp.

--- LỊCH SỬ HỘI THOẠI ---
{history_text}

--- THÔNG TIN TỪ WEBSITE ---
{context}

--- CÂU HỎI HIỆN TẠI ---
{user_query}

Trả lời:"""
        

