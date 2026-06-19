
#điều phối toàn bộ luồng xử lý từ câu hỏi đến câu trả lời
from app.rag.retriever import search
from app.rag.prompt_builder import build_context, build_prompt
from app.llm.gemini import generate_response
from app.conversation.session_manager import session_manager
from app.conversation.reference_resolver import resolve
from app.conversation.intent_classifier import classify
from app.conversation.response_validator import validate
from app.db.database import save_message
from app.lead.lead_service import try_capture_lead, ASK_LEAD_MESSAGE

async def process_message(user_query: str, session_id: str) -> dict:
    # 1. Load / tạo session
    session = session_manager.get_or_create(session_id)
    
    # 2. Lấy lịch sử TRƯỚC khi thêm tin nhắn mới
    history_text = session.get_history_text()
    session.add_message("user", user_query)
    resolved_query = resolve(user_query, history_text)
    intent = classify(user_query)
    hits = search(resolved_query)
    if not hits:
        lead_info = await try_capture_lead(session_id, user_query, intent)
        if lead_info:
            answer = "Cảm ơn em! Anh Quang sẽ liên hệ lại sớm để tư vấn chi tiết nhé!"
        else:
            answer = (
                "Xin lỗi, tôi không tìm thấy thông tin liên quan. "
                "Vui lòng liên hệ 0971.716.939 để được tư vấn trực tiếp."
            )
        session.add_message("assistant", answer)
        await _save_exchange(session_id, user_query, answer, intent)
        return {
            "answer": answer,
            "sources": [],
            "session_id": session_id,
            "intent": intent,
        }

    # 3. Build prompt có lịch sử
    context = build_context(hits)
    prompt = _build_prompt_with_history(context, user_query, history_text)

    # 4. Gọi Gemini
    answer = generate_response(prompt)

    # 5. Validate câu trả lời
    _, answer = validate(answer, intent)

    # 6. Thử capture lead nếu user vừa cung cấp tên/SĐT
    lead_info = await try_capture_lead(session_id, user_query, intent)

    # 7. Nếu intent là lead nhưng chưa có thông tin → hỏi xin
    if intent == "lead" and not lead_info:
        answer += ASK_LEAD_MESSAGE

    # 8. Lưu câu trả lời vào session + DB
    session.add_message("assistant", answer)
    await _save_exchange(session_id, user_query, answer, intent)
    

    # 9. Tổng hợp sources
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

    return {"answer": answer, "sources": sources, "session_id": session_id, "intent": intent}


async def _save_exchange(
    session_id: str,
    user_query: str,
    answer: str,
    intent: str,
) -> None:
    await save_message(session_id, "user", user_query, intent)
    await save_message(session_id, "assistant", answer, intent)


def _build_prompt_with_history(context: str, user_query: str, history_text: str) -> str:
    if not history_text:
        return build_prompt(context, user_query)

    return f"""Bạn là trợ lý tư vấn xuất khẩu lao động điều dưỡng sang Nhật Bản của xklddieuduong.vn.
Trả lời thân thiện, chính xác, dựa trên thông tin được cung cấp.
Không chào hỏi lại nếu đã có lịch sử hội thoại, đi thẳng vào trả lời.

--- LỊCH SỬ HỘI THOẠI ---
{history_text}

Luu y bat buoc: neu da co lich su hoi thoai, khong mo dau bang "Chao ban",
"Xin chao", hoac bat ky loi chao nao. Tra loi truc tiep vao cau hoi hien tai.

--- THÔNG TIN TỪ WEBSITE ---
{context}

--- CÂU HỎI HIỆN TẠI ---
{user_query}

Trả lời:"""
        

