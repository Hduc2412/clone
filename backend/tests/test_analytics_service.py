import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.analytics_service import get_overview, get_recent_leads, get_today_stats


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
