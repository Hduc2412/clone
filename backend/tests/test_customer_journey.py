import secrets
import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.api.customer_journey import customer_journey
from app.db.database import close_db, get_db, init_db
from app.services.customer_journey_service import _phone_candidates, get_customer_journey


class CustomerJourneyApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.lead = {
            "lead_code": "LD-001",
            "customer_name": "Nguyễn Văn Nam",
            "phone": "0912345678",
            "assigned_to": "owner@example.com",
        }
        self.consultant = {
            "email": "consultant@example.com",
            "role": "consultant",
        }

    async def test_consultant_cannot_view_customer_not_assigned_to_them(self):
        with (
            patch(
                "app.api.customer_journey.get_managed_lead",
                new=AsyncMock(return_value=self.lead),
            ),
            patch(
                "app.api.customer_journey.list_recruitment_applications",
                new=AsyncMock(return_value=[]),
            ),
        ):
            with self.assertRaises(HTTPException) as context:
                await customer_journey("LD-001", self.consultant)
        self.assertEqual(context.exception.status_code, 403)

    async def test_assigned_application_grants_access_and_filters_appointments(self):
        aggregate = AsyncMock(return_value={"lead": self.lead})
        with (
            patch(
                "app.api.customer_journey.get_managed_lead",
                new=AsyncMock(return_value=self.lead),
            ),
            patch(
                "app.api.customer_journey.list_recruitment_applications",
                new=AsyncMock(return_value=[{"application_code": "HS-001"}]),
            ),
            patch("app.api.customer_journey.get_customer_journey", new=aggregate),
        ):
            result = await customer_journey("LD-001", self.consultant)
        self.assertEqual(result, {"lead": self.lead})
        aggregate.assert_awaited_once_with(
            self.lead, appointment_owner="consultant@example.com"
        )

    async def test_manager_sees_complete_customer_journey(self):
        manager = {"email": "manager@example.com", "role": "manager"}
        aggregate = AsyncMock(return_value={"lead": self.lead})
        with (
            patch(
                "app.api.customer_journey.get_managed_lead",
                new=AsyncMock(return_value=self.lead),
            ),
            patch("app.api.customer_journey.get_customer_journey", new=aggregate),
        ):
            await customer_journey("LD-001", manager)
        aggregate.assert_awaited_once_with(self.lead)


class CustomerJourneyPhoneTests(unittest.TestCase):
    def test_phone_candidates_include_local_and_international_formats(self):
        candidates = _phone_candidates("+84 912 345 678")
        self.assertIn("0912345678", candidates)
        self.assertIn("84912345678", candidates)
        self.assertIn("+84912345678", candidates)


class CustomerJourneyDatabaseIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await init_db()
        suffix = secrets.token_hex(6)
        self.session_id = f"journey-session-{suffix}"
        self.lead_code = f"LD-JOURNEY-{suffix.upper()}"
        self.phone = f"09{int(suffix[:8], 16) % 100000000:08d}"
        self.now = datetime.now(UTC)
        db = get_db()
        await db.sessions.insert_one({
            "session_id": self.session_id,
            "booking_data": {"phone": self.phone},
            "message_count": 2,
            "last_active": self.now,
            "created_at": self.now,
        })
        await db.messages.insert_many([
            {
                "session_id": self.session_id,
                "role": "user",
                "content": "Tôi muốn đặt lịch tư vấn",
                "intent": "booking",
                "created_at": self.now,
            },
            {
                "session_id": self.session_id,
                "role": "assistant",
                "content": "Bạn vui lòng cung cấp thông tin.",
                "intent": "booking",
                "created_at": self.now,
            },
        ])

    async def asyncTearDown(self):
        db = get_db()
        await db.messages.delete_many({"session_id": self.session_id})
        await db.sessions.delete_many({"session_id": self.session_id})
        await db.recruitment_applications.delete_many({"lead_code": self.lead_code})
        await db.consultation_appointments.delete_many({"phone": self.phone})
        await close_db()

    async def test_service_finds_conversation_from_session_booking_phone(self):
        result = await get_customer_journey({
            "lead_code": self.lead_code,
            "customer_name": "Khách kiểm thử",
            "phone": self.phone,
        })

        self.assertEqual(len(result["conversations"]), 1)
        conversation = result["conversations"][0]
        self.assertEqual(conversation["session_id"], self.session_id)
        self.assertEqual(
            [message["role"] for message in conversation["messages"]],
            ["user", "assistant"],
        )


if __name__ == "__main__":
    unittest.main()
