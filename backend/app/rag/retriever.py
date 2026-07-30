import os

from app.db.qdrant import get_qdrant_client, COLLECTION_NAME
from app.llm.gemini import create_embedding
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
from qdrant_client import models
from app.rag.taxonomy import infer_topic

TOP_K = 5
MIN_RETRIEVAL_SCORE = float(os.getenv("MIN_RETRIEVAL_SCORE", "0.65"))

INTENT_TO_TOPICS = {
    "chi_phi": ["chi_phi"],
    "quy_trinh": ["quy_trinh"],
    "dieu_kien": ["dieu_kien"],
    "luong_thuong": ["luong_thuong"],
    "cong_viec": ["cong_viec"],
    "phong_van": ["phong_van"],
    "thoi_gian": ["thoi_gian"],
    "hoc_tap": ["hoc_tap"],
    "ky_tuc_xa": ["ky_tuc_xa"],
    "lead": ["chi_phi", "quy_trinh", "dieu_kien"],
    "chung": [],
}

def search(query: str, intent: str = "chung") -> list:
    """Embed query → tìm TOP_K chunk gần nhất trong Qdrant, filter theo intent"""
    query_vector = create_embedding(query)
    if not query_vector:
        return []

    qdrant = get_qdrant_client()

    # Lọc theo topic nghiệp vụ, không lọc theo section nguồn quá rộng.
    topics = INTENT_TO_TOPICS.get(intent, [])
    search_filter = None
    if topics:
        search_filter = models.Filter(
            should=[
                models.FieldCondition(
                    key="topic",
                    match=models.MatchValue(value=topic)
                )
                for topic in topics
            ]
        )

    try:
        hits = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=search_filter,
            limit=TOP_K
        ).points
    except (ResponseHandlingException, UnexpectedResponse) as exc:
        print(f"[Qdrant] Search failed: {exc}")
        return []

    hits = [hit for hit in hits if hit.score >= MIN_RETRIEVAL_SCORE]

    # Hỗ trợ dữ liệu cũ chưa có topic trong thời gian chuyển đổi.
    for hit in hits:
        if not hit.payload.get("topic"):
            hit.payload["topic"] = infer_topic(
                hit.payload.get("section", ""),
                hit.payload.get("title", ""),
            )

    return hits
