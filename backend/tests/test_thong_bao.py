"""Thông báo cho nhân viên: phạm vi, rút gọn tên, đếm, đánh dấu đã đọc (12/10).

Trước 12/10: không màn hình nào đọc `/notifications`, số trên nút "Thông báo" đếm mọi
thông báo của cả hệ thống (161 trên database thật) và chỉ tăng; API trả họ tên đầy đủ
của khách ở hồ sơ chưa ai nhận cho consultant; thông báo yêu cầu hỗ trợ không ai đánh
dấu đọc được (rơi vào nhánh lịch hẹn → 404).
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.db import database

TV = "tv@example.com"


def _cursor(rows):
    c = MagicMock()
    c.to_list = AsyncMock(return_value=rows)
    c.sort.return_value = c
    c.limit.return_value = c
    return c


def _db(thong_bao):
    db = MagicMock()
    db.consultation_appointments.find.return_value = _cursor([{"appointment_code": "LH-1"}])
    db.recruitment_applications.find.return_value = _cursor([
        {"application_code": "HS-MINH", "assigned_to": TV},
        {"application_code": "HS-CHUA", "assigned_to": None},
    ])
    db.support_requests.find.return_value = _cursor([{"code": "HT-CHUA", "assigned_to": None}])
    db.notifications.find.return_value = _cursor(thong_bao)
    db.notifications.count_documents = AsyncMock(return_value=3)
    db.notifications.update_many = AsyncMock(return_value=MagicMock(modified_count=2))
    return db


class PhamViTests(unittest.IsolatedAsyncioTestCase):
    async def test_viec_chua_cua_minh_chi_con_ten_viet_tat(self):
        tb = [
            {"reference_type": "application", "reference_code": "HS-CHUA",
             "detail": {"customer_name": "Trần Thị Thu Hà", "note": "nội bộ"}},
            {"reference_type": "application", "reference_code": "HS-MINH",
             "detail": {"customer_name": "Lê Văn An"}},
        ]
        with patch.object(database, "get_db", return_value=_db(tb)):
            ra = await database.list_notifications(assigned_to=TV)
        chua, minh = ra
        self.assertEqual(chua["detail"]["customer_name"], "T. T. T. H.")
        self.assertNotIn("note", chua["detail"])
        self.assertTrue(chua["ban_toi_thieu"])
        self.assertEqual(minh["detail"]["customer_name"], "Lê Văn An")
        self.assertNotIn("ban_toi_thieu", minh)

    async def test_quan_ly_thay_du_khong_rut_gon(self):
        tb = [{"reference_type": "application", "reference_code": "HS-CHUA", "detail": {"customer_name": "Trần Thị Thu Hà"}}]
        db = _db(tb)
        with patch.object(database, "get_db", return_value=db):
            ra = await database.list_notifications(assigned_to=None)
        self.assertEqual(ra[0]["detail"]["customer_name"], "Trần Thị Thu Hà")
        self.assertEqual(db.notifications.find.call_args.args[0], {})

    async def test_thong_bao_ban_giao_chi_cho_nguoi_nhan(self):
        # Trình duyệt 12/10: việc giao rồi trả về hàng đợi → "Bạn được giao…" hiện cho mọi consultant.
        db = _db([])
        with patch.object(database, "get_db", return_value=db):
            await database.list_notifications(assigned_to=TV)
        q = db.notifications.find.call_args.args[0]
        dieu_kien = q["$and"][0]["$or"]
        self.assertIn({"detail.assigned_to": TV}, dieu_kien)
        self.assertEqual(set(dieu_kien[0]["type"]["$nin"]), {"application_handover", "support_handover"})

    async def test_dem_va_danh_dau_het_dung_pham_vi(self):
        db = _db([])
        with patch.object(database, "get_db", return_value=db):
            self.assertEqual(await database.count_notifications(assigned_to=TV), 3)
            self.assertEqual(await database.mark_all_notifications_read(assigned_to=TV), 2)
        dem = db.notifications.count_documents.call_args.args[0]
        danh_dau = db.notifications.update_many.call_args.args[0]
        for q in (dem, danh_dau):
            self.assertFalse(q["is_read"])
            loai = {d["reference_type"] for d in q["$or"]}
            self.assertEqual(loai, {"appointment", "application", "support_request"})
            self.assertNotIn("job_order", loai)  # thông báo về đơn chỉ Admin/Manager


class DanhDauYeuCauHoTroTests(unittest.IsolatedAsyncioTestCase):
    async def _doc(self, nguoi, giu):
        from app.api import appointments

        with patch.object(appointments, "get_notification_by_reference",
                          AsyncMock(return_value={"reference_type": "support_request", "reference_code": "HT-1"})), \
             patch("app.db.support_requests.get_request", AsyncMock(return_value={"code": "HT-1", "assigned_to": giu})), \
             patch.object(appointments, "mark_notification_read", AsyncMock(return_value=True)), \
             patch.object(appointments, "require_appointment_access", AsyncMock(side_effect=AssertionError("nhánh lịch hẹn"))):
            return await appointments.read_notification("HT-1", nguoi)

    async def test_khong_con_roi_vao_nhanh_lich_hen(self):
        ra = await self._doc({"email": "ql@example.com", "role": "manager"}, "ai.do@example.com")
        self.assertTrue(ra["is_read"])

    async def test_consultant_danh_dau_viec_chua_ai_nhan_hoac_cua_minh(self):
        self.assertTrue((await self._doc({"email": TV, "role": "consultant"}, None))["is_read"])
        self.assertTrue((await self._doc({"email": TV, "role": "consultant"}, TV))["is_read"])

    async def test_consultant_khong_danh_dau_viec_nguoi_khac(self):
        with self.assertRaises(HTTPException) as loi:
            await self._doc({"email": TV, "role": "consultant"}, "nguoi.khac@example.com")
        self.assertEqual(loi.exception.status_code, 403)


class ApiDemTests(unittest.IsolatedAsyncioTestCase):
    async def test_so_tren_nut_theo_pham_vi_nguoi_xem(self):
        from app.api import appointments

        with patch("app.db.database.count_notifications", AsyncMock(return_value=4)) as dem:
            self.assertEqual(await appointments.unread_notification_count({"email": TV, "role": "consultant"}), {"count": 4})
            self.assertEqual(dem.await_args.kwargs["assigned_to"], TV)
            await appointments.unread_notification_count({"email": "ql@example.com", "role": "manager"})
            self.assertIsNone(dem.await_args.kwargs["assigned_to"])


if __name__ == "__main__":
    unittest.main()
