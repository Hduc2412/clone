"""
MongoDB persistence layer for chat sessions, messages, leads, and analytics.
"""
from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from app.core.config import settings


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
        _client = AsyncIOMotorClient(settings.mongodb_uri)
        _db = _client[settings.mongodb_db_name]

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
        [("assigned_to", ASCENDING), ("appointment_date", ASCENDING)],
    )
    await db.consultation_appointments.create_index(
        "booking_key",
        unique=True,
    )
    await db.notifications.create_index(
        [("is_read", ASCENDING), ("created_at", DESCENDING)],
    )
    await db.appointment_events.create_index(
        [("appointment_code", ASCENDING), ("created_at", ASCENDING)],
    )
    await db.managed_leads.create_index("lead_code", unique=True)
    await db.managed_leads.create_index("phone")
    await db.managed_leads.create_index(
        [("status", ASCENDING), ("created_at", DESCENDING)]
    )
    await db.staff_users.create_index("email", unique=True)
    await db.staff_users.create_index("status")
    await db.audit_logs.create_index([("created_at", DESCENDING)])
    await db.audit_logs.create_index([("actor_email", ASCENDING), ("created_at", DESCENDING)])
    await db.audit_logs.create_index([("action", ASCENDING), ("created_at", DESCENDING)])
    await db.recruitment_applications.create_index("application_code", unique=True)
    await db.recruitment_applications.create_index(
        [("lead_code", ASCENDING), ("created_at", DESCENDING)]
    )
    await db.recruitment_applications.create_index(
        [("assigned_to", ASCENDING), ("status", ASCENDING), ("updated_at", DESCENDING)]
    )
    await db.recruitment_applications.create_index(
        "lead_code",
        unique=True,
        name="unique_active_application_per_lead",
        partialFilterExpression={"is_active": True},
    )
    await db.application_events.create_index(
        [("application_code", ASCENDING), ("created_at", ASCENDING)]
    )

    await _create_initial_admin()

    print("[DB] MongoDB initialized successfully.")


SENSITIVE_AUDIT_KEYS = {
    "password",
    "password_hash",
    "current_password",
    "new_password",
    "token",
    "authorization",
    "cookie",
}


def _sanitize_audit_details(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key.lower() in SENSITIVE_AUDIT_KEYS else _sanitize_audit_details(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_audit_details(item) for item in value]
    return value


async def record_audit_log(
    action: str,
    outcome: str,
    actor_email: str | None = None,
    actor_name: str | None = None,
    actor_role: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    ip_address: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    await get_db().audit_logs.insert_one(
        {
            "action": action,
            "outcome": outcome,
            "actor_email": actor_email,
            "actor_name": actor_name,
            "actor_role": actor_role,
            "target_type": target_type,
            "target_id": target_id,
            "ip_address": ip_address,
            "details": _sanitize_audit_details(details or {}),
            "created_at": _now(),
        }
    )


async def list_audit_logs(
    actor_email: str | None = None,
    action: str | None = None,
    outcome: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if actor_email:
        query["actor_email"] = actor_email.strip().lower()
    if action:
        query["action"] = action
    if outcome:
        query["outcome"] = outcome
    if date_from or date_to:
        query["created_at"] = {}
        if date_from:
            query["created_at"]["$gte"] = date_from
        if date_to:
            query["created_at"]["$lte"] = date_to
    cursor = get_db().audit_logs.find(query, {"_id": 0}).sort("created_at", DESCENDING).limit(limit)
    return await cursor.to_list(length=limit)


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
        "assigned_to": None,
        "assigned_name": None,
        "assigned_by": None,
        "assigned_at": None,
        "created_at": now,
        "updated_at": now,
    }
    await get_db().consultation_appointments.insert_one(document)
    await _record_appointment_event(
        appointment_code=document["appointment_code"],
        action="created",
        actor_name="Chatbot",
        actor_email=None,
        new_status="pending",
    )
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
    date_from: str | None = None,
    date_to: str | None = None,
    assigned_to: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if status:
        query["status"] = status
    if assigned_to:
        query["assigned_to"] = assigned_to.strip().lower()
    if date_from or date_to:
        query["appointment_date"] = {}
        if date_from:
            query["appointment_date"]["$gte"] = date_from
        if date_to:
            query["appointment_date"]["$lte"] = date_to
    cursor = (
        get_db()
        .consultation_appointments.find(query, {"_id": 0, "booking_key": 0})
        .sort([("appointment_date", ASCENDING), ("appointment_time", ASCENDING)])
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def get_appointment_by_code(appointment_code: str) -> dict[str, Any] | None:
    return await get_db().consultation_appointments.find_one(
        {"appointment_code": appointment_code},
        {"_id": 0, "booking_key": 0},
    )


async def get_appointment_stats(
    date_from: str | None = None,
    date_to: str | None = None,
    assigned_to: str | None = None,
) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if assigned_to:
        query["assigned_to"] = assigned_to.strip().lower()
    if date_from or date_to:
        query["appointment_date"] = {}
        if date_from:
            query["appointment_date"]["$gte"] = date_from
        if date_to:
            query["appointment_date"]["$lte"] = date_to

    db = get_db()
    rows = await db.consultation_appointments.aggregate(
        [
            {"$match": query},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
    ).to_list(length=None)
    by_status = {row["_id"]: row["count"] for row in rows}
    total = sum(by_status.values())
    confirmed_total = await db.consultation_appointments.count_documents(
        {**query, "confirmed_at": {"$ne": None}}
    )

    def rate(value: int) -> float:
        return round(value * 100 / total, 1) if total else 0.0

    completed = by_status.get("completed", 0)
    unreachable = by_status.get("unreachable", 0)
    cancelled = by_status.get("cancelled", 0)
    return {
        "total": total,
        "pending": by_status.get("pending", 0),
        "confirmed": by_status.get("confirmed", 0),
        "completed": completed,
        "unreachable": unreachable,
        "cancelled": cancelled,
        "confirmation_rate": rate(confirmed_total),
        "completion_rate": rate(completed),
        "unreachable_rate": rate(unreachable),
        "cancellation_rate": rate(cancelled),
    }


async def update_appointment_status(
    appointment_code: str,
    status: str,
    actor: dict[str, Any],
    result_note: str | None = None,
    required_assigned_to: str | None = None,
) -> dict[str, Any] | None:
    now = _now()
    employee_name = actor["full_name"]
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
        "cancelled": ["pending", "confirmed", "unreachable"],
    }
    query: dict[str, Any] = {
        "appointment_code": appointment_code,
        "status": {"$in": allowed_previous_statuses.get(status, [])},
    }
    if required_assigned_to:
        query["assigned_to"] = required_assigned_to
    if status == "confirmed":
        query["confirmed_by"] = None

    previous = await get_db().consultation_appointments.find_one_and_update(
        query,
        {"$set": fields},
        return_document=ReturnDocument.BEFORE,
        projection={"_id": 0, "booking_key": 0},
    )
    if previous is None:
        return None

    await _record_appointment_event(
        appointment_code=appointment_code,
        action="status_changed",
        actor_name=employee_name,
        actor_email=actor["email"],
        old_status=previous.get("status"),
        new_status=status,
        note=result_note,
    )
    return await get_db().consultation_appointments.find_one(
        {"appointment_code": appointment_code},
        {"_id": 0, "booking_key": 0},
    )


async def assign_appointment(
    appointment_code: str,
    assignee: dict[str, Any],
    actor: dict[str, Any],
) -> dict[str, Any] | None:
    now = _now()
    previous = await get_db().consultation_appointments.find_one_and_update(
        {
            "appointment_code": appointment_code,
            "status": {"$nin": ["completed", "cancelled"]},
        },
        {
            "$set": {
                "assigned_to": assignee["email"],
                "assigned_name": assignee["full_name"],
                "assigned_by": actor["email"],
                "assigned_at": now,
                "updated_at": now,
                "updated_by": actor["full_name"],
            }
        },
        return_document=ReturnDocument.BEFORE,
        projection={"_id": 0, "booking_key": 0},
    )
    if previous is None:
        return None

    await _record_appointment_event(
        appointment_code=appointment_code,
        action="assigned",
        actor_name=actor["full_name"],
        actor_email=actor["email"],
        old_status=previous.get("status"),
        new_status=previous.get("status"),
        details={
            "previous_assigned_to": previous.get("assigned_to"),
            "assigned_to": assignee["email"],
            "assigned_name": assignee["full_name"],
        },
    )
    return await get_db().consultation_appointments.find_one(
        {"appointment_code": appointment_code},
        {"_id": 0, "booking_key": 0},
    )


async def find_appointment_conflict(
    appointment_code: str,
    appointment_date: str,
    appointment_time: str,
) -> dict[str, Any] | None:
    db = get_db()
    appointment = await db.consultation_appointments.find_one(
        {"appointment_code": appointment_code},
        {"_id": 0},
    )
    if appointment is None:
        return None

    conflict_conditions: list[dict[str, Any]] = [{"phone": appointment["phone"]}]
    if appointment.get("assigned_to"):
        conflict_conditions.append({"assigned_to": appointment["assigned_to"]})
    return await db.consultation_appointments.find_one(
        {
            "appointment_code": {"$ne": appointment_code},
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
            "status": {"$nin": ["completed", "cancelled"]},
            "$or": conflict_conditions,
        },
        {"_id": 0, "booking_key": 0},
    )


async def reschedule_appointment(
    appointment_code: str,
    appointment_date: str,
    appointment_time: str,
    actor: dict[str, Any],
    note: str | None = None,
    required_assigned_to: str | None = None,
) -> dict[str, Any] | None:
    now = _now()
    ownership_query: dict[str, Any] = {"appointment_code": appointment_code}
    if required_assigned_to:
        ownership_query["assigned_to"] = required_assigned_to
    current = await get_db().consultation_appointments.find_one(
        ownership_query,
        {"phone": 1},
    )
    if current is None:
        return None
    update_query: dict[str, Any] = {
        "appointment_code": appointment_code,
        "status": {"$nin": ["completed", "cancelled"]},
    }
    if required_assigned_to:
        update_query["assigned_to"] = required_assigned_to
    previous = await get_db().consultation_appointments.find_one_and_update(
        update_query,
        {
            "$set": {
                "appointment_date": appointment_date,
                "appointment_time": appointment_time,
                "booking_key": f"{current['phone']}|{appointment_date}|{appointment_time}",
                "status": "confirmed",
                "updated_at": now,
                "updated_by": actor["full_name"],
            }
        },
        return_document=ReturnDocument.BEFORE,
        projection={"_id": 0},
    )
    if previous is None:
        return None

    await _record_appointment_event(
        appointment_code=appointment_code,
        action="rescheduled",
        actor_name=actor["full_name"],
        actor_email=actor["email"],
        old_status=previous.get("status"),
        new_status="confirmed",
        note=note,
        details={
            "previous_date": previous.get("appointment_date"),
            "previous_time": previous.get("appointment_time"),
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
        },
    )
    return await get_db().consultation_appointments.find_one(
        {"appointment_code": appointment_code},
        {"_id": 0, "booking_key": 0},
    )


async def _record_appointment_event(
    appointment_code: str,
    action: str,
    actor_name: str,
    actor_email: str | None,
    old_status: str | None = None,
    new_status: str | None = None,
    note: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    await get_db().appointment_events.insert_one(
        {
            "appointment_code": appointment_code,
            "action": action,
            "actor_name": actor_name,
            "actor_email": actor_email,
            "old_status": old_status,
            "new_status": new_status,
            "note": note,
            "details": details or {},
            "created_at": _now(),
        }
    )


async def list_appointment_events(
    appointment_code: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    cursor = (
        get_db()
        .appointment_events.find(
            {"appointment_code": appointment_code},
            {"_id": 0},
        )
        .sort("created_at", ASCENDING)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def list_notifications(
    unread_only: bool = False,
    assigned_to: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    query = {"is_read": False} if unread_only else {}
    if assigned_to:
        appointments = await get_db().consultation_appointments.find(
            {"assigned_to": assigned_to},
            {"appointment_code": 1},
        ).to_list(length=None)
        query["appointment_code"] = {
            "$in": [row["appointment_code"] for row in appointments]
        }
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


async def get_managed_lead(lead_code: str) -> dict[str, Any] | None:
    return await get_db().managed_leads.find_one(
        {"lead_code": lead_code},
        {"_id": 0},
    )


async def list_recruitment_applications(
    status: str | None = None,
    lead_code: str | None = None,
    assigned_to: str | None = None,
    active_only: bool = False,
    limit: int = 100,
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if status:
        query["status"] = status
    if lead_code:
        query["lead_code"] = lead_code
    if assigned_to:
        query["assigned_to"] = assigned_to.strip().lower()
    if active_only:
        query["is_active"] = True
    cursor = (
        get_db()
        .recruitment_applications.find(query, {"_id": 0})
        .sort("updated_at", DESCENDING)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def get_recruitment_application(application_code: str) -> dict[str, Any] | None:
    return await get_db().recruitment_applications.find_one(
        {"application_code": application_code},
        {"_id": 0},
    )


async def create_recruitment_application(data: dict[str, Any]) -> dict[str, Any]:
    now = _now()
    document = {
        **data,
        "created_at": now,
        "updated_at": now,
    }
    await get_db().recruitment_applications.insert_one(document)
    return {key: value for key, value in document.items() if key != "_id"}


async def update_recruitment_application(
    application_code: str,
    fields: dict[str, Any],
) -> dict[str, Any] | None:
    clean_fields = {key: value for key, value in fields.items() if value is not None}
    clean_fields["updated_at"] = _now()
    return await get_db().recruitment_applications.find_one_and_update(
        {"application_code": application_code},
        {"$set": clean_fields},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )


async def create_application_event(data: dict[str, Any]) -> None:
    await get_db().application_events.insert_one({**data, "created_at": _now()})


async def list_application_events(
    application_code: str,
    limit: int = 200,
) -> list[dict[str, Any]]:
    cursor = (
        get_db()
        .application_events.find({"application_code": application_code}, {"_id": 0})
        .sort("created_at", ASCENDING)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


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
    email = settings.initial_admin_email
    password_hash = settings.initial_admin_password_hash
    full_name = settings.initial_admin_name
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
