# tao vector cho query, sau do tim TOP_K chunk gan nhat trong Qdrant
from app.db.qdrant import get_qdrant_client, COLLECTION_NAME
from app.llm.gemini import create_embedding

TOP_K = 5

def search(query: str) -> list:
    """Embed query → tìm TOP_K chunk gần nhất trong Qdrant"""
    query_vector = create_embedding(query)
    if not query_vector:
        return []

    qdrant = get_qdrant_client()
    hits = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=TOP_K
    ).points

    return hits