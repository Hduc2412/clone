"""Phiên đăng nhập của tài khoản đã xóa không được mở tài khoản mới cùng email.

Bắt trên trình duyệt ngày 06/10: xóa ba tài khoản nhân viên tạm, tạo lại cùng
email — cookie cũ trong trình duyệt vào thẳng tài khoản mới, `/auth/me` trả 200.
Token khi ấy chỉ mang email. Nếu email của một nhân viên đã nghỉ được cấp lại cho
người khác, người cũ còn giữ cookie là vào được tài khoản của người mới.
"""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.auth import security
from app.core.config import settings

TAO_LUC = datetime(2026, 10, 6, 9, 38, 44, 388000)  # đúng hình MongoDB trả: UTC, không múi


def nhan_vien(**them):
    return {
        "email": "a@local.test", "full_name": "A", "role": "consultant",
        "status": "active", "created_at": TAO_LUC, **them,
    }


class PhienTaiKhoanCuTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        goc = settings.jwt_secret
        settings.jwt_secret = "khoa-thu-du-dai-cho-kiem-thu-phien-tai-khoan"
        self.addCleanup(setattr, settings, "jwt_secret", goc)

    async def _xac_thuc(self, token, tai_khoan_trong_db):
        with patch.object(
            security, "get_staff_user_by_email", AsyncMock(return_value=tai_khoan_trong_db)
        ):
            return await security.get_user_pending_password(token=token)

    async def test_cung_ban_ghi_thi_vao_duoc(self):
        token = security.create_access_token(nhan_vien())
        ra = await self._xac_thuc(token, nhan_vien())
        self.assertEqual(ra["email"], "a@local.test")

    async def test_tai_khoan_tao_lai_cung_email_thi_token_cu_chet(self):
        """Đúng thao tác ngày 06/10: xóa rồi tạo lại, email y nguyên."""
        token_cu = security.create_access_token(nhan_vien())
        tao_lai = nhan_vien(created_at=TAO_LUC + timedelta(minutes=40))
        with self.assertRaises(HTTPException) as ctx:
            await self._xac_thuc(token_cu, tao_lai)
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_lech_mot_mili_giay_cung_la_tai_khoan_khac(self):
        token_cu = security.create_access_token(nhan_vien())
        with self.assertRaises(HTTPException):
            await self._xac_thuc(token_cu, nhan_vien(created_at=TAO_LUC + timedelta(milliseconds=1)))

    async def test_token_cap_truoc_ban_sua_khong_mang_dau_thi_phai_dang_nhap_lai(self):
        token = security.create_access_token(nhan_vien())
        # Dựng lại đúng hình token cũ: không có khóa `acc`.
        with patch.object(security, "dau_tai_khoan", lambda _u: None):
            token_cu = security.create_access_token(nhan_vien())
        self.assertNotEqual(token, token_cu)
        with self.assertRaises(HTTPException) as ctx:
            await self._xac_thuc(token_cu, nhan_vien())
        self.assertEqual(ctx.exception.status_code, 401)


class DauTaiKhoanTests(unittest.TestCase):
    def test_gio_khong_mui_hieu_la_utc(self):
        co_mui = TAO_LUC.replace(tzinfo=timezone.utc)
        self.assertEqual(
            security.dau_tai_khoan({"created_at": TAO_LUC}),
            security.dau_tai_khoan({"created_at": co_mui}),
        )

    def test_micro_giay_trong_bo_nho_khop_mili_giay_trong_db(self):
        """Lúc tạo, bản trong bộ nhớ có micro giây; bản đọc lại từ MongoDB thì không."""
        trong_bo_nho = TAO_LUC.replace(microsecond=388999)
        self.assertEqual(
            security.dau_tai_khoan({"created_at": trong_bo_nho}),
            security.dau_tai_khoan({"created_at": TAO_LUC}),
        )

    def test_khong_co_ngay_tao_thi_khong_bia_dau(self):
        self.assertIsNone(security.dau_tai_khoan({}))


if __name__ == "__main__":
    unittest.main()
