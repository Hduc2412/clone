import math
import re
import time
import requests
from app.core.config import settings

MAX_RETRIES = 5
RETRY_DELAYS = [2, 5, 10]
RETRYABLE_CODES = {429, 500, 503}


def _get_retry_delay(error_message: str, attempt: int) -> int:
    match = re.search(
        r"retry in\s+([0-9.]+)s",
        error_message,
        flags=re.IGNORECASE,
    )
    if match:
        return max(1, math.ceil(float(match.group(1))) + 1)

    delay_index = min(attempt, len(RETRY_DELAYS) - 1)
    return RETRY_DELAYS[delay_index]


def _post_with_retry(
    url: str,
    payload: dict,
    label: str,
    max_retries: int = MAX_RETRIES,
    retry_rate_limit: bool = True,
) -> dict:
    last_error = None

    for attempt in range(max_retries):
        try:
            res = requests.post(
                url,
                json=payload,
                headers={"x-goog-api-key": settings.gemini_api_key},
                timeout=30,
            )
            data = res.json()

            if res.status_code == 200 and "error" not in data:
                return data
            if res.status_code in RETRYABLE_CODES:
                last_error = data.get("error", {}).get(
                    "message",
                    f"HTTP {res.status_code}",
                )
                if res.status_code == 429 and not retry_rate_limit:
                    return data
                if attempt >= max_retries - 1:
                    break
                wait = _get_retry_delay(last_error, attempt)
                print(f"[{label}] HTTP {res.status_code} - thu lai sau {wait}s (lan {attempt +1}/{max_retries})")
                time.sleep(wait)
                continue 
            error_msg = data.get("error", {}).get("message", "Unknown error")
            print(f"[{label}] Loi khong the retry: {error_msg}")
            return data
        
        except requests.exceptions.Timeout:
            last_error = "Request timeout"
            if attempt >= max_retries - 1:
                break
            wait = _get_retry_delay(last_error, attempt)
            print(f"[{label}] Timeout — thử lại sau {wait}s (lần {attempt + 1}/{max_retries})")
            time.sleep(wait)

        except requests.exceptions.RequestException as e:
            print(f"[{label}] Lỗi kết nối: {e}")
            last_error = str(e)
            break
    print(f"[{label}] Thất bại sau {max_retries} lần thử. Lỗi cuối: {last_error}")
    return {"error": {"message": last_error or "Max retries exceeded"}}

def generate_response(prompt: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            # Gemini 2.5 Flash mặc định dành một phần lớn token cho suy luận.
            # Tắt thinking vì đây là tác vụ RAG ngắn, cần ưu tiên token cho đáp án.
            "thinkingConfig": {"thinkingBudget": 0},
            "maxOutputTokens": 512,
        },
    }
    data = _post_with_retry(
        url,
        payload,
        label="Gemini generate",
        max_retries=3,
        retry_rate_limit=False,
    )
    
    if "error" in data:
        return f"Lỗi Gemini: {data['error']['message']}"

    candidates = data.get("candidates") or []
    if not candidates:
        return "Lỗi Gemini: Không nhận được nội dung trả lời"

    candidate = candidates[0]
    if candidate.get("finishReason") == "MAX_TOKENS":
        payload["generationConfig"]["maxOutputTokens"] = 768
        data = _post_with_retry(
            url,
            payload,
            label="Gemini generate retry",
            max_retries=1,
            retry_rate_limit=False,
        )
        if "error" in data:
            return f"Lỗi Gemini: {data['error']['message']}"
        candidates = data.get("candidates") or []
        if not candidates or candidates[0].get("finishReason") == "MAX_TOKENS":
            return "Lỗi Gemini: Câu trả lời bị giới hạn độ dài (MAX_TOKENS)"
        candidate = candidates[0]

    parts = candidate.get("content", {}).get("parts", [])
    if not parts or not parts[0].get("text"):
        return "Lỗi Gemini: Không nhận được nội dung trả lời"
    return parts[0]["text"]

def create_embedding(text: str) -> list | None:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.embedding_model}:embedContent"
    )
    payload = {
        "model": f"models/{settings.embedding_model}",
        "content": {"parts": [{"text": text}]},
        "taskType": "RETRIEVAL_QUERY",
    }
    data = _post_with_retry(url, payload, label="Gemini embedding")

    if "error" in data:
        print(f"Loi embedding: {data['error']['message']}")
        return None

    return data["embedding"]["values"]
