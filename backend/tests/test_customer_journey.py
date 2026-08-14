import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.api.customer_journey import customer_journey
from app.services.customer_journey_service import _phone_candidates


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


if __name__ == "__main__":
    unittest.main()
