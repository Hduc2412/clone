# Nhiệm vụ: Cửa ngõ tiếp nhận request từ người dùng
#           Điều phối sang gemini_service để xử lý
import traceback
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_service import answer_with_rag

app = FastAPI()
#CORS - cho phep frontend goi vao backend

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#Cấu trúc dữ liệu đầu vào(input)
class ChatRequest(BaseModel):
    message: str #Cau hoi tu khach

#Cau truc du lieu dau ra - them image_url so voi truoc

class ChatResponse(BaseModel):
    answer: str
    sources: list

#Endpoint kiểm tra sever
@app.get("/")
def read_root():
    return {"message": "Chatbot XKLD Dieu duong dang hoat dong! "}

@app.get("/health")
def health_check():
    return {"status": "ok"}
# Endpoint chat chính
# Luồng:
#   1. Nhận message từ khách
#   2. Gọi gemini_service xử lý
#   3. Nhận { reply, image_url }
#   4. Trả về cho khách
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        result = answer_with_rag(request.message)
        return result
    except Exception as e:
        traceback.print_exc()  # in lỗi ra terminal
        raise
    


