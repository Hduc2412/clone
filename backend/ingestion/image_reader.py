# Nhiệm vụ: Gửi ảnh lên Gemini Vision để đọc nội dung
from urllib import response

import requests
import base64
import os 
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_VISION_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def get_best_image_url(image_url: str) -> str:
    """
    Chuyển link ảnh nhỏ sang ảnh gốc chất lượng cao
    Ví dụ: 2-6-247x247.jpg → 2-6.jpg
    """
    import re
    clean_url = re.sub(r'-\d+x\d+(\.\w+)$', r'\1', image_url)
    return clean_url

def read_image_content(image_url: str, question: str) -> str:
    """
     Gửi ảnh lên Gemini Vision
    Gemini đọc nội dung ảnh + trả lời câu hỏi dựa trên ảnh
    """
    try:
        best_url = get_best_image_url(image_url)
        image_response = requests.get(best_url, headers=HEADERS, timeout=15)

        if image_response.status_code != 200:
            print(f"Không thể tải ảnh: {image_url}")
            image_response = requests.get(image_url, headers=HEADERS, timeout=15) # Thử lại với link gốc

        image_base64 = base64.b64encode(image_response.content).decode('utf-8')
        print("Dang gui len Gemini Vision...")
        payLoad = {
            "contents": [
                {
                    "parts": [
                        {
                            # Câu lệnh cho Gemini đọc ảnh
                            "text": f"""Hãy đọc toàn bộ nội dung trong ảnh này và trả lời câu hỏi sau: {question}
                            
Yêu cầu:
- Đọc hết tất cả chữ trong ảnh
- Giữ nguyên các số liệu quan trọng
- Trả lời bằng ngôn ngữ của câu hỏi
- Trình bày rõ ràng, dễ hiểu"""
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_base64
                            }
                        }
                    ]
                }
            ]
        }
        reponse = requests.post(GEMINI_VISION_URL, json=payLoad)
        data = reponse.json()

        print(f"Status: {reponse.status_code}")

        if  "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        elif "error" in data:
            return f"Loi doc Anh: {data['error']['message']}"
        else:
            return "Khong the doc noi dung anh."
    except Exception as e:
        print(f"Error: {e}")
        return "Xin lỗi, đã có lỗi xảy ra khi xử lý yêu cầu của bạn."


    # Test thử