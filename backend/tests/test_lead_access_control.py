"""Quyền truy cập khách hàng: nhân viên tư vấn chỉ thao tác trên khách được giao."""
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("JWT_SECRET", "test-secret-that-is-long-enough-for-lead-access-tests")

from fastapi import HTTPException

from app.api.management import (
    LeadCreateRequest,
    LeadUpdateRequest,
    create_lead,
    leads,
    update_lead,
)


CONSULTANT = {"email": "an@cty.com", "full_name": "An", "role": "consultant"}
MANAGER = {"email": "quanly@cty.com", "full_name": "Quản lý", "role": "manager"}


class LeadListScopeTests(unittest.IsolatedAsyncioTestCase):
    async def test_consultant_only_sees_their_own_leads(self):
        with patch(
            "app.api.management.list_managed_leads", new=AsyncMock(return_value=[])
        ) as listing:
            await leads(assigned_to="nguoikhac@cty.com", current_user=CONSULTANT)

        self.assertEqual(listing.await_args.kwargs["assigned_to"], CONSULTANT["email"])

    async def test_manager_can_list_everyone(self):
        # assigned_to=None mô phỏng đúng thứ FastAPI truyền vào khi client
        # không gửi tham số; gọi hàm trực tiếp sẽ nhận nguyên đối tượng Query.
        with patch(
            "app.api.management.list_managed_leads", new=AsyncMock(return_value=[])
        ) as listing:
            await leads(assigned_to=None, current_user=MANAGER)

        self.assertIsNone(listing.await_args.kwargs["assigned_to"])

    async def test_manager_can_filter_by_any_employee(self):
        with patch(
            "app.api.management.list_managed_leads", new=AsyncMock(return_value=[])
        ) as listing:
            await leads(assigned_to="an@cty.com", current_user=MANAGER)

        self.assertEqual(listing.await_args.kwargs["assigned_to"], "an@cty.com")


class LeadUpdateAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_consultant_cannot_update_lead_of_someone_else(self):
        existing = {"lead_code": "LD-001", "assigned_to": "nguoikhac@cty.com"}
        with (
            patch(
                "app.api.management.get_managed_lead",
                new=AsyncMock(return_value=existing),
            ),
            patch("app.api.management.update_managed_lead", new=AsyncMock()) as updating,
        ):
            with self.assertRaises(HTTPException) as raised:
                await update_lead(
                    "LD-001",
                    LeadUpdateRequest(status="contacted"),
                    MagicMock(),
                    CONSULTANT,
                )

        self.assertEqual(raised.exception.status_code, 403)
        updating.assert_not_awaited()

    async def test_consultant_can_update_their_own_lead(self):
        existing = {"lead_code": "LD-001", "assigned_to": CONSULTANT["email"]}
        with (
            patch(
                "app.api.management.get_managed_lead",
                new=AsyncMock(return_value=existing),
            ),
            patch(
                "app.api.management.update_managed_lead",
                new=AsyncMock(return_value={"lead_code": "LD-001"}),
            ) as updating,
            patch("app.api.management.audit_action", new=AsyncMock()),
        ):
            await update_lead(
                "LD-001",
                LeadUpdateRequest(status="contacted"),
                MagicMock(),
                CONSULTANT,
            )

        updating.assert_awaited_once()

    async def test_consultant_cannot_reassign_lead(self):
        existing = {"lead_code": "LD-001", "assigned_to": CONSULTANT["email"]}
        with (
            patch(
                "app.api.management.get_managed_lead",
                new=AsyncMock(return_value=existing),
            ),
            patch("app.api.management.update_managed_lead", new=AsyncMock()) as updating,
        ):
            with self.assertRaises(HTTPException) as raised:
                await update_lead(
                    "LD-001",
                    LeadUpdateRequest(assigned_to="nguoikhac@cty.com"),
                    MagicMock(),
                    CONSULTANT,
                )

        self.assertEqual(raised.exception.status_code, 403)
        updating.assert_not_awaited()

    async def test_missing_lead_returns_404(self):
        with patch(
            "app.api.management.get_managed_lead", new=AsyncMock(return_value=None)
        ):
            with self.assertRaises(HTTPException) as raised:
                await update_lead(
                    "LD-KHONG-CO",
                    LeadUpdateRequest(status="contacted"),
                    MagicMock(),
                    MANAGER,
                )

        self.assertEqual(raised.exception.status_code, 404)


class LeadAssigneeValidationTests(unittest.IsolatedAsyncioTestCase):
    """Không được giao khách cho một email không tồn tại hoặc tài khoản đã khóa."""

    async def test_update_rejects_unknown_assignee(self):
        existing = {"lead_code": "LD-001", "assigned_to": None}
        with (
            patch(
                "app.api.management.get_managed_lead",
                new=AsyncMock(return_value=existing),
            ),
            patch(
                "app.services.assignment.get_staff_user_by_email",
                new=AsyncMock(return_value=None),
            ),
            patch("app.api.management.update_managed_lead", new=AsyncMock()) as updating,
        ):
            with self.assertRaises(HTTPException) as raised:
                await update_lead(
                    "LD-001",
                    LeadUpdateRequest(assigned_to="khong-ton-tai@abc.com"),
                    MagicMock(),
                    MANAGER,
                )

        self.assertEqual(raised.exception.status_code, 400)
        updating.assert_not_awaited()

    async def test_update_rejects_deactivated_assignee(self):
        existing = {"lead_code": "LD-001", "assigned_to": None}
        with (
            patch(
                "app.api.management.get_managed_lead",
                new=AsyncMock(return_value=existing),
            ),
            patch(
                "app.services.assignment.get_staff_user_by_email",
                new=AsyncMock(return_value={"status": "disabled"}),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await update_lead(
                    "LD-001",
                    LeadUpdateRequest(assigned_to="da-nghi@cty.com"),
                    MagicMock(),
                    MANAGER,
                )

        self.assertEqual(raised.exception.status_code, 400)

    async def test_create_rejects_unknown_assignee(self):
        with (
            patch(
                "app.services.assignment.get_staff_user_by_email",
                new=AsyncMock(return_value=None),
            ),
            patch("app.api.management.create_managed_lead", new=AsyncMock()) as creating,
        ):
            with self.assertRaises(HTTPException) as raised:
                await create_lead(
                    LeadCreateRequest(
                        customer_name="Nguyễn Thị Lan",
                        phone="0912345678",
                        assigned_to="khong-ton-tai@abc.com",
                    ),
                    MagicMock(),
                    MANAGER,
                )

        self.assertEqual(raised.exception.status_code, 400)
        creating.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
