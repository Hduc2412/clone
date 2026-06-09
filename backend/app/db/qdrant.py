import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "xkld_knowledge"

_client = None

def get_qdrant_client() -> QdrantClient:
    """ Singletion - chi tao 1 connection duy nhat"""
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL)
    return _client
