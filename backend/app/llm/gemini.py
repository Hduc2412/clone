import os
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"
EMBEDDING_MODEL = "gemini-embedding-001"

def generate_response(prompt: str) -> str:
    url = f"https://generativelanguage,googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMNINI_API_KEY}"
    payload = {"content": [{"parts": [{"text": prompt}]}] }
    res = requests.post(url, json=payload)
    data = res.json()

    if "error" in data:
        return f"Loi Gemini: {data['error']['message']}"
    return data["candidates"][0]["content"]["parts"][0]["text"]

def create_embedding(text: str) -> list:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent?key={GEMINI_API_KEY}"
    payload = {
        "model": f"models/{EMBEDDING_MODEL}",
        "content": {"parts": [{"text": text}]},
        "taskType": "RETRIEVAL_QUERY"
    }
    res = requests.post(url, json=payload)
    data = res.json()

    if "error" in data:
        print(f"Lỗi embedding: {data['error']['message']}")
        return None

    return data["embedding"]["values"]