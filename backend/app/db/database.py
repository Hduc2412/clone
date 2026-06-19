"""
MongoDB persistence layer for chat sessions, messages, leads, and analytics.
"""
import os
from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING


MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "xkld_chatbot")

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def _now() -> datetime:
    return datetime.now(UTC)


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database has not been initialized. Call init_db() first.")
    return _db


async def init_db() -> None:
    """Connect to MongoDB and create indexes used by the application."""
    global _client, _db

    if _client is None:
        _client = AsyncIOMotorClient(MONGODB_URI)
        _db = _client[MONGODB_DB_NAME]

    db = get_db()
    await db.command("ping")

    await db.messages.create_index(
        [("session_id", ASCENDING), ("created_at", ASCENDING)]
    )
    await db.sessions.create_index("session_id", unique=True)
    await db.sessions.create_index("last_active")
    await db.leads.create_index([("session_id", ASCENDING), ("created_at", DESCENDING)])
    await db.analytics.create_index("date", unique=True)

    print("[DB] MongoDB initialized successfully.")


async def close_db() -> None:
    """Close MongoDB connection on application shutdown."""
    global _client, _db

    if _client is not None:
        _client.close()
        _client = None
        _db = None


async def touch_session(session_id: str, intent: str | None = None) -> None:
    """Create or update a chat session record."""
    now = _now()
    update: dict[str, Any] = {
        "$set": {"last_active": now},
        "$setOnInsert": {"session_id": session_id, "created_at": now},
        "$inc": {"message_count": 1},
    }
    if intent:
        update["$set"]["last_intent"] = intent

    await get_db().sessions.update_one(
        {"session_id": session_id},
        update,
        upsert=True,
    )


async def save_message(
    session_id: str,
    role: str,
    content: str,
    intent: str = "chung",
) -> None:
    """Save one chat message into MongoDB."""
    now = _now()
    await get_db().messages.insert_one(
        {
            "session_id": session_id,
            "role": role,
            "content": content,
            "intent": intent,
            "created_at": now,
        }
    )
    await touch_session(session_id, intent=intent)


async def save_lead(
    session_id: str,
    name: str | None = None,
    phone: str | None = None,
    note: str | None = None,
) -> None:
    """Save a potential customer lead."""
    now = _now()
    await get_db().leads.insert_one(
        {
            "session_id": session_id,
            "name": name,
            "phone": phone,
            "note": note,
            "created_at": now,
            "updated_at": now,
        }
    )


async def get_messages(session_id: str) -> list[dict[str, Any]]:
    """Get all messages for one session."""
    cursor = (
        get_db()
        .messages.find(
            {"session_id": session_id},
            {"_id": 0, "role": 1, "content": 1, "intent": 1, "created_at": 1},
        )
        .sort("created_at", ASCENDING)
    )
    return await cursor.to_list(length=None)


async def get_message(session_id: str) -> list[dict[str, Any]]:
    """Backward-compatible alias for get_messages()."""
    return await get_messages(session_id)


async def get_all_leads() -> list[dict[str, Any]]:
    """Get all leads for future analytics/admin views."""
    cursor = (
        get_db()
        .leads.find(
            {},
            {
                "_id": 0,
                "session_id": 1,
                "name": 1,
                "phone": 1,
                "note": 1,
                "created_at": 1,
                "updated_at": 1,
            },
        )
        .sort("created_at", DESCENDING)
    )
    return await cursor.to_list(length=None)


async def delete_session_data(session_id: str) -> None:
    """Delete chat/session records only; keep leads as business data."""
    db = get_db()
    await db.messages.delete_many({"session_id": session_id})
    await db.sessions.delete_one({"session_id": session_id})
