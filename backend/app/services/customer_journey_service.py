import re
from typing import Any

from app.db.database import get_db


def _phone_candidates(phone: str) -> list[str]:
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("84"):
        local = f"0{digits[2:]}"
    else:
        local = digits
    international = f"84{local[1:]}" if local.startswith("0") else local
    return list({phone, digits, local, international, f"+{international}"})


async def get_customer_journey(
    lead: dict[str, Any],
    appointment_owner: str | None = None,
) -> dict[str, Any]:
    """Combine business and chatbot records without coupling their modules."""
    db = get_db()
    phone_query = {"$in": _phone_candidates(lead["phone"])}
    applications = await (
        db.recruitment_applications.find(
            {"lead_code": lead["lead_code"]}, {"_id": 0}
        ).sort("updated_at", -1).to_list(length=100)
    )
    appointment_query: dict[str, Any] = {"phone": phone_query}
    if appointment_owner:
        appointment_query["assigned_to"] = appointment_owner.strip().lower()
    appointments = await (
        db.consultation_appointments.find(
            appointment_query, {"_id": 0, "booking_key": 0}
        ).sort([("appointment_date", -1), ("appointment_time", -1)]).to_list(length=100)
    )
    chatbot_leads = await db.leads.find(
        {"phone": phone_query}, {"_id": 0, "session_id": 1}
    ).to_list(length=100)
    session_ids = list({row["session_id"] for row in chatbot_leads if row.get("session_id")})
    conversations: list[dict[str, Any]] = []
    if session_ids:
        conversations = await db.sessions.aggregate([
            {"$match": {"session_id": {"$in": session_ids}}},
            {"$sort": {"last_active": -1}},
            {"$lookup": {
                "from": "messages",
                "let": {"sid": "$session_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$session_id", "$$sid"]}}},
                    {"$sort": {"created_at": 1}},
                    {"$project": {"_id": 0}},
                ],
                "as": "messages",
            }},
            {"$project": {"_id": 0, "booking_data": 0}},
        ]).to_list(length=100)
    application_codes = [row["application_code"] for row in applications]
    appointment_codes = [row["appointment_code"] for row in appointments]
    application_events = (
        await db.application_events.find(
            {"application_code": {"$in": application_codes}}, {"_id": 0}
        ).sort("created_at", -1).to_list(length=500)
        if application_codes else []
    )
    appointment_events = (
        await db.appointment_events.find(
            {"appointment_code": {"$in": appointment_codes}}, {"_id": 0}
        ).sort("created_at", -1).to_list(length=500)
        if appointment_codes else []
    )
    return {
        "lead": lead,
        "applications": applications,
        "appointments": appointments,
        "conversations": conversations,
        "events": {"applications": application_events, "appointments": appointment_events},
    }
