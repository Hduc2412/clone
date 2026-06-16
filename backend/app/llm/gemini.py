import os
import time
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"
EMBEDDING_MODEL = "gemini-embedding-001"

MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 10]
RETRYABLE_CODES = {429, 500, 503}

def _post_with_retry(url: str, payload: dict, label: str) -> dict:
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            res = requests.post(url, json=payload, timeout=30)
            data = res.json()

            if res.status_code == 200 and "error" not in data:
                return data
            if res.status_code in RETRYABLE_CODES:
                wait = RETRY_DELAYS[attempt]
                print(f"[{label}] HTTP {res.status_code} - thu lai sau {wait}s (lan {attempt +1}/{MAX_RETRIES})")
                time.sleep(wait)
                last_error = data.get("error", {}).get("message", f"HTTP {res.status_code}")
                continue 
            error_msg = data.get("error", {}).get("message", "Unknown error")
            print(f"[{label}] Loi khong the retry: {error_msg}")
            return data
        
        except requests.exceptions.Timeout:
            wait = RETRY_DELAYS[attempt]
            print(f"[{label}] Timeout — thử lại sau {wait}s (lần {attempt + 1}/{MAX_RETRIES})")
            time.sleep(wait)
            last_error = "Request timeout"

        except requests.exceptions.RequestException as e:
            print(f"[{label}] Lỗi kết nối: {e}")
            last_error = str(e)
            break
    print(f"[{label}] Thất bại sau {MAX_RETRIES} lần thử. Lỗi cuối: {last_error}")
    return {"error": {"message": last_error or "Max retries exceeded"}}

def generate_response(prompt: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    data = _post_with_retry(url, payload, label="Gemini generate")
    
    if "error" in data:
        return f"Lỗi Gemini: {data['error']['message']}"

    return data["candidates"][0]["content"]["parts"][0]["text"]

def create_embedding(text: str) -> list | None:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{EMBEDDING_MODEL}:embedContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "model": f"models/{EMBEDDING_MODEL}",
        "content": {"parts": [{"text": text}]},
        "taskType": "RETRIEVAL_QUERY",
    }
    data = _post_with_retry(url, payload, label="Gemini embedding")

    if "error" in data:
        print(f"Loi embedding: {data['error']['message']}")
        return None

    return data["embedding"]["values"]
