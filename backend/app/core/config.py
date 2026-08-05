import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=BACKEND_DIR / ".env")


def _as_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _origins() -> tuple[str, ...]:
    value = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:3001",
    )
    return tuple(origin.strip() for origin in value.split(",") if origin.strip())


@dataclass
class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001").strip()
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017").strip()
    mongodb_db_name: str = os.getenv("MONGODB_DB_NAME", "xkld_chatbot").strip()
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333").strip()
    qdrant_collection_name: str = os.getenv("QDRANT_COLLECTION_NAME", "xkld_knowledge").strip()
    min_retrieval_score: float = float(os.getenv("MIN_RETRIEVAL_SCORE", "0.65"))
    jwt_secret: str = os.getenv("JWT_SECRET", "").strip()
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
    auth_cookie_name: str = os.getenv("AUTH_COOKIE_NAME", "xkld_admin_session").strip()
    auth_cookie_secure: bool = _as_bool("AUTH_COOKIE_SECURE")
    cors_origins: tuple[str, ...] = _origins()
    initial_admin_email: str = os.getenv("INITIAL_ADMIN_EMAIL", "").strip().lower()
    initial_admin_name: str = os.getenv("INITIAL_ADMIN_NAME", "Quản trị viên").strip()
    initial_admin_password_hash: str = os.getenv("INITIAL_ADMIN_PASSWORD_HASH", "").strip()


settings = Settings()
