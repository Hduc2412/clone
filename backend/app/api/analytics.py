"""
Endpoints xem số liệu hoạt động chatbot.
"""
from fastapi import APIRouter
from app.services.analytics_service import (
    get_overview,
    get_today_stats,
    get_intent_distribution,
    get_fallback_rate,
    get_recent_leads,
)
router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/overview")
async def overview():
    """Tổng quan toàn thời gian: sessions, messages, leads."""
    return await get_overview()


@router.get("/today")
async def today():
    """Thống kê trong ngày hôm nay."""
    return await get_today_stats()


@router.get("/intents")
async def intents():
    """Intent nào được hỏi nhiều nhất."""
    return await get_intent_distribution()


@router.get("/fallbacks")
async def fallbacks():
    """Tỷ lệ câu trả lời rơi vào fallback."""
    return await get_fallback_rate()


@router.get("/leads")
async def leads(limit: int = 20):
    """Danh sách leads gần nhất."""
    return await get_recent_leads(limit=limit)