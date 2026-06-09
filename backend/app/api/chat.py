from fastapi import APIRouter

from pydantic import BaseModel
from app.services.chat_service import process_message

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

class ChatResponese(BaseModel):
    answer: str
    sources: list

@router.post("/chat", response_model=ChatResponese)
async def chat(request: ChatRequest):
    result = process_message(request.message)
    return result


