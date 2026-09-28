import logging
import uuid
from uuid import UUID

from fastapi import APIRouter, Cookie, HTTPException, Request, Path, Response
from pydantic import BaseModel, Field, field_validator
from app.auth.journey_security import (
    attach_cookie,
    new_session_id,
    session_from_cookie,
)
from app.services.chat_service import process_message
from app.conversation.session_manager import session_manager
from app.core.config import settings
from app.db.database import delete_session_data
from app.core.rate_limit import chat_rate_key, rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter()



class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None)

    @field_validator("session_id")
    @classmethod
    def validate_session(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = UUID(value)
        # Preserve legacy CV hex IDs; rewriting them disconnects their documents.
        return parsed.hex if len(value) == 32 else str(parsed)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tin nhắn không được để trống.")
        return value


class ChatResponse(BaseModel):
    answer: str
    sources: list
    session_id: str
    intent: str = "chung"
    # True khi hệ thống không đủ căn cứ để trả lời và phải dùng câu dự phòng.
    # Frontend dựa vào đây để hiển thị khác đi, và Analytics đếm tỷ lệ fallback.
    is_fallback: bool = False


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    response: Response,
    journey_cookie: str | None = Cookie(
        default=None, alias=settings.journey_cookie_name
    ),
):
    """Cửa vào của cả hành trình tư vấn — và cũng là nơi phát mã phiên.

    Mã phiên **do máy chủ sinh**, không lấy từ thân yêu cầu. Bản cũ nhận
    `session_id` client gửi lên và dùng luôn; vì mọi đường `/public/*` nhận diện
    người dùng bằng đúng mã ấy, gửi lên mã của người khác là ghi được vào hồ sơ
    của họ. Nay mã nằm trong một cookie đã ký, và `request.session_id` chỉ còn
    được dùng để **so** chứ không để tin.

    Khách vãng lai vẫn không phải đăng nhập: lượt chat đầu tiên tự mở phiên.
    """
    rate_limiter.check(chat_rate_key(http_request), limit=20, window_seconds=60)

    sid = session_from_cookie(journey_cookie)
    if sid is None:
        sid = new_session_id()
        attach_cookie(response, sid)
    elif request.session_id and request.session_id != sid:
        # Trình duyệt nhớ một mã khác với mã trong cookie. Thường là do dữ liệu
        # cũ còn sót trong `localStorage` sau khi cách xác thực thay đổi. Không
        # chiều theo mã client gửi — đó chính là lỗ hổng vừa vá — nhưng cũng
        # không dựng rào giữa cuộc trò chuyện: cứ trả lời trên phiên của cookie
        # và để phía giao diện tự cập nhật lại mã nó đang giữ.
        logger.info("Mã phiên client gửi lên không khớp cookie; dùng mã của cookie")

    result = await process_message(request.message, session_id=sid)
    # Trả mã phiên thật về để giao diện đồng bộ lại; nội dung nhạy cảm vẫn chỉ
    # lấy được khi kèm cookie.
    result["session_id"] = sid
    return result


def _phien_cua_chinh_minh(session_id: str, journey_cookie: str | None) -> str:
    """Hai đường dưới đây đụng vào hội thoại của một người cụ thể.

    `GET` trả về tóm tắt phiên, trong đó có lịch sử tin nhắn; `DELETE` xoá sạch
    dữ liệu của phiên. Cả hai trước đây chỉ kiểm hình dạng mã phiên, nên biết mã
    là đọc được hội thoại của người khác — hoặc xoá nó đi.
    """
    sid = ChatRequest.validate_session(session_id)
    cookie_session = session_from_cookie(journey_cookie)
    if cookie_session is None or cookie_session != sid:
        raise HTTPException(status_code=403, detail="Phiên này không thuộc về bạn.")
    return sid


@router.delete("/chat/session/{session_id}", status_code=204)
async def clear_session(
    session_id: str = Path(pattern=r"^(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12})$"),
    journey_cookie: str | None = Cookie(
        default=None, alias=settings.journey_cookie_name
    ),
):
    sid = _phien_cua_chinh_minh(session_id, journey_cookie)
    session_manager.delete(sid)
    await delete_session_data(sid)


@router.get("/chat/session/{session_id}")
async def get_session_info(
    session_id: str = Path(pattern=r"^(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12})$"),
    journey_cookie: str | None = Cookie(
        default=None, alias=settings.journey_cookie_name
    ),
):
    session = session_manager.get(_phien_cua_chinh_minh(session_id, journey_cookie))
    if not session:
        raise HTTPException(status_code=404, detail="Session không tồn tại hoặc đã hết hạn")
    return session.summary()
