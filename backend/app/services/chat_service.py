
#điều phối toàn bộ luồng xử lý từ câu hỏi đến câu trả lời
from app.rag.retriever import search
from app.rag.prompt_builder import build_context, build_prompt
from app.llm.gemini import generate_response
from app.conversation.session_manager import session_manager
from app.conversation.reference_resolver import resolve
from app.conversation.intent_classifier import classify
from app.conversation.response_validator import validate
from app.db.database import get_booking_draft, get_messages, save_message
from app.booking.booking_service import process_booking_message

async def process_message(user_query: str, session_id: str) -> dict:
    # 1. Load / tạo session
    session = session_manager.get_or_create(session_id)

    if not session.restored_from_db:
        stored_messages = await get_messages(session_id)
        session.restore_history(stored_messages)
        booking_draft = await get_booking_draft(session_id)
        if booking_draft:
            session.booking_step = booking_draft.get("booking_step")
            session.booking_data = booking_draft.get("booking_data") or {}

    # 2. Lấy lịch sử TRƯỚC khi thêm tin nhắn mới
    history_text = session.get_history_text()
    session.add_message("user", user_query)
    resolved_query = resolve(user_query, history_text)
    intent = classify(user_query)
    print(f"[ChatService] intent = '{intent}'")

    # Booking là luồng nghiệp vụ riêng, không tạo hoặc cập nhật lead.
    if intent == "booking" or session.booking_step is not None:
        answer, _ = await process_booking_message(session, user_query)
        session.add_message("assistant", answer)
        await _save_exchange(session_id, user_query, answer, "booking")
        return {
            "answer": answer,
            "sources": [],
            "session_id": session_id,
            "intent": "booking",
        }

    hits = search(resolved_query, intent=intent)
    if not hits:
        if intent == "lead":
            answer = (
                "Nếu bạn muốn nhân viên liên hệ, hãy nhắn **đặt lịch tư vấn** "
                "để mình hỗ trợ chọn ngày và giờ."
            )
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
    prompt = build_prompt(context, user_query, history_text)

    # 4. Gọi Gemini
    answer = generate_response(prompt)

    # 5. Validate câu trả lời
    _, answer = validate(answer, intent)

    if intent == "lead":
        answer += (
            "\n\nNếu muốn nhân viên liên hệ, bạn có thể nhắn "
            "**đặt lịch tư vấn**."
        )

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
                "topic": hit.payload.get("topic", None),
                "is_primary": len(sources) == 0,
            })
        if len(sources) == 3:
            break

    return {"answer": answer, "sources": sources, "session_id": session_id, "intent": intent}


async def _save_exchange(
    session_id: str,
    user_query: str,
    answer: str,
    intent: str,
) -> None:
    await save_message(session_id, "user", user_query, intent)
    await save_message(session_id, "assistant", answer, intent)
