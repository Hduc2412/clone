"""Đề xuất của trợ lý: hiện bằng nhãn người đọc được, và xác nhận tỉnh thì kèm vùng.

Hai điểm bắt trên trình duyệt thật ngày 06/10, phiên `3db5442f-…`:

1. Câu xác nhận hiện "Loại hình: vien_duong_lao" — mã danh mục, không phải chữ.
2. Bấm "Đúng, lưu lại" cho "Tỉnh mong muốn: Tokyo" xong, hồ sơ không có vùng.
   Vùng Kantō chỉ xuất hiện khi khách tình cờ gửi lại biểu mẫu.
"""
import unittest
from unittest.mock import AsyncMock, patch

from app.agent import contract
from app.api import agent as api_agent
from app.db import candidate_profiles as profiles

PHIEN = "3db5442f-f6d1-41ee-8928-cf4392392d00"


def ho_so() -> dict:
    return {
        "code": "UV-TEST01",
        "session_id": PHIEN,
        "status": "extracted",
        "version": 1,
        "fields": {"japanese_level": {"value": "N4", "source": "cv"}},
        "preferences": {},
    }


class NhanGiaTriTests(unittest.TestCase):
    def test_ma_danh_muc_co_nhan(self):
        d = contract.DeXuatGhi(field="desired_employer_type", value="vien_duong_lao", muc="preferences")
        self.assertEqual(d.as_dict()["value_label"], "Viện dưỡng lão")

    def test_gia_tri_khong_phai_ma_thi_khong_bia_nhan(self):
        d = contract.DeXuatGhi(field="experience_years", value=2, muc="fields")
        self.assertIsNone(d.as_dict()["value_label"])

    def test_ma_la_khong_co_trong_bang_thi_khong_bia_nhan(self):
        self.assertIsNone(contract.nhan_gia_tri("desired_employer_type", "khong_co"))


class XacNhanTinhKemVungTests(unittest.IsolatedAsyncioTestCase):
    async def _xac_nhan(self, field, value, hs=None):
        da_ghi: dict = {}

        async def _ap(session_id, **kw):
            da_ghi.update(kw)
            return {**(hs or ho_so()), "version": 2}

        with patch.object(
            profiles, "get_by_session", AsyncMock(return_value=hs or ho_so())
        ), patch.object(profiles, "apply_changes", _ap):
            await api_agent.xac_nhan_de_xuat(PHIEN, api_agent.XacNhanBody(field=field, value=value))
        return da_ghi

    async def test_xac_nhan_tinh_thi_ghi_luon_vung(self):
        ghi = await self._xac_nhan("desired_prefecture", "Tokyo")
        uu = ghi["preferences"]
        self.assertEqual(uu["desired_prefecture"]["value"], "Tokyo")
        self.assertEqual(uu["desired_region_group"]["value"], "kanto")
        self.assertEqual(uu["desired_region_group"]["source"], "user_confirmed")

    async def test_doi_tinh_thi_vung_cu_khong_o_lai(self):
        hs = ho_so()
        hs["preferences"] = {
            "desired_prefecture": {"value": "Tokyo", "source": "user_confirmed"},
            "desired_region_group": {"value": "kanto", "source": "user_confirmed"},
        }
        ghi = await self._xac_nhan("desired_prefecture", "Osaka", hs=hs)
        self.assertEqual(ghi["preferences"]["desired_region_group"]["value"], "kansai")

    async def test_truong_khac_khong_dung_toi_vung(self):
        ghi = await self._xac_nhan("desired_employer_type", "vien_duong_lao")
        self.assertNotIn("desired_region_group", ghi["preferences"])


if __name__ == "__main__":
    unittest.main()
