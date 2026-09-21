import math
import re
import threading
import time
from collections import OrderedDict

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

    # Gộp **mọi** part có chữ, không chỉ part đầu.
    #
    # Gemini 2.5 Flash luôn trả về đúng một part, nên lấy `parts[0]` chạy đúng
    # suốt và lỗi nằm im. Đo thử gemini-3.8-flash ngày 21/09/2026: cùng một câu
    # hỏi, model chia câu trả lời thành nhiều part, và bản cũ trả về mỗi mẩu đầu
    # — khách nhận được "Nơi làm việc do từng đơn hàng quy định và" rồi hết.
    #
    # Hỏng kiểu này không báo lỗi: câu vẫn là tiếng Việt, vẫn đúng ngữ pháp ở
    # chỗ bị cắt, chỉ là cụt. Bộ kiểm chứng cũng không bắt được vì nó dài hơn
    # ngưỡng tối thiểu.
    #
    # Bỏ qua part suy luận (`thought`): đó là phần nháp của model, không phải
    # câu trả lời cho khách.
    parts = candidate.get("content", {}).get("parts", [])
    text = "".join(
        part["text"] for part in parts
        if part.get("text") and not part.get("thought")
    )
    if not text:
        return "Lỗi Gemini: Không nhận được nội dung trả lời"
    return text

# Hai vai khác nhau, hai không gian vector khác nhau. Câu hỏi của người dùng nhúng
# kiểu QUERY, còn đoạn tài liệu nằm trong kho phải nhúng kiểu DOCUMENT. Dùng lẫn
# thì vẫn ra vector và vẫn tính được độ gần nghĩa, nên hỏng mà không báo lỗi —
# chỉ thấy điểm thấp đi và đoạn đúng tụt hạng.
#
# Đo trên một đoạn thật: cùng câu hỏi, đoạn nhúng kiểu QUERY được 0,6423, nhúng
# đúng kiểu DOCUMENT được 0,7006. Chênh 0,06 — vừa đúng khoảng làm đoạn đúng rơi
# khỏi ngưỡng lọc.
TASK_QUERY = "RETRIEVAL_QUERY"
TASK_DOCUMENT = "RETRIEVAL_DOCUMENT"


# Nhớ đệm vector của câu hỏi.
#
# Mỗi lượt chat đi ra Internet **hai lần**: một lần nhúng câu hỏi, một lần sinh
# chữ. Đo trên máy thật: nhúng mất ~700 ms trong tổng 3,1–3,9 s, tức khoảng một
# phần năm thời gian chờ — cho một việc mà cùng một câu hỏi luôn ra cùng một kết
# quả.
#
# Trong lĩnh vực này khách hỏi đi hỏi lại đúng mấy câu (chi phí, điều kiện, lương),
# nên tỷ lệ trúng đệm sẽ cao. Mỗi vector 3072 chiều ≈ 24KB, nên 256 mục ≈ 6MB —
# đủ nhỏ để nằm trong tiến trình, đủ lớn để phủ hết các câu hay gặp.
#
# Đệm nằm trong bộ nhớ tiến trình nên chạy nhiều worker thì mỗi worker có đệm
# riêng. Chấp nhận được: đệm lạnh chỉ có nghĩa là chậm bằng lúc chưa có đệm.
_CACHE_SIZE = 256
_embedding_cache: "OrderedDict[tuple[str, str], list]" = OrderedDict()
_cache_lock = threading.Lock()


def clear_embedding_cache() -> None:
    """Xoá đệm. Dùng trong kiểm thử, và khi kho tri thức vừa được nhúng lại."""
    with _cache_lock:
        _embedding_cache.clear()


def _cache_get(key: tuple[str, str]) -> list | None:
    with _cache_lock:
        vector = _embedding_cache.get(key)
        if vector is None:
            return None
        _embedding_cache.move_to_end(key)
        # Trả bản sao: người gọi sửa vào danh sách trả về thì mục trong đệm hỏng
        # theo, và lỗi đó sẽ hiện ra ở một câu hỏi khác hẳn.
        return list(vector)


def _cache_put(key: tuple[str, str], vector: list) -> None:
    with _cache_lock:
        _embedding_cache[key] = list(vector)
        _embedding_cache.move_to_end(key)
        while len(_embedding_cache) > _CACHE_SIZE:
            _embedding_cache.popitem(last=False)


def create_embedding(text: str, task_type: str = TASK_QUERY) -> list | None:
    key = ((text or "").strip(), task_type)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.embedding_model}:embedContent"
    )
    payload = {
        "model": f"models/{settings.embedding_model}",
        "content": {"parts": [{"text": text}]},
        "taskType": task_type,
    }
    data = _post_with_retry(url, payload, label="Gemini embedding")

    if "error" in data:
        print(f"Loi embedding: {data['error']['message']}")
        # Không nhớ đệm lần hỏng. Nhớ lại thì một trục trặc mạng thoáng qua sẽ
        # biến thành câu hỏi đó hỏng vĩnh viễn cho tới khi khởi động lại.
        return None

    vector = data["embedding"]["values"]
    _cache_put(key, vector)
    return vector
