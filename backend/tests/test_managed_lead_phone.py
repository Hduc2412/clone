import secrets
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError

from app.api.management import (
    LeadCreateRequest,
    LeadUpdateRequest,
    create_lead,
    update_lead,
)
from app.core.phone import normalize_vietnamese_phone
from app.db.database import (
    close_db,
    create_managed_lead,
    get_db,
    init_db,
    update_managed_lead,
)


class PhoneNormalizationTests(unittest.TestCase):
    def test_normalizes_common_local_and_international_formats(self):
        self.assertEqual(normalize_vietnamese_phone("0912 345 678"), "0912345678")
        self.assertEqual(normalize_vietnamese_phone("+84 912.345.678"), "0912345678")
        self.assertEqual(
            LeadCreateRequest(
                customer_name="Nguyễn Văn Nam",
                phone="+84 912 345 678",
            ).phone,
            "0912345678",
        )
        self.assertEqual(LeadUpdateRequest(phone="0912-345-678").phone, "0912345678")

    def test_rejects_invalid_phone(self):
        for value in ("", "12345", "+1 202 555 0100"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_vietnamese_phone(value)
        with self.assertRaises(ValidationError):
            LeadCreateRequest(customer_name="Nguyễn Văn Nam", phone="12345")


class ManagedLeadPhoneApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.actor = {
            "email": "manager@example.com",
            "full_name": "Manager",
            "role": "manager",
        }
        self.http_request = MagicMock()

    async def test_create_duplicate_returns_conflict(self):
        request = LeadCreateRequest(
            customer_name="Nguyễn Văn Nam", phone="0912345678"
        )
        with patch(
            "app.api.management.create_managed_lead",
            new=AsyncMock(side_effect=DuplicateKeyError("duplicate")),
        ):
            with self.assertRaises(HTTPException) as context:
                await create_lead(request, self.http_request, self.actor)
        self.assertEqual(context.exception.status_code, 409)

    async def test_update_duplicate_returns_conflict(self):
        request = LeadUpdateRequest(phone="+84 912 345 678")
        with patch(
            "app.api.management.update_managed_lead",
            new=AsyncMock(side_effect=DuplicateKeyError("duplicate")),
        ):
            with self.assertRaises(HTTPException) as context:
                await update_lead("LD-001", request, self.http_request, self.actor)
        self.assertEqual(context.exception.status_code, 409)


class ManagedLeadPhoneDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await init_db()
        suffix = secrets.token_hex(5).upper()
        number = int(suffix[:8], 16) % 100000000
        self.phone = f"09{number:08d}"
        self.first_code = f"LD-PHONE-A-{suffix}"
        self.second_code = f"LD-PHONE-B-{suffix}"

    async def asyncTearDown(self):
        await get_db().managed_leads.delete_many(
            {"lead_code": {"$in": [self.first_code, self.second_code]}}
        )
        await close_db()

    async def test_unique_index_blocks_equivalent_phone_formats(self):
        first = await create_managed_lead({
            "lead_code": self.first_code,
            "customer_name": "Khách A",
            "phone": self.phone,
            "source": "test",
        })
        self.assertEqual(first["phone"], self.phone)
        stored = await get_db().managed_leads.find_one(
            {"lead_code": self.first_code}
        )
        self.assertEqual(stored["phone_normalized"], self.phone)

        international = f"+84{self.phone[1:]}"
        with self.assertRaises(DuplicateKeyError):
            await create_managed_lead({
                "lead_code": self.second_code,
                "customer_name": "Khách B",
                "phone": international,
                "source": "test",
            })

    async def test_update_cannot_take_another_customers_phone(self):
        other_number = (int(self.phone) + 1) % 10_000_000_000
        other_phone = f"{other_number:010d}"
        if not other_phone.startswith("0"):
            other_phone = f"0{other_phone[1:]}"
        await create_managed_lead({
            "lead_code": self.first_code,
            "customer_name": "Khách A",
            "phone": self.phone,
            "source": "test",
        })
        await create_managed_lead({
            "lead_code": self.second_code,
            "customer_name": "Khách B",
            "phone": other_phone,
            "source": "test",
        })

        with self.assertRaises(DuplicateKeyError):
            await update_managed_lead(self.second_code, {"phone": self.phone})


if __name__ == "__main__":
    unittest.main()
