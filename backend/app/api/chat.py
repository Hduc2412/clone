import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Path
from pydantic import BaseModel, Field, field_validator
from app.services.chat_service import process_message
from app.conversation.session_manager import session_manager
from app.db.database import delete_session_data
from app.core.rate_limit import chat_rate_key, rate_limiter

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
async def chat(request: ChatRequest, http_request: Request):
    rate_limiter.check(chat_rate_key(http_request), limit=20, window_seconds=60)
    sid = str(request.session_id or uuid.uuid4())
    result = await process_message(request.message, session_id=sid)
    return result


@router.delete("/chat/session/{session_id}", status_code=204)
async def clear_session(session_id: str = Path(pattern=r"^(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12})$")):
    sid = ChatRequest.validate_session(session_id)
    session_manager.delete(sid)
    await delete_session_data(sid)


@router.get("/chat/session/{session_id}")
async def get_session_info(session_id: str = Path(pattern=r"^(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12})$")):
    session = session_manager.get(ChatRequest.validate_session(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session không tồn tại hoặc đã hết hạn")
    return session.summary()
