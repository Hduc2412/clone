
# Điều phối toàn bộ luồng xử lý từ câu hỏi đến câu trả lời.
from fastapi.concurrency import run_in_threadpool
import asyncio
import logging
from app.services.journey_profile import capture as capture_profile

from app.consultation import context_builder, next_question
from app.db import candidate_profiles as profiles
from app.db import session_memory
from app.memory import render as bo_nho_render
from app.memory import topics as bo_nho_topics
from app.rag import job_lookup
from app.rag.retriever import search
from app.rag.prompt_builder import build_context, build_prompt
from app.llm.gemini import generate_response
from app.conversation.session_manager import session_manager
from app.conversation.reference_resolver import resolve
from app.conversation.intent_classifier import classify
from app.conversation.response_validator import validate
from app.conversation.fallback_messages import (
    LEAD_NO_KNOWLEDGE,
    NO_KNOWLEDGE,
    looks_like_refusal,
)
from app.db.database import get_booking_draft, get_messages, save_message
from app.booking.booking_service import process_booking_message

logger = logging.getLogger(__name__)


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

    # Câu hỏi nối tiếp kiểu "thế cái đó có gồm... không?" không chứa từ khóa nào,
    # nên phân loại trên câu gốc sẽ ra "chung" và mất luôn bộ lọc topic.
    # Chỉ khi câu gốc không cho ra ý định nào thì mới dựa vào ngữ cảnh đã bồi.
    intent = classify(user_query)
    if intent == "chung" and resolved_query != user_query:
        intent = classify(resolved_query)
    logger.debug("Ý định của lượt này: %s", intent)

    # Booking là luồng nghiệp vụ riêng, không tạo hoặc cập nhật lead.
    if intent == "booking" or session.booking_step is not None:
        answer, _ = await process_booking_message(session, user_query)
        session.add_message("assistant", answer)
        await _save_exchange(session_id, user_query, answer, "booking")
        return _response(answer, [], session_id, "booking", is_fallback=False)

    # Embedding + Qdrant client đang là API đồng bộ; chạy ngoài event loop.
    hits = await run_in_threadpool(search, resolved_query, intent)

    # Câu hỏi nhắc tới một tỉnh hoặc vùng ở Nhật thì tra thẳng danh mục đơn hàng.
    # Kho tri thức chỉ có tài liệu chính sách, không có đơn nào — nên "muốn đi
    # Tokyo có được không" là câu hệ thống biết đáp án mà chatbot vẫn chịu, chỉ
    # vì đáp án nằm ở nửa kia. Việc dò tỉnh là tất định, không hỏi mô hình.
    job_block = await job_lookup.context_for(resolved_query)

    # Hồ sơ của chính người đang nhắn.
    #
    # Trước 22/09/2026 luồng chat chưa bao giờ đọc hồ sơ, dù nó và trang tư vấn
    # dùng chung một mã phiên. Đo trên máy chủ thật: một khách đã khai N4, ba năm
    # kinh nghiệm, muốn đi Tokyo, và hệ thống đã xếp hạng 11 đơn cho họ — nhưng
    # hỏi trong chat thì bot trả lời như với người lạ. Hệ thống biết, chatbot
    # không, chỉ vì không ai nối hai nửa lại.
    #
    # Khối này sinh bằng mã, tách rõ đã-xác-nhận / đọc-từ-CV / nghe-trong-hội-thoại.
    profile_block = await _profile_context(session_id)

    # Bộ nhớ dùng chung với phòng tư vấn theo đơn.
    #
    # Mẩu quan trọng nhất ở đây là ĐƠN KHÁCH ĐANG XEM. Không có nó thì khối
    # `job_block` ngay trên phải đoán đơn bằng cách dò tên tỉnh trong câu hỏi —
    # nên khách đang mở một đơn Tokyo rồi hỏi trống không "đơn này lương bao
    # nhiêu" thì hoặc là chịu, hoặc tệ hơn là vớ nhầm một đơn Tokyo khác và trả
    # lời rất trôi chảy bằng số của đơn không liên quan.
    #
    # Khối này KHÔNG chứa câu trả lời nào của phía tư vấn, chỉ chứa chủ đề đã
    # bàn. Xem `app/memory/__init__.py`.
    bo_nho_block = bo_nho_render.render(
        await _bo_nho(session_id), cho=session_memory.BEN_CHAT
    )

    if not hits and not job_block:
        answer = LEAD_NO_KNOWLEDGE if intent == "lead" else NO_KNOWLEDGE
        session.add_message("assistant", answer)
        await _save_exchange(session_id, user_query, answer, intent, is_fallback=True)
        return _response(answer, [], session_id, intent, is_fallback=True)

    # 3. Build prompt có lịch sử
    context = build_context(hits)
    # Thứ tự có chủ ý: hồ sơ khách trước, rồi danh mục đơn, rồi tài liệu chính
    # sách. Hai khối đầu nói về đúng người đang hỏi; tài liệu chỉ là nền.
    for khoi in (bo_nho_block, job_block, profile_block):
        if khoi:
            context = f"{khoi}\n\n---\n\n{context}" if context else khoi
    prompt = build_prompt(context, user_query, history_text)

    # 4. Gọi Gemini
    # requests.post của Gemini là đồng bộ; không chặn các request FastAPI khác.
    answer = await run_in_threadpool(generate_response, prompt)

    # 5. Validate câu trả lời
    # Truyền câu của khách vào để bộ kiểm biết số nào là số khách vừa nhắn: bot
    # được nhắc lại số đó, còn số nào không có trong câu của khách thì chặn.
    is_valid, answer = validate(answer, intent, user_message=user_query)

    # Câu trả lời bị chặn thì không được kèm nguồn: nói "chưa có thông tin"
    # mà vẫn hiện link tham khảo là tự mâu thuẫn trên màn hình người dùng.
    if not is_valid:
        session.add_message("assistant", answer)
        await _save_exchange(session_id, user_query, answer, intent, is_fallback=True)
        return _response(answer, [], session_id, intent, is_fallback=True)

    # Mô hình có thể tự từ chối bằng lời của nó, không dùng câu dự phòng nào.
    # Những câu đó trước đây được ghi nhận như trả lời thành công, nên tỷ lệ
    # "trả lời được" trong thống kê cao hơn thực tế. Đây cũng là lý do không kèm
    # nguồn: nói "website chưa có thông tin này" mà vẫn hiện link tham khảo là
    # tự mâu thuẫn ngay trên màn hình người dùng.
    if looks_like_refusal(answer):
        session.add_message("assistant", answer)
        await _save_exchange(session_id, user_query, answer, intent, is_fallback=True)
        return _response(answer, [], session_id, intent, is_fallback=True)

    if intent == "lead":
        answer += (
            "\n\nNếu muốn nhân viên liên hệ, bạn có thể nhắn "
            "**đặt lịch tư vấn**."
        )

    # 6. Lưu câu trả lời vào session + DB
    session.add_message("assistant", answer)
    await _save_exchange(session_id, user_query, answer, intent)

    # 7. Tổng hợp sources
    return _response(
        answer, _build_sources(hits), session_id, intent, is_fallback=False
    )


async def _profile_context(session_id: str) -> str:
    """Khối hồ sơ khách, kèm gợi ý hỏi thêm nếu còn thiếu dữ liệu.

    Không được phép làm hỏng một câu trả lời vốn đã trả lời được. Hồ sơ là thứ
    làm câu trả lời *tốt hơn*, không phải điều kiện để có câu trả lời — nên cơ
    sở dữ liệu trục trặc thì bot vẫn trả lời như trước khi có tính năng này.
    """
    try:
        profile = await profiles.get_by_session(session_id)
    except Exception:  # noqa: BLE001
        logger.warning("Không đọc được hồ sơ cho ngữ cảnh chat", exc_info=True)
        return ""

    if profile is None:
        return ""

    profiles.decorate(profile)
    cac_khoi = [context_builder.render(profile), next_question.render(profile)]
    return "\n\n".join(khoi for khoi in cac_khoi if khoi)


def _response(
    answer: str,
    sources: list,
    session_id: str,
    intent: str,
    is_fallback: bool,
) -> dict:
    """Một hình dạng response duy nhất cho mọi nhánh của luồng chat."""
    return {
        "answer": answer,
        "sources": sources,
        "session_id": session_id,
        "intent": intent,
        "is_fallback": is_fallback,
    }


def _build_sources(hits: list, limit: int = 3) -> list[dict]:
    sources: list[dict] = []
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
        if len(sources) == limit:
            break
    return sources


async def _save_exchange(
    session_id: str,
    user_query: str,
    answer: str,
    intent: str,
    is_fallback: bool = False,
) -> None:
    await save_message(session_id, "user", user_query, intent)
    await save_message(
        session_id, "assistant", answer, intent, is_fallback=is_fallback
    )
    # Ghi chủ đề khách vừa hỏi vào bộ nhớ chung, để phòng tư vấn theo đơn biết
    # mối lo thật của họ. Chỉ ghi nhãn chủ đề và câu hỏi nguyên văn của khách —
    # không bao giờ ghi câu trả lời, xem `app/memory/__init__.py`.
    chu_de = bo_nho_topics.phan_loai(user_query)
    if chu_de:
        try:
            await session_memory.ghi_moi_quan_tam(
                session_id,
                chu_de=chu_de,
                cau_hoi=user_query,
                ben=session_memory.BEN_CHAT,
            )
            if not is_fallback:
                await session_memory.ghi_da_giai_thich(
                    session_id, chu_de=chu_de, ben=session_memory.BEN_CHAT
                )
        except Exception:
            # Bộ nhớ chung là phần thêm vào. Hỏng nó không được làm hỏng một câu
            # trả lời vốn đã đúng và đã lưu xong.
            logger.warning("Không ghi được bộ nhớ chung của phiên", exc_info=True)

    try:
        await asyncio.wait_for(capture_profile(session_id, user_query, intent), timeout=3)
    except Exception:
        # The exchange is durable already. Do not fail an otherwise valid answer
        # or log the customer's personal message when enrichment is unavailable.
        logger.warning("Chat profile intake unavailable", exc_info=True)


async def _bo_nho(session_id: str) -> dict | None:
    """Đọc bộ nhớ chung, nuốt lỗi.

    Cùng lý do với `_profile_context`: khung chat vẫn phải trả lời được khi phần
    nghiệp vụ chưa dựng xong hoặc database trục trặc. Không có bộ nhớ thì câu
    trả lời nghèo đi một chút, còn ném lỗi ra thì khách không nhận được gì.
    """
    try:
        return await session_memory.lay(session_id)
    except Exception:
        logger.warning("Không đọc được bộ nhớ chung của phiên", exc_info=True)
        return None
