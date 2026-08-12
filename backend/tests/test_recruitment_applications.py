import os
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("JWT_SECRET", "test-secret-that-is-long-enough-for-application-tests")

from fastapi import HTTPException, Request
from pymongo.errors import DuplicateKeyError

from app.api.applications import (
    ApplicationCreateRequest,
    ApplicationUpdateRequest,
    applications,
    create_application,
    update_application,
)


def http_request() -> Request:
    return Request({"type": "http", "headers": [], "client": ("127.0.0.1", 12345)})


class RecruitmentApplicationTests(unittest.IsolatedAsyncioTestCase):
    consultant = {
        "email": "consultant@example.com",
        "full_name": "Tư vấn viên",
        "role": "consultant",
    }
    manager = {
        "email": "manager@example.com",
        "full_name": "Quản lý",
        "role": "manager",
    }

    async def test_consultant_list_is_forced_to_their_email(self):
        with patch(
            "app.api.applications.list_recruitment_applications",
            new=AsyncMock(return_value=[]),
        ) as listing:
            result = await applications(
                assigned_to="other@example.com",
                current_user=self.consultant,
            )
        self.assertEqual(result, [])
        self.assertEqual(listing.await_args.kwargs["assigned_to"], self.consultant["email"])

    async def test_consultant_cannot_update_unassigned_application(self):
        existing = {
            "application_code": "HS-001",
            "assigned_to": "other@example.com",
            "status": "draft",
        }
        with patch(
            "app.api.applications.get_recruitment_application",
            new=AsyncMock(return_value=existing),
        ):
            with self.assertRaises(HTTPException) as raised:
                await update_application(
                    "HS-001",
                    ApplicationUpdateRequest(status="screening"),
                    http_request(),
                    self.consultant,
                )
        self.assertEqual(raised.exception.status_code, 403)

    async def test_create_uses_lead_identity_and_records_history(self):
        lead = {
            "lead_code": "LD-001",
            "customer_name": "Nguyễn Văn Nam",
            "phone": "0912345678",
            "assigned_to": "consultant@example.com",
        }
        created = {
            "application_code": "HS-001",
            "lead_code": "LD-001",
            "customer_name": lead["customer_name"],
            "phone": lead["phone"],
            "status": "draft",
            "is_active": True,
        }
        with (
            patch("app.api.applications.secrets.token_hex", return_value="001"),
            patch("app.api.applications.get_managed_lead", new=AsyncMock(return_value=lead)),
            patch(
                "app.api.applications.get_staff_user_by_email",
                new=AsyncMock(return_value={"status": "active"}),
            ),
            patch(
                "app.api.applications.create_recruitment_application",
                new=AsyncMock(return_value=created),
            ) as creating,
            patch("app.api.applications.create_application_event", new=AsyncMock()) as event,
            patch("app.api.applications.audit_action", new=AsyncMock()) as audit,
        ):
            result = await create_application(
                ApplicationCreateRequest(lead_code="LD-001"),
                http_request(),
                self.manager,
            )
        document = creating.await_args.args[0]
        self.assertEqual(document["customer_name"], lead["customer_name"])
        self.assertEqual(document["phone"], lead["phone"])
        self.assertEqual(document["assigned_to"], lead["assigned_to"])
        self.assertTrue(document["is_active"])
        self.assertEqual(result, created)
        event.assert_awaited_once()
        audit.assert_awaited_once()

    async def test_duplicate_active_application_returns_conflict(self):
        lead = {
            "lead_code": "LD-001",
            "customer_name": "Nguyễn Văn Nam",
            "phone": "0912345678",
            "assigned_to": None,
        }
        with (
            patch("app.api.applications.get_managed_lead", new=AsyncMock(return_value=lead)),
            patch(
                "app.api.applications.create_recruitment_application",
                new=AsyncMock(side_effect=DuplicateKeyError("duplicate")),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await create_application(
                    ApplicationCreateRequest(lead_code="LD-001"),
                    http_request(),
                    self.manager,
                )
        self.assertEqual(raised.exception.status_code, 409)

    async def test_closing_application_sets_inactive(self):
        existing = {
            "application_code": "HS-001",
            "assigned_to": self.consultant["email"],
            "status": "visa_processing",
        }
        updated = {**existing, "status": "withdrawn", "is_active": False}
        with (
            patch(
                "app.api.applications.get_recruitment_application",
                new=AsyncMock(return_value=existing),
            ),
            patch(
                "app.api.applications.update_recruitment_application",
                new=AsyncMock(return_value=updated),
            ) as updating,
            patch("app.api.applications.create_application_event", new=AsyncMock()),
            patch("app.api.applications.audit_action", new=AsyncMock()),
        ):
            result = await update_application(
                "HS-001",
                ApplicationUpdateRequest(status="withdrawn"),
                http_request(),
                self.consultant,
            )
        self.assertFalse(updating.await_args.args[1]["is_active"])
        self.assertEqual(result, updated)


if __name__ == "__main__":
    unittest.main()
