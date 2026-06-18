import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.chat_service import process_message
from app.conversation.session_manager import session_manager

router = APIRouter()



class ChatRequest(BaseModel):
    message: str
    session_id: str | None = Field(default=None)


class ChatResponse(BaseModel):
    answer: str
    sources: list
    session_id: str
    intent: str = "chung"


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    sid = request.session_id or str(uuid.uuid4())
    result = process_message(request.message, session_id=sid)
    return result


@router.delete("/chat/session/{session_id}", status_code=204)
async def clear_session(session_id: str):
    session_manager.delete(session_id)


@router.get("/chat/session/{session_id}")
async def get_session_info(session_id: str):
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session không tồn tại hoặc đã hết hạn")
    return session.summary()


