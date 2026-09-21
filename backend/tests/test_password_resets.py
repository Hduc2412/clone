"""Kiểm thử luồng quên mật khẩu, cho cả ứng viên và nhân viên.

Ba điều quan trọng hơn "gửi yêu cầu có chạy không":

- **Không dò được số nào đã đăng ký.** Gửi cho số có thật và số bịa phải nhận
  cùng một câu trả lời.
- **Tư vấn viên không đặt lại được mật khẩu cho đồng nghiệp.** Đó là việc của
  quản trị viên; cho phép là mở đường mượn tài khoản nhau.
- **Đặt lại xong thì bắt buộc đổi.** Mật khẩu mặc định là dãy ai cũng biết, nên
  thiếu cờ này là để ngỏ tài khoản.
"""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, Request

from app.api import password_resets as api
from app.api.password_resets import CandidateResetRequest, StaffResetRequest
from app.auth import security
from app.db import candidate_accounts as accounts
from app.db import password_resets as store


def http_request() -> Request:
    return Request({"type": "http", "headers": [], "client": ("127.0.0.1", 12345)})


ADMIN = {"email": "admin@example.com", "full_name": "Quản trị", "role": "admin"}
MANAGER = {"email": "manager@example.com", "full_name": "Quản lý", "role": "manager"}
CONSULTANT = {"email": "tu.van@example.com", "full_name": "Tư vấn", "role": "consultant"}

PHONE = "0912345678"


def pending(**overrides) -> dict:
    document = {
        "code": "YC-A1B2C3",
        "subject_type": store.SUBJECT_CANDIDATE,
        "subject_id": PHONE,
        "full_name": "Nguyễn Thị Lan",
        "status": store.STATUS_PENDING,
    }
    document.update(overrides)
    return document


class RequestPrivacyTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_real_number_and_a_made_up_one_get_the_same_answer(self):
        with patch.object(
            accounts, "get_account_by_phone", new=AsyncMock(return_value={"full_name": "A"})
        ), patch.object(store, "create_request", new=AsyncMock(return_value=pending())):
            real = await api.request_candidate_reset(
                CandidateResetRequest(phone=PHONE), http_request()
            )
        with patch.object(accounts, "get_account_by_phone", new=AsyncMock(return_value=None)):
            fake = await api.request_candidate_reset(
                CandidateResetRequest(phone="0900000000"), http_request()
            )
        self.assertEqual(real, fake)

    async def test_no_row_is_written_for_a_number_without_an_account(self):
        """Không có tài khoản thì không ghi gì — hàng đợi không đầy yêu cầu bịa."""
        writer = AsyncMock()
        with patch.object(
            accounts, "get_account_by_phone", new=AsyncMock(return_value=None)
        ), patch.object(store, "create_request", new=writer):
            await api.request_candidate_reset(
                CandidateResetRequest(phone="0900000000"), http_request()
            )
        writer.assert_not_awaited()

    async def test_a_staff_request_is_written_under_the_staff_type(self):
        writer = AsyncMock(return_value=pending(subject_type=store.SUBJECT_STAFF))
        with patch.object(
            api, "get_staff_user_by_email", new=AsyncMock(return_value={"full_name": "Tư vấn"})
        ), patch.object(store, "create_request", new=writer):
            await api.request_staff_reset(
                StaffResetRequest(email="Tu.Van@Example.com"), http_request()
            )
        self.assertEqual(writer.await_args.kwargs["subject_type"], store.SUBJECT_STAFF)
        self.assertEqual(writer.await_args.kwargs["subject_id"], "tu.van@example.com")

    def test_the_same_number_written_three_ways_is_one_subject(self):
        for written in ("0912345678", "0912 345 678", "+84912345678"):
            self.assertEqual(CandidateResetRequest(phone=written).phone, PHONE)


class VisibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_consultant_only_sees_candidate_requests(self):
        listed = AsyncMock(return_value=[])
        with patch.object(store, "list_requests", new=listed):
            await api.list_pending(current_user=CONSULTANT)
        self.assertEqual(
            listed.await_args.kwargs["subject_types"], (store.SUBJECT_CANDIDATE,)
        )

    async def test_a_manager_also_sees_staff_requests(self):
        listed = AsyncMock(return_value=[])
        with patch.object(store, "list_requests", new=listed):
            await api.list_pending(current_user=MANAGER)
        self.assertIn(store.SUBJECT_STAFF, listed.await_args.kwargs["subject_types"])


class HandlingTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_consultant_cannot_reset_a_colleague(self):
        staff_request = pending(subject_type=store.SUBJECT_STAFF, subject_id=MANAGER["email"])
        with patch.object(store, "get_request", new=AsyncMock(return_value=staff_request)):
            with self.assertRaises(HTTPException) as caught:
                await api.handle_reset("YC-A1B2C3", http_request(), current_user=CONSULTANT)
        self.assertEqual(caught.exception.status_code, 403)

    async def test_a_consultant_can_reset_a_candidate(self):
        with patch.object(
            store, "get_request", new=AsyncMock(return_value=pending())
        ), patch.object(
            accounts, "reset_password", new=AsyncMock(return_value={"phone": PHONE})
        ), patch.object(
            store, "mark_done", new=AsyncMock(return_value=pending(status=store.STATUS_DONE))
        ), patch.object(api, "audit_action", new=AsyncMock()):
            result = await api.handle_reset(
                "YC-A1B2C3", http_request(), current_user=CONSULTANT
            )
        self.assertEqual(result["subject_type"], store.SUBJECT_CANDIDATE)
        self.assertEqual(result["default_password"], "12345678")

    async def test_resetting_a_staff_account_forces_a_change(self):
        staff_request = pending(subject_type=store.SUBJECT_STAFF, subject_id=CONSULTANT["email"])
        flag = AsyncMock(return_value=True)
        with patch.object(
            store, "get_request", new=AsyncMock(return_value=staff_request)
        ), patch.object(
            api, "update_staff_password", new=AsyncMock(return_value=True)
        ), patch.object(api, "set_staff_password_flag", new=flag), patch.object(
            store, "mark_done", new=AsyncMock(return_value=staff_request)
        ), patch.object(api, "audit_action", new=AsyncMock()):
            await api.handle_reset("YC-A1B2C3", http_request(), current_user=ADMIN)
        self.assertEqual(flag.await_args.args, (CONSULTANT["email"], True))

    async def test_resetting_a_candidate_forces_a_change(self):
        """`reset_password` ở tầng dữ liệu luôn bật lại cờ bắt buộc đổi."""
        writer = AsyncMock(return_value={"phone": PHONE})
        with patch.object(
            store, "get_request", new=AsyncMock(return_value=pending())
        ), patch.object(accounts, "reset_password", new=writer), patch.object(
            store, "mark_done", new=AsyncMock(return_value=pending())
        ), patch.object(api, "audit_action", new=AsyncMock()):
            await api.handle_reset("YC-A1B2C3", http_request(), current_user=CONSULTANT)
        self.assertEqual(writer.await_args.args[1], "12345678")

    async def test_an_already_handled_request_is_refused(self):
        with patch.object(
            store,
            "get_request",
            new=AsyncMock(return_value=pending(status=store.STATUS_DONE)),
        ):
            with self.assertRaises(HTTPException) as caught:
                await api.handle_reset("YC-A1B2C3", http_request(), current_user=ADMIN)
        self.assertEqual(caught.exception.status_code, 409)

    async def test_two_people_handling_at_once_lose_the_race_loudly(self):
        with patch.object(
            store, "get_request", new=AsyncMock(return_value=pending())
        ), patch.object(
            accounts, "reset_password", new=AsyncMock(return_value={"phone": PHONE})
        ), patch.object(store, "mark_done", new=AsyncMock(return_value=None)):
            with self.assertRaises(HTTPException) as caught:
                await api.handle_reset("YC-A1B2C3", http_request(), current_user=ADMIN)
        self.assertEqual(caught.exception.status_code, 409)

    async def test_an_unknown_request_gives_404(self):
        with patch.object(store, "get_request", new=AsyncMock(return_value=None)):
            with self.assertRaises(HTTPException) as caught:
                await api.handle_reset("YC-KHONG-CO", http_request(), current_user=ADMIN)
        self.assertEqual(caught.exception.status_code, 404)


class StaffForcedChangeTests(unittest.IsolatedAsyncioTestCase):
    """Nhân viên còn nợ đổi mật khẩu thì bị chặn ở mọi cửa, trừ ba cửa thoát."""

    async def test_a_staff_owing_a_password_change_is_blocked(self):
        with self.assertRaises(HTTPException) as caught:
            await security.get_current_user(
                user={**CONSULTANT, "must_change_password": True}
            )
        self.assertEqual(caught.exception.status_code, 409)

    async def test_a_staff_with_their_own_password_passes(self):
        user = await security.get_current_user(user={**CONSULTANT, "must_change_password": False})
        self.assertEqual(user["email"], CONSULTANT["email"])

    async def test_an_account_without_the_field_is_not_blocked(self):
        """Tài khoản tạo trước khi có cờ này không được tự nhiên bị khóa."""
        user = await security.get_current_user(user=dict(CONSULTANT))
        self.assertEqual(user["email"], CONSULTANT["email"])


if __name__ == "__main__":
    unittest.main()
