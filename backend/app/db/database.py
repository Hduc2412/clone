"""
MongoDB persistence layer for chat sessions, messages, leads, and analytics.
"""
import os
from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument


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
    await db.leads.create_index(
        "session_id",
        unique=True,
        name="unique_lead_session_id",
    )
    await db.analytics.create_index("date", unique=True)
    await db.consultation_appointments.create_index(
        "appointment_code",
        unique=True,
    )
    await db.consultation_appointments.create_index(
        [("status", ASCENDING), ("appointment_date", ASCENDING)],
    )
    await db.consultation_appointments.create_index(
        "booking_key",
        unique=True,
    )
    await db.notifications.create_index(
        [("is_read", ASCENDING), ("created_at", DESCENDING)],
    )
    await db.managed_leads.create_index("lead_code", unique=True)
    await db.managed_leads.create_index("phone")
    await db.managed_leads.create_index(
        [("status", ASCENDING), ("created_at", DESCENDING)]
    )
    await db.staff_users.create_index("email", unique=True)
    await db.staff_users.create_index("status")

    await _create_initial_admin()

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
) -> dict[str, Any]:
    """Tạo hoặc bổ sung lead của session mà không sinh bản ghi trùng."""
    now = _now()
    fields: dict[str, Any] = {"updated_at": now}
    if name:
        fields["name"] = name
    if phone:
        fields["phone"] = phone
    if note:
        fields["note"] = note

    lead = await get_db().leads.find_one_and_update(
        {"session_id": session_id},
        {
            "$set": fields,
            "$setOnInsert": {
                "session_id": session_id,
                "created_at": now,
            },
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={
            "_id": 0,
            "session_id": 1,
            "name": 1,
            "phone": 1,
            "note": 1,
            "created_at": 1,
            "updated_at": 1,
        },
    )
    return lead or {"session_id": session_id, **fields}


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


async def save_booking_draft(
    session_id: str,
    step: str | None,
    data: dict[str, Any],
) -> None:
    """Lưu tiến độ đặt lịch để không mất khi backend/session khởi động lại."""
    now = _now()
    await get_db().sessions.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "booking_step": step,
                "booking_data": data,
                "last_active": now,
            },
            "$setOnInsert": {
                "session_id": session_id,
                "created_at": now,
                "message_count": 0,
            },
        },
        upsert=True,
    )


async def get_booking_draft(session_id: str) -> dict[str, Any] | None:
    return await get_db().sessions.find_one(
        {"session_id": session_id},
        {"_id": 0, "booking_step": 1, "booking_data": 1},
    )


async def create_appointment(appointment: dict[str, Any]) -> dict[str, Any]:
    """Tạo lịch pending và thông báo nhân viên."""
    now = _now()
    document = {
        **appointment,
        "status": "pending",
        "confirmed_by": None,
        "confirmed_at": None,
        "contacted_at": None,
        "result_note": None,
        "created_at": now,
        "updated_at": now,
    }
    await get_db().consultation_appointments.insert_one(document)
    await get_db().notifications.insert_one(
        {
            "type": "new_appointment",
            "title": "Lịch tư vấn mới",
            "appointment_code": document["appointment_code"],
            "customer_name": document["customer_name"],
            "phone": document["phone"],
            "appointment_date": document["appointment_date"],
            "appointment_time": document["appointment_time"],
            "is_read": False,
            "created_at": now,
        }
    )
    return {key: value for key, value in document.items() if key != "_id"}


async def list_appointments(
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    query = {"status": status} if status else {}
    cursor = (
        get_db()
        .consultation_appointments.find(query, {"_id": 0, "booking_key": 0})
        .sort([("appointment_date", ASCENDING), ("appointment_time", ASCENDING)])
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def update_appointment_status(
    appointment_code: str,
    status: str,
    employee_name: str,
    result_note: str | None = None,
) -> dict[str, Any] | None:
    now = _now()
    fields: dict[str, Any] = {
        "status": status,
        "updated_at": now,
        "updated_by": employee_name,
    }
    if status == "confirmed":
        fields["confirmed_by"] = employee_name
        fields["confirmed_at"] = now
    if status in {"completed", "unreachable"}:
        fields["contacted_at"] = now
    if result_note is not None:
        fields["result_note"] = result_note

    allowed_previous_statuses = {
        "confirmed": ["pending"],
        "completed": ["confirmed"],
        "unreachable": ["confirmed"],
        "rescheduled": ["confirmed", "unreachable"],
        "cancelled": ["pending", "confirmed", "unreachable"],
    }
    query: dict[str, Any] = {
        "appointment_code": appointment_code,
        "status": {"$in": allowed_previous_statuses.get(status, [])},
    }
    if status == "confirmed":
        query["confirmed_by"] = None

    return await get_db().consultation_appointments.find_one_and_update(
        query,
        {"$set": fields},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0, "booking_key": 0},
    )


async def list_notifications(
    unread_only: bool = False,
    limit: int = 100,
) -> list[dict[str, Any]]:
    query = {"is_read": False} if unread_only else {}
    cursor = (
        get_db()
        .notifications.find(query, {"_id": 0})
        .sort("created_at", DESCENDING)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def mark_notification_read(appointment_code: str) -> bool:
    result = await get_db().notifications.update_many(
        {"appointment_code": appointment_code},
        {"$set": {"is_read": True, "read_at": _now()}},
    )
    return result.modified_count > 0


async def get_management_overview() -> dict[str, Any]:
    db = get_db()
    appointment_pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    appointment_rows = await db.consultation_appointments.aggregate(
        appointment_pipeline
    ).to_list(length=None)
    appointment_by_status = {
        row["_id"]: row["count"] for row in appointment_rows
    }
    return {
        "appointments_total": sum(appointment_by_status.values()),
        "appointments_pending": appointment_by_status.get("pending", 0),
        "appointments_confirmed": appointment_by_status.get("confirmed", 0),
        "appointments_completed": appointment_by_status.get("completed", 0),
        "leads_total": await db.managed_leads.count_documents({}),
        "leads_new": await db.managed_leads.count_documents({"status": "new"}),
        "conversations_total": await db.sessions.count_documents({}),
        "messages_total": await db.messages.count_documents({}),
        "notifications_unread": await db.notifications.count_documents(
            {"is_read": False}
        ),
        "staff_active": await db.staff_users.count_documents(
            {"status": "active"}
        ),
    }


async def list_conversations(limit: int = 100) -> list[dict[str, Any]]:
    pipeline = [
        {"$sort": {"last_active": -1}},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "messages",
                "let": {"sid": "$session_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {"$eq": ["$session_id", "$$sid"]}
                        }
                    },
                    {"$sort": {"created_at": -1}},
                    {"$limit": 1},
                    {"$project": {"_id": 0, "role": 1, "content": 1}},
                ],
                "as": "latest",
            }
        },
        {
            "$project": {
                "_id": 0,
                "session_id": 1,
                "message_count": 1,
                "last_intent": 1,
                "created_at": 1,
                "last_active": 1,
                "booking_step": 1,
                "latest_message": {"$arrayElemAt": ["$latest", 0]},
            }
        },
    ]
    return await get_db().sessions.aggregate(pipeline).to_list(length=limit)


async def list_managed_leads(
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    query = {"status": status} if status else {}
    cursor = (
        get_db()
        .managed_leads.find(query, {"_id": 0})
        .sort("created_at", DESCENDING)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def create_managed_lead(data: dict[str, Any]) -> dict[str, Any]:
    now = _now()
    document = {
        **data,
        "status": data.get("status", "new"),
        "created_at": now,
        "updated_at": now,
    }
    await get_db().managed_leads.insert_one(document)
    return {key: value for key, value in document.items() if key != "_id"}


async def update_managed_lead(
    lead_code: str,
    fields: dict[str, Any],
) -> dict[str, Any] | None:
    fields = {
        key: value
        for key, value in fields.items()
        if value is not None
    }
    fields["updated_at"] = _now()
    return await get_db().managed_leads.find_one_and_update(
        {"lead_code": lead_code},
        {"$set": fields},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )


async def list_staff_users(limit: int = 100) -> list[dict[str, Any]]:
    cursor = (
        get_db()
        .staff_users.find({}, {"_id": 0, "password_hash": 0})
        .sort("created_at", DESCENDING)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def create_staff_user(data: dict[str, Any]) -> dict[str, Any]:
    now = _now()
    document = {
        **data,
        "status": data.get("status", "active"),
        "created_at": now,
        "updated_at": now,
    }
    await get_db().staff_users.insert_one(document)
    return {
        key: value
        for key, value in document.items()
        if key not in {"_id", "password_hash"}
    }


async def get_staff_user_by_email(email: str) -> dict[str, Any] | None:
    return await get_db().staff_users.find_one(
        {"email": email.strip().lower()},
        {"_id": 0},
    )


async def record_staff_login(email: str) -> None:
    now = _now()
    await get_db().staff_users.update_one(
        {"email": email.strip().lower()},
        {"$set": {"last_login_at": now, "updated_at": now}},
    )


async def update_staff_password(email: str, password_hash: str) -> bool:
    result = await get_db().staff_users.update_one(
        {"email": email.strip().lower(), "status": "active"},
        {"$set": {"password_hash": password_hash, "updated_at": _now()}},
    )
    return result.modified_count == 1


async def _create_initial_admin() -> None:
    """Create the first admin from environment variables when no staff exists."""
    email = os.getenv("INITIAL_ADMIN_EMAIL", "").strip().lower()
    password_hash = os.getenv("INITIAL_ADMIN_PASSWORD_HASH", "").strip()
    full_name = os.getenv("INITIAL_ADMIN_NAME", "Quản trị viên").strip()
    if not email or not password_hash:
        return
    if await get_db().staff_users.count_documents({"email": email}) > 0:
        return
    await create_staff_user(
        {"full_name": full_name, "email": email, "role": "admin", "password_hash": password_hash}
    )


async def update_staff_user(
    email: str,
    fields: dict[str, Any],
) -> dict[str, Any] | None:
    fields = {
        key: value
        for key, value in fields.items()
        if value is not None
    }
    fields["updated_at"] = _now()
    return await get_db().staff_users.find_one_and_update(
        {"email": email},
        {"$set": fields},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0, "password_hash": 0},
    )
