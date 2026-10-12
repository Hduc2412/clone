"""Số lịch chờ trên thanh bên đếm theo phạm vi người xem (12/10).

Kiểm trình duyệt 12/10: consultant thấy "Lịch hẹn 34" ở thanh bên, mở danh sách thì 0
lịch — thanh bên đọc số của cả hệ thống, danh sách chỉ hiện lịch giao cho chính họ.
"""
import unittest
from unittest.mock import AsyncMock, patch

from app.api import appointments as api


class DemLichChoTests(unittest.IsolatedAsyncioTestCase):
    async def _dem(self, user):
        dem = AsyncMock(return_value=3)
        with patch.object(api, "count_appointments", new=dem):
            ra = await api.get_pending_appointment_count(current_user=user)
        return ra, dem.await_args.kwargs

    async def test_consultant_chi_dem_lich_cua_minh(self):
        ra, kw = await self._dem({"email": "tv@local.test", "role": "consultant"})
        self.assertEqual(ra, {"count": 3})
        self.assertEqual(kw, {"status": "pending", "assigned_to": "tv@local.test"})

    async def test_quan_ly_dem_ca_he_thong(self):
        for vai_tro in ("manager", "admin"):
            _, kw = await self._dem({"email": "ql@local.test", "role": vai_tro})
            self.assertEqual(kw, {"status": "pending", "assigned_to": None})


class DemLichDbTests(unittest.IsolatedAsyncioTestCase):
    async def test_cung_luat_loc_nguoi_phu_trach_voi_danh_sach(self):
        from app.db import database
        bang = AsyncMock()
        bang.count_documents.return_value = 2
        with patch.object(database, "get_db", return_value=type("D", (), {"consultation_appointments": bang})()):
            self.assertEqual(await database.count_appointments(status="pending", assigned_to=" TV@Local.Test "), 2)
            await database.count_appointments(status="pending")
        self.assertEqual(bang.count_documents.await_args_list[0].args[0],
                         {"status": "pending", "assigned_to": "tv@local.test"})
        self.assertEqual(bang.count_documents.await_args_list[1].args[0], {"status": "pending"})


if __name__ == "__main__":
    unittest.main()
