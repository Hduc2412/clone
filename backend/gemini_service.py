import os
import requests
from dotenv import load_dotenv
from crawler import get_section_content


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

SYSTEM_PROMPT = """Bạn là nhân viên tư vấn của DC Trung Tâm Học, 
chuyên tư vấn xuất khẩu lao động điều dưỡng sang Nhật Bản.

Nguyên tắc:
- Trả lời lịch sự, thân thiện, rõ ràng
- Tự động nhận diện ngôn ngữ khách dùng và trả lời đúng ngôn ngữ đó
- Chỉ tư vấn dựa trên thông tin thật của công ty
- Cuối câu trả lời gợi ý khách liên hệ: 0971.716.939
"""

def get_gemini_response(message: str) -> dict:
    """
    Hàm chính: Nhận câu hỏi, trả về câu trả lời từ Gemini
    Nếu câu hỏi liên quan đến bài viết trên web, trả về thông tin bài viết đó
    Nếu câu hỏi liên quan đến ảnh, trả về nội dung đọc được từ ảnh
    """
    # Bước 1: Tìm kiếm thông tin bài viết phù hợp dựa trên câu hỏi
    if not message.strip():
        return {
            "reply": "Vui lòng nhập câu hỏi.",
            "image_content": None
        }
    try:
        section_data = get_section_content(message)

        image_content = ""
        best_image_url = None

        if section_data["posts"]:
            #Buoc 2: Nếu có bài viết phù hợp, lấy ảnh đầu tiên để đọc nội dung
            best_post = section_data["posts"][0]
            best_image_url = best_post["image"]

            print(f"Đang đọc ảnh: {best_post['title']}")
            #Bước 3: Gửi ảnh lên Gemini Vision để đọc nội dung
            image_content = read_image_content(best_image_url, message)

        #Bước 4: Gửi câu hỏi + nội dung ảnh lên Gemini để tạo câu trả lời
        context = ""
        if image_content:
            context = f""" Thông tin từ tài liệu của công ty: {image_content} 
Dựa vào thông tin trên, hãy trả lời câu hỏi của khách hàng """
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"{SYSTEM_PROMPT}\n\n{context}\n\nKhách hàng hỏi: {message}"
                        }
                    ]
                }
            ]
        }

        response = requests.post(GEMINI_URL, json=payload)
        response.encoding = 'utf-8'
        data = response.json()

        if "candidates" in data:
            reply = data["candidates"][0]["content"]["parts"][0]["text"]
        elif "error" in data:
            reply = f"Xin lỗi, hệ thống gặp lỗi: {data['error']['message']}"
        else:
            reply = "Xin lỗi, không thể xử lý câu hỏi lúc này."   
        return {
            "reply": reply,
            "image_url": best_image_url,
        }
    except Exception as e:
        print(f"Loi: {e}")
        return {
            "reply": "Xin lỗi, hệ thống gặp sự cố. Vui lòng thử lại sau.",
            "image_url": None
        }