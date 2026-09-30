"""Kiểm thử hệ khách hàng: đăng nhập, đổi mật khẩu, và ranh giới dữ liệu.

Trọng tâm không phải "đăng nhập có chạy không" mà là **hai hệ thống không lẫn
vào nhau**: token của ứng viên không mở được cửa quản trị, token của nhân viên
không mở được cửa khách hàng, và một ứng viên không đọc được hồ sơ của người
khác dù có đổi mã trên thanh địa chỉ.
"""
import asyncio
import time
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, Request, Response

from app.api import candidate_auth, portal
from app.api.candidate_auth import ChangePasswordRequest, LoginRequest
from app.auth import candidate_security
from app.auth.security import create_access_token, decode_access_token, hash_password
from app.core.config import settings
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


class DefaultPasswordExpiryTests(unittest.IsolatedAsyncioTestCase):
    """Dãy mặc định có hạn dùng, vì cờ bắt đổi không xác minh được người đăng nhập.

    Ai biết số điện thoại cũng gõ đúng `12345678`. Trong suốt quãng tài khoản
    còn nằm ở dãy đó, người vào trước mới là người đặt mật khẩu mới — kể cả khi
    đó không phải chủ tài khoản. Hạn dùng không làm dãy ấy an toàn, nó chỉ cắt
    khung giờ lợi dụng từ vô hạn xuống một con số đếm được.
    """

    async def _dang_nhap(self, account: dict):
        with patch.object(
            accounts, "get_account_by_phone", new=AsyncMock(return_value=account)
        ), patch.object(accounts, "record_login", new=AsyncMock()):
            return await candidate_auth.login(
                LoginRequest(phone=PHONE, password="12345678"),
                Response(),
                http_request(),
            )

    def _tai_khoan_moi_cap(self, gio_truoc: float) -> dict:
        return account_doc(
            password_hash=hash_password("12345678"),
            must_change_password=True,
            password_changed_at=int(time.time() - gio_truoc * 3600),
        )

    async def test_day_mac_dinh_con_han_thi_dang_nhap_duoc(self):
        result = await self._dang_nhap(self._tai_khoan_moi_cap(1))
        self.assertTrue(result["must_change_password"])

    async def test_day_mac_dinh_qua_han_thi_bi_tu_choi(self):
        with self.assertRaises(HTTPException) as caught:
            await self._dang_nhap(self._tai_khoan_moi_cap(settings.default_password_hours + 1))
        self.assertEqual(caught.exception.status_code, 401)
        self.assertIn("hết hạn", caught.exception.detail)

    async def test_nguoi_da_tu_dat_mat_khau_rieng_khong_bi_han_nay(self):
        """Dấu thời gian khi ấy nói về mật khẩu của riêng họ, không phải dãy mặc định."""
        account = account_doc(
            password_hash=hash_password("12345678"),
            must_change_password=False,
            password_changed_at=int(time.time() - 3600 * 24 * 365),
        )
        result = await self._dang_nhap(account)
        self.assertFalse(result["must_change_password"])

    async def test_tai_khoan_cu_chua_co_dau_thoi_gian_thi_khong_chan(self):
        account = self._tai_khoan_moi_cap(1)
        account.pop("password_changed_at")
        result = await self._dang_nhap(account)
        self.assertTrue(result["must_change_password"])


class StaleSessionTests(unittest.IsolatedAsyncioTestCase):
    """Đổi mật khẩu phải **đuổi được** phiên đang mở, không chỉ chặn lần sau.

    Kịch bản thật: ai đó biết số điện thoại, đăng nhập trước bằng dãy mặc định
    rồi im lặng. Chủ tài khoản gọi nhân viên đặt lại rồi tự đổi mật khẩu — nhưng
    token của người kia còn hạn thì họ vẫn đọc tiếp toàn bộ hồ sơ. Khi ấy việc
    đổi mật khẩu chỉ là cảm giác an toàn.
    """

    async def _mo_cua(self, account: dict, token: str):
        # Vá đúng tên đã import vào `candidate_security`, không phải tên gốc
        # trong `accounts` — module này import thẳng hàm, nên vá ở nguồn không
        # có tác dụng.
        with patch.object(
            candidate_security, "get_account_by_phone", new=AsyncMock(return_value=account)
        ):
            return await candidate_security.get_current_candidate(token=token)

    async def test_token_cap_truoc_khi_doi_mat_khau_bi_tu_choi(self):
        account = account_doc()
        token = candidate_security.create_candidate_token(account)
        # Mật khẩu đổi một phút sau khi token được cấp.
        account["password_changed_at"] = int(time.time()) + 60
        with self.assertRaises(HTTPException) as caught:
            await self._mo_cua(account, token)
        self.assertEqual(caught.exception.status_code, 401)

    async def test_token_cap_sau_khi_doi_mat_khau_van_dung_duoc(self):
        account = account_doc(password_changed_at=int(time.time()) - 60)
        token = candidate_security.create_candidate_token(account)
        result = await self._mo_cua(account, token)
        self.assertEqual(result["phone"], PHONE)

    async def test_tai_khoan_cu_chua_co_moc_thoi_gian_thi_khong_duoi_ai(self):
        """Bản ghi tạo trước khi có trường này: không có mốc thì không chặn."""
        account = account_doc()
        account.pop("password_changed_at", None)
        token = candidate_security.create_candidate_token(account)
        result = await self._mo_cua(account, token)
        self.assertEqual(result["phone"], PHONE)

    async def test_khong_bao_gio_tra_ve_bam_mat_khau(self):
        account = account_doc()
        token = candidate_security.create_candidate_token(account)
        result = await self._mo_cua(account, token)
        self.assertNotIn("password_hash", result)


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


class DefaultPasswordTests(unittest.TestCase):
    """Mật khẩu mặc định là dãy ai cũng biết, nên nó phải luôn đi kèm bắt buộc đổi."""

    def test_mat_khau_cap_la_ngau_nhien_moi_lan(self):
        """Không còn dãy dùng chung — đây là lỗ hổng bản rà soát 30/09 xếp P1.

        Một dãy ai cũng biết thì ai biết số điện thoại của một tài khoản vừa cấp
        cũng đăng nhập được, và nếu vào trước chủ tài khoản thì họ là người đặt mật
        khẩu mới. `must_change_password` không bịt được điều đó: nó bắt đổi mật
        khẩu, nhưng không xác minh người đang đổi là ai.
        """
        cac = {accounts.default_password() for _ in range(50)}
        self.assertEqual(len(cac), 50, "mật khẩu cấp bị lặp — không phải ngẫu nhiên")

    def test_mat_khau_cap_doc_duoc_qua_dien_thoai(self):
        """Dãy này được đọc qua điện thoại, và máy chủ không đọc lại được lần hai.

        Nên nó phải tránh ký tự nghe giống nhau: `0/O`, `1/l/I`, `5/S`, `2/Z`. Một
        ký tự nghe nhầm là ứng viên gõ sai ba lần rồi gọi lại, mà nhân viên không
        tra lại được vì bản rõ không được lưu.
        """
        mk = accounts.default_password()
        self.assertEqual(len(mk), accounts.DAI_MAT_KHAU_CAP)
        for ky_tu in "0O1lI5S2Z":
            self.assertNotIn(ky_tu, mk, f"ký tự {ky_tu!r} dễ nghe nhầm khi đọc")

    def test_khong_con_day_dung_chung_trong_cau_hinh(self):
        """Canh để không ai đưa nó về: một dòng trong `.env` là mở lại cả lỗ hổng."""
        self.assertFalse(
            hasattr(settings, "default_password"),
            "`default_password` đã bị bỏ — đừng khai lại một dãy dùng chung",
        )

    def test_a_new_account_always_owes_a_password_change(self):
        """Đây là thứ duy nhất bù lại việc mật khẩu ban đầu không phải bí mật."""
        with patch.object(accounts, "get_db") as fake_db:
            fake_db.return_value = {accounts.COLLECTION: AsyncMock()}
            created = asyncio.run(
                accounts.create_account(
                    phone=PHONE,
                    lead_code="LD-0001",
                    full_name="Nguyễn Thị Lan",
                    password=accounts.default_password(),
                    created_by="tu.van@example.com",
                )
            )
        self.assertTrue(created["must_change_password"])
        self.assertNotIn(accounts.default_password(), created["password_hash"])


if __name__ == "__main__":
    unittest.main()
