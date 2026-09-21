"""Kiểm thử hệ khách hàng: đăng nhập, đổi mật khẩu, và ranh giới dữ liệu.

Trọng tâm không phải "đăng nhập có chạy không" mà là **hai hệ thống không lẫn
vào nhau**: token của ứng viên không mở được cửa quản trị, token của nhân viên
không mở được cửa khách hàng, và một ứng viên không đọc được hồ sơ của người
khác dù có đổi mã trên thanh địa chỉ.
"""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, Request, Response

from app.api import candidate_auth, portal
from app.api.candidate_auth import ChangePasswordRequest, LoginRequest
from app.auth import candidate_security
from app.auth.security import create_access_token, decode_access_token, hash_password
from app.db import candidate_accounts as accounts


def http_request() -> Request:
    return Request({"type": "http", "headers": [], "client": ("127.0.0.1", 12345)})


STAFF = {"email": "tu.van@example.com", "full_name": "Tư vấn", "role": "consultant"}

PHONE = "0912345678"


def account_doc(**overrides) -> dict:
    document = {
        "phone": PHONE,
        "lead_code": "LD-0001",
        "full_name": "Nguyễn Thị Lan",
        "password_hash": hash_password("MatKhau@2026"),
        "must_change_password": False,
        "status": accounts.STATUS_ACTIVE,
    }
    document.update(overrides)
    return document


class TokenSeparationTests(unittest.TestCase):
    """Hai loại token phải từ chối nhau. Đây là ranh giới giữa hai hệ thống."""

    def test_a_candidate_token_is_refused_at_the_staff_door(self):
        token = candidate_security.create_candidate_token(account_doc())
        with self.assertRaises(HTTPException) as caught:
            decode_access_token(token)
        self.assertEqual(caught.exception.status_code, 401)

    def test_a_staff_token_is_refused_at_the_candidate_door(self):
        token = create_access_token(
            {"email": "admin@example.com", "full_name": "Quản trị", "role": "admin"}
        )
        with self.assertRaises(HTTPException) as caught:
            candidate_security.decode_candidate_token(token)
        self.assertEqual(caught.exception.status_code, 401)

    def test_a_candidate_token_carries_the_lead_it_is_locked_to(self):
        payload = candidate_security.decode_candidate_token(
            candidate_security.create_candidate_token(account_doc())
        )
        self.assertEqual(payload["sub"], PHONE)
        self.assertEqual(payload["lead"], "LD-0001")

    def test_a_tampered_token_is_refused(self):
        token = candidate_security.create_candidate_token(account_doc())
        header, body, signature = token.split(".")
        forged = f"{header}.{body}.{'A' * len(signature)}"
        with self.assertRaises(HTTPException):
            candidate_security.decode_candidate_token(forged)


class LoginTests(unittest.IsolatedAsyncioTestCase):
    async def test_login_succeeds_and_sets_a_cookie(self):
        with patch.object(
            accounts, "get_account_by_phone", new=AsyncMock(return_value=account_doc())
        ), patch.object(accounts, "record_login", new=AsyncMock()):
            response = Response()
            result = await candidate_auth.login(
                LoginRequest(phone="0912 345 678", password="MatKhau@2026"),
                response,
                http_request(),
            )
        self.assertEqual(result["phone"], PHONE)
        self.assertIn("xkld_candidate_session", response.headers.get("set-cookie", ""))

    async def test_the_password_hash_never_reaches_the_candidate(self):
        with patch.object(
            accounts, "get_account_by_phone", new=AsyncMock(return_value=account_doc())
        ), patch.object(accounts, "record_login", new=AsyncMock()):
            result = await candidate_auth.login(
                LoginRequest(phone=PHONE, password="MatKhau@2026"),
                Response(),
                http_request(),
            )
        self.assertNotIn("password_hash", result)

    async def test_a_wrong_password_and_an_unknown_number_give_the_same_answer(self):
        """Tách hai câu trả lời ra là biến trang đăng nhập thành công cụ dò số."""
        with patch.object(
            accounts, "get_account_by_phone", new=AsyncMock(return_value=account_doc())
        ):
            with self.assertRaises(HTTPException) as wrong_password:
                await candidate_auth.login(
                    LoginRequest(phone=PHONE, password="sai-mat-khau"),
                    Response(),
                    http_request(),
                )
        with patch.object(accounts, "get_account_by_phone", new=AsyncMock(return_value=None)):
            with self.assertRaises(HTTPException) as unknown_number:
                await candidate_auth.login(
                    LoginRequest(phone="0900000000", password="MatKhau@2026"),
                    Response(),
                    http_request(),
                )
        self.assertEqual(wrong_password.exception.detail, unknown_number.exception.detail)
        self.assertEqual(wrong_password.exception.status_code, 401)

    async def test_a_disabled_account_cannot_log_in(self):
        with patch.object(
            accounts,
            "get_account_by_phone",
            new=AsyncMock(return_value=account_doc(status=accounts.STATUS_DISABLED)),
        ):
            with self.assertRaises(HTTPException) as caught:
                await candidate_auth.login(
                    LoginRequest(phone=PHONE, password="MatKhau@2026"),
                    Response(),
                    http_request(),
                )
        self.assertEqual(caught.exception.status_code, 401)

    async def test_the_same_number_written_three_ways_reaches_one_account(self):
        for written in ("0912345678", "0912 345 678", "+84912345678"):
            self.assertEqual(LoginRequest(phone=written, password="x").phone, PHONE)


class PasswordChangeTests(unittest.IsolatedAsyncioTestCase):
    async def test_an_account_on_the_staff_issued_password_cannot_browse(self):
        """Mật khẩu nhân viên đọc qua điện thoại thì ít nhất hai người biết."""
        with self.assertRaises(HTTPException) as caught:
            await candidate_security.require_usable_password(
                account_doc(must_change_password=True)
            )
        self.assertEqual(caught.exception.status_code, 409)

    async def test_changing_the_password_clears_the_forced_change(self):
        stored = account_doc(must_change_password=True)
        updated = account_doc(must_change_password=False)
        with patch.object(
            accounts, "get_account_by_phone", new=AsyncMock(return_value=stored)
        ), patch.object(accounts, "set_password", new=AsyncMock(return_value=updated)) as write:
            result = await candidate_auth.change_password(
                ChangePasswordRequest(
                    current_password="MatKhau@2026", new_password="MatKhauMoi@2026"
                ),
                Response(),
                http_request(),
                account=stored,
            )
        self.assertFalse(result["must_change_password"])
        self.assertEqual(write.await_args.args[1], "MatKhauMoi@2026")

    async def test_a_wrong_current_password_is_refused(self):
        stored = account_doc()
        with patch.object(accounts, "get_account_by_phone", new=AsyncMock(return_value=stored)):
            with self.assertRaises(HTTPException) as caught:
                await candidate_auth.change_password(
                    ChangePasswordRequest(
                        current_password="doan-bua", new_password="MatKhauMoi@2026"
                    ),
                    Response(),
                    http_request(),
                    account=stored,
                )
        self.assertEqual(caught.exception.status_code, 401)

    async def test_reusing_the_same_password_is_refused(self):
        stored = account_doc()
        with patch.object(accounts, "get_account_by_phone", new=AsyncMock(return_value=stored)):
            with self.assertRaises(HTTPException) as caught:
                await candidate_auth.change_password(
                    ChangePasswordRequest(
                        current_password="MatKhau@2026", new_password="MatKhau@2026"
                    ),
                    Response(),
                    http_request(),
                    account=stored,
                )
        self.assertEqual(caught.exception.status_code, 400)

    def test_a_password_of_one_repeated_character_is_refused(self):
        with self.assertRaises(ValueError):
            ChangePasswordRequest(current_password="cu", new_password="aaaaaaaa")


class DataBoundaryTests(unittest.IsolatedAsyncioTestCase):
    """Ứng viên chỉ được thấy hồ sơ của chính mình, kể cả khi đoán đúng mã."""

    async def test_the_query_is_locked_to_the_lead_in_the_token(self):
        listed = AsyncMock(return_value=[])
        with patch.object(portal, "list_recruitment_applications", new=listed):
            await portal.my_applications(account_doc())
        self.assertEqual(listed.await_args.kwargs["lead_code"], "LD-0001")

    async def test_someone_elses_application_code_gives_404(self):
        mine = [{"application_code": "HS-CUA-TOI", "lead_code": "LD-0001"}]
        with patch.object(
            portal, "list_recruitment_applications", new=AsyncMock(return_value=mine)
        ):
            with self.assertRaises(HTTPException) as caught:
                await portal.my_application_detail("HS-CUA-NGUOI-KHAC", account_doc())
        self.assertEqual(caught.exception.status_code, 404)

    async def test_my_own_application_is_returned(self):
        mine = [{"application_code": "HS-CUA-TOI", "status": "screening", "lead_code": "LD-0001"}]
        with patch.object(
            portal, "list_recruitment_applications", new=AsyncMock(return_value=mine)
        ):
            result = await portal.my_application_detail("HS-CUA-TOI", account_doc())
        self.assertEqual(result["application_code"], "HS-CUA-TOI")
        self.assertEqual(result["status"], "screening")

    async def test_internal_columns_never_reach_the_candidate(self):
        """Danh sách cho phép, không phải danh sách loại trừ."""
        raw = [
            {
                "application_code": "HS-1",
                "status": "screening",
                "lead_code": "LD-0001",
                "assigned_to": "tu.van@example.com",
                "note": "ghi chú nội bộ",
                "match_score": 75,
            }
        ]
        with patch.object(
            portal, "list_recruitment_applications", new=AsyncMock(return_value=raw)
        ):
            result = await portal.my_applications(account_doc())
        item = result["items"][0]
        for hidden in ("assigned_to", "note", "match_score", "lead_code"):
            self.assertNotIn(hidden, item)

    async def test_an_account_without_a_lead_sees_nothing_rather_than_everything(self):
        """Thiếu mã khách mà vẫn gọi truy vấn thì rơi vào nhánh không lọc."""
        listed = AsyncMock(return_value=[{"application_code": "HS-NGUOI-KHAC"}])
        with patch.object(portal, "list_recruitment_applications", new=listed):
            result = await portal.my_applications(account_doc(lead_code=None))
        self.assertEqual(result["items"], [])
        listed.assert_not_awaited()


class InitialPasswordTests(unittest.TestCase):
    def test_the_generated_password_avoids_characters_that_sound_alike(self):
        """Mật khẩu này được đọc qua điện thoại, không phải chép từ màn hình."""
        for _ in range(50):
            password = accounts.generate_initial_password()
            self.assertEqual(len(password), accounts.INITIAL_PASSWORD_LENGTH)
            for confusing in "01OIl":
                self.assertNotIn(confusing, password)

    def test_two_accounts_never_get_the_same_password(self):
        generated = {accounts.generate_initial_password() for _ in range(200)}
        self.assertEqual(len(generated), 200)


if __name__ == "__main__":
    unittest.main()
