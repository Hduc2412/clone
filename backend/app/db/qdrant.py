from qdrant_client import QdrantClient
from app.core.config import settings

COLLECTION_NAME = settings.qdrant_collection_name

_client = None

def get_qdrant_client() -> QdrantClient:
    """ Singletion - chi tao 1 connection duy nhat"""
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url)
    return _client
