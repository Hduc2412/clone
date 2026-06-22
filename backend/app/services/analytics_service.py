"""
Analytics Service 
Query MongoDB để tổng hợp số liệu hoạt động chatbot.
"""

from datetime import UTC, datetime, timedelta
from app.db.database import get_db

async def get_overview() -> dict:
    """Tổng quan: số sessions, messages, leads toàn thời gian."""
    db = get_db()
    total_sessions = await db.sessions.count_documents({})
    total_messages = await db.messages.count_documents({})
    total_leads = await db.leads.count_documents({})

    return {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "total_leads": total_leads,
    }

async def get_today_stats() -> dict:
    """Số sessions, messages, leads trong ngày hôm nay."""
    db = get_db()
    start_of_day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    sessions_today = await db.sessions.count_documents(
        {"created_at": {"$gte": start_of_day}}
    )
    messages_today = await db.messages.count_documents(
        {"created_at": {"$gte": start_of_day}}
    )
    leads_today = await db.leads.count_documents(
        {"created_at": {"$gte": start_of_day}}
    )

    return {
        "session_today": sessions_today,
        "messages_today": messages_today,
        "leads_today": leads_today,
    }

async def get_intent_distribution() -> dict:
    """Thống kê intent nào được hỏi nhiều nhất."""
    db = get_db()
    pipeline = [
        {"$match": {"role": "user"}},
        {"$group": {"_id": "$intent", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    cursor = db.messages.aggregate(pipeline)
    results = await cursor.to_list(length=None)
    return [{"intent": r["_id"], "count": r["count"]} for r in results]

async def get_fallback_rate() -> dict:
    """Tỷ lệ câu trả lời rơi vào fallback."""
    db = get_db()
    total_bot_messages = await db.messages.count_documents({"role": "assistant"})
    fallback_messages = await db.messages.count_documents({
        "role": "assistant",
        "content": {"$regex": "Xin lỗi, tôi không tìm thấy"}
    })
    rate = round(fallback_messages / total_bot_messages * 100, 1) if total_bot_messages else 0
    
    return {
        "total_bot_messages": total_bot_messages,
        "fallback_count": fallback_messages,
        "fallback_rate_percent": rate,
    }

async def get_recent_leads(limit: int = 20) -> list:
    """Danh sách leads gần nhất."""
    from pymongo import DESCENDING
    cursor = (
        get_db()
        .leads.find(
            {},
            {"_id": 0, "session_id": 1, "name": 1, "phone": 1, "created_at": 1}
        )
        .sort("created_at", DESCENDING)
        .limit(limit)
    )
    return await cursor.to_list(length=None)