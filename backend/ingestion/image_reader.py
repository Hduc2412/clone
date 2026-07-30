# Nhiem vu: Gui anh len Gemini Vision de doc noi dung
import base64
import hashlib
import json
import math
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_VISION_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
VISION_TIMEOUT_SECONDS = int(os.getenv("VISION_TIMEOUT_SECONDS", "45"))
VISION_MAX_RETRIES = int(os.getenv("VISION_MAX_RETRIES", "5"))
VISION_RETRY_DELAY_SECONDS = int(os.getenv("VISION_RETRY_DELAY_SECONDS", "3"))
CACHE_PATH = Path(__file__).parent.parent / "data" / "image_vision_cache.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def _load_cache() -> dict:
    try:
        if CACHE_PATH.exists():
            with CACHE_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Không thể đọc cache ảnh: {e}")
    return {}


def _save_cache(cache: dict) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CACHE_PATH.open("w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Không thể lưu cache ảnh: {e}")


def _cache_key(image_url: str, question: str) -> str:
    raw_key = f"{image_url}|{question}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _get_retry_delay(error_message: str, attempt: int) -> int:
    """Ưu tiên thời gian chờ Gemini yêu cầu, nếu không có thì dùng backoff."""
    match = re.search(
        r"retry in\s+([0-9.]+)s",
        error_message,
        flags=re.IGNORECASE,
    )
    if match:
        return max(1, math.ceil(float(match.group(1))) + 1)
    return VISION_RETRY_DELAY_SECONDS * attempt


def get_best_image_url(image_url: str) -> str:
    """
    Chuyển link ảnh nhỏ sang ảnh gốc chất lượng cao.
    Ví dụ: 2-6-247x247.jpg -> 2-6.jpg
    """
    import re
    clean_url = re.sub(r'-\d+x\d+(\.\w+)$', r'\1', image_url)
    return clean_url


def read_image_content(image_url: str, question: str) -> str | None:
    """
    Gửi ảnh lên Gemini Vision để đọc nội dung ảnh và trả lời theo câu hỏi.
    Kết quả được cache theo URL ảnh + câu hỏi để lần sau không tốn quota.
    """
    try:
        best_url = get_best_image_url(image_url)
        cache_key = _cache_key(best_url, question)
        cache = _load_cache()
        cached = cache.get(cache_key)
        if cached:
            print("Dùng kết quả đọc ảnh từ cache")
            return cached.get("text", "")

        image_response = requests.get(best_url, headers=HEADERS, timeout=15)

        if image_response.status_code != 200:
            print(f"Không thể tải ảnh: {image_url}")
            image_response = requests.get(image_url, headers=HEADERS, timeout=15)

        if image_response.status_code != 200:
            return None

        image_base64 = base64.b64encode(image_response.content).decode("utf-8")
        print("Dang gui len Gemini Vision...")

        payload = {
            "contents": [
                {
                    "parts": [
                        {
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

        last_error = None
        for attempt in range(1, VISION_MAX_RETRIES + 1):
            response = requests.post(
                GEMINI_VISION_URL,
                json=payload,
                headers={"x-goog-api-key": GEMINI_API_KEY or ""},
                timeout=VISION_TIMEOUT_SECONDS,
            )
            data = response.json()
            print(f"Status: {response.status_code}")

            if "candidates" in data:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                cache[cache_key] = {
                    "image_url": best_url,
                    "question": question,
                    "text": text,
                }
                _save_cache(cache)
                return text

            if "error" in data:
                last_error = data["error"].get("message", "Không rõ lỗi")
                if response.status_code in (429, 500, 502, 503, 504) and attempt < VISION_MAX_RETRIES:
                    wait_time = _get_retry_delay(last_error, attempt)
                    print(f"Vision API tạm nghẽn, thử lại sau {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                print(f"Lỗi đọc ảnh: {last_error}")
                return None

            last_error = "Không thể đọc nội dung ảnh."
            if attempt < VISION_MAX_RETRIES:
                wait_time = _get_retry_delay(last_error or "", attempt)
                print(f"Vision API chưa trả kết quả hợp lệ, thử lại sau {wait_time}s...")
                time.sleep(wait_time)

        print(f"Không thể đọc nội dung ảnh: {last_error}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None
