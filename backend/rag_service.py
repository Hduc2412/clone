import os
import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "xkld_knowledge"
EMBEDDING_MODEL = "gemini-embedding-001"
VECTOR_SIZE = 3072
TOP_K = 5

qdrant = QdrantClient(url=QDRANT_URL)


def search_context(query: str) -> list:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent?key={GEMINI_API_KEY}"
    payload = {
        "model": f"models/{EMBEDDING_MODEL}",
        "content": {"parts": [{"text": query}]},
        "taskType": "RETRIEVAL_QUERY"
    }
    res = requests.post(url, json=payload)
    data = res.json()
    
    if "error" in data:
        print(f"Lỗi API: {data['error']['message']}")
        return []
    
    query_vector = data["embedding"]["values"]
    print(f"Query vector size: {len(query_vector)}" )

    hits = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=TOP_K
    ).points
    return hits


def build_context_text(hits: list) -> str:
    parts = []
    for hit in hits:
        title = hit.payload.get("title", "")
        text = hit.payload.get("text", "")
        url = hit.payload.get("url", "")
        parts.append(f"[{title}]\n{text}\n(Nguồn: {url})")
    return "\n\n---\n\n".join(parts)


def answer_with_rag(user_query: str) -> dict:
    hits = search_context(user_query)
    if not hits:
        return {
            "answer": "Xin lỗi, tôi không tìm thấy thông tin liên quan. Vui lòng liên hệ trực tiếp để được tư vấn.",
            "sources": []
        }
    for hit in hits[:2]:
        print(f"Score: {hit.score}")
        print(f"Text: {hit.payload.get('text', '')[:200]}")
        print("---")

    context = build_context_text(hits)

    prompt = f"""Bạn là người chủ - chuyên viên tư vấn xuất khẩu lao động điều dưỡng tại Nhật Bản của công ty DC.
Bạn đã có nhiều năm kinh nghiệm tư vấn và hiểu rõ tâm lý của các bạn muốn đi Nhật.
Hãy trả lời như một người anh đang trò chuyện trực tiếp với em/bạn — thân thiện, nhiệt tình, dùng ngôn ngữ tự nhiên.

Quy tắc trả lời:
- Dùng "mình/bạn" hoặc "anh/em" tùy ngữ cảnh
- Trả lời dựa trên thông tin bên dưới, KHÔNG bịa đặt số liệu
- Nếu không có thông tin, nói thẳng và gợi ý liên hệ: 0971.716.939
- Có thể dùng emoji cho sinh động 😊
- Trả lời ngắn gọn, đi thẳng vào vấn đề, không dài dòng

THÔNG TIN THAM KHẢO:
{context}

CÂU HỎI: {user_query}

TRẢ LỜI:"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    res = requests.post(url, json=payload)
    answer = res.json()["candidates"][0]["content"]["parts"][0]["text"]

    sources = []
    seen = set()
    for hit in hits:
        hit_url = hit.payload.get("url", "")
        if hit_url and hit_url not in seen:
            seen.add(hit_url)
            sources.append({
                "title": hit.payload.get("title", ""),
                "url": hit_url,
                "image": hit.payload.get("image", ""),
                "score": round(hit.score, 3)
            })

    return {"answer": answer, "sources": sources}

if __name__ == "__main__":
    result = answer_with_rag("Cách tính lương bên Nhật")
    print(qdrant.get_collection(COLLECTION_NAME))
    print(result['answer'])

