import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.conversation.fallback_messages import ALL_FALLBACKS, RATE_LIMITED
from app.services.analytics_service import (
    get_fallback_rate,
    get_overview,
    get_recent_leads,
    get_today_stats,
)


class AnalyticsLeadSchemaTests(unittest.IsolatedAsyncioTestCase):
    async def test_overview_and_today_use_managed_leads(self):
        db = MagicMock()
        db.sessions.count_documents = AsyncMock(side_effect=[12, 3])
        db.messages.count_documents = AsyncMock(side_effect=[48, 7])
        db.managed_leads.count_documents = AsyncMock(side_effect=[5, 2])

        with patch("app.services.analytics_service.get_db", return_value=db):
            overview = await get_overview()
            today = await get_today_stats()

        self.assertEqual(overview["total_leads"], 5)
        self.assertEqual(today["leads_today"], 2)
        self.assertEqual(db.managed_leads.count_documents.await_count, 2)

    async def test_recent_leads_returns_new_schema_fields(self):
        expected = [{
            "lead_code": "LD-ABC123",
            "customer_name": "Nguyễn Văn Nam",
            "phone": "0912345678",
            "source": "manual",
            "status": "new",
            "assigned_to": None,
            "note": None,
            "created_at": datetime.now(UTC),
        }]
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.to_list = AsyncMock(return_value=expected)
        db = MagicMock()
        db.managed_leads.find.return_value = cursor

        with patch("app.services.analytics_service.get_db", return_value=db):
            result = await get_recent_leads(limit=10)

        self.assertEqual(result, expected)
        projection = db.managed_leads.find.call_args.args[1]
        self.assertIn("lead_code", projection)
        self.assertIn("customer_name", projection)
        self.assertNotIn("session_id", projection)
        self.assertNotIn("name", projection)


class FallbackRateTests(unittest.IsolatedAsyncioTestCase):
    """Đếm fallback theo cờ, không dò chuỗi trong nội dung tin nhắn."""

    async def test_counts_every_kind_of_fallback(self):
        db = MagicMock()
        db.messages.count_documents = AsyncMock(side_effect=[100, 25])

        with patch("app.services.analytics_service.get_db", return_value=db):
            result = await get_fallback_rate()

        self.assertEqual(result["fallback_count"], 25)
        self.assertEqual(result["fallback_rate_percent"], 25.0)

        query = db.messages.count_documents.await_args_list[1].args[0]
        self.assertEqual(query["role"], "assistant")
        # nhánh 1: tin nhắn mới đã có cờ
        self.assertIn({"is_fallback": True}, query["$or"])
        # nhánh 2: tin nhắn cũ chưa có cờ thì đối chiếu theo nội dung
        legacy = query["$or"][1]
        self.assertEqual(legacy["is_fallback"], {"$exists": False})
        self.assertIn(RATE_LIMITED, legacy["content"]["$in"])
        self.assertEqual(len(legacy["content"]["$in"]), len(ALL_FALLBACKS))

    async def test_zero_messages_does_not_divide_by_zero(self):
        db = MagicMock()
        db.messages.count_documents = AsyncMock(side_effect=[0, 0])

        with patch("app.services.analytics_service.get_db", return_value=db):
            result = await get_fallback_rate()

        self.assertEqual(result["fallback_rate_percent"], 0)


if __name__ == "__main__":
    unittest.main()
