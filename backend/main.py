# Nhiệm vụ: Cửa ngõ tiếp nhận request từ người dùng
#           Điều phối sang gemini_service để xử lý

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from gemini_service import get_gemini_response

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
    reply: str #Câu trả lời bằng lời
    image_content: str #Link ảnh minh họa (nếu có)

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
@app.post("/chat")
def chat(request: ChatRequest):
    #goi Gemini service de xu ly cua tra loi + image_url
    result = get_gemini_response(request.message)

    return {
        "reply": result["reply"],
        "image_url": result["image_url"]
    }
