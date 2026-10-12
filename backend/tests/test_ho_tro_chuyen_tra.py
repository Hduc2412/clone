"""Chuyển người xử lý và trả yêu cầu hỗ trợ về hàng đợi.

Trước 07/10 yêu cầu hỗ trợ không có đường nào đổi người xử lý: nhân viên nghỉ, bận
hay nhận nhầm thì yêu cầu — kèm khung giờ hẹn khách đã chọn — nằm ở tên người ấy cho
tới khi có người sửa thẳng database (đúng việc phải làm với 67 yêu cầu ngày 06/10).

Cùng nguyên tắc với hồ sơ đăng ký (`test_handover`): một yêu cầu có một người xử lý
tại một thời điểm, quản lý chuyển được, người giữ tự trả được, người ngoài không đụng
được, và hai thao tác sát nhau thì thao tác sau thất bại chứ không đè.
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, Request

from app.api import support as api
from app.db import support_requests as store

QUAN_LY = {"email": "ql@local.test", "full_name": "QL", "role": "manager"}
A = {"email": "a@local.test", "full_name": "A", "role": "consultant"}
B = {"email": "b@local.test", "full_name": "B", "role": "consultant"}


def _yc(**them):
    return {"code": "HT-AAAAAA", "status": "dang_xu_ly", "assigned_to": A["email"], "full_name": "Khách", **them}


def _req() -> Request:
    return Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1)})


class ChuyenTests(unittest.IsolatedAsyncioTestCase):
    async def _chuyen(self, actor, *, hien_co=None, sau=None, den=B["email"]):
        with patch.object(api.store, "get_request", AsyncMock(return_value=hien_co or _yc())), \
             patch.object(api.store, "chuyen_nguoi_xu_ly", AsyncMock(return_value=sau)) as chuyen, \
             patch.object(api, "validate_assignee", AsyncMock(side_effect=lambda e: e)), \
             patch.object(api, "audit_action", AsyncMock()) as audit, \
             patch.object(api, "create_notification", AsyncMock()) as bao:
            ra = await api.chuyen_nguoi_xu_ly(
                "HT-AAAAAA", api.ChuyenBody(assigned_to=den, note="A nghỉ phép"), _req(), actor
            )
        return ra, chuyen, audit, bao

    async def test_quan_ly_chuyen_duoc_va_khoa_theo_nguoi_dang_giu(self):
        ra, chuyen, audit, bao = await self._chuyen(QUAN_LY, sau=_yc(assigned_to=B["email"]))
        self.assertEqual(ra["assigned_to"], B["email"])
        kw = chuyen.await_args.kwargs
        self.assertEqual((kw["tu"], kw["den"], kw["boi"]), (A["email"], B["email"], QUAN_LY["email"]))
        self.assertEqual(audit.await_args.args[1], "support.handover")
        self.assertEqual(bao.await_args.kwargs["detail"]["assigned_to"], B["email"])

    async def test_tu_van_vien_khong_chuyen_duoc(self):
        with self.assertRaises(HTTPException) as ctx:
            await self._chuyen(A)
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_chuyen_cho_chinh_nguoi_dang_giu_thi_bao_loi(self):
        with self.assertRaises(HTTPException) as ctx:
            await self._chuyen(QUAN_LY, den=A["email"])
        self.assertEqual(ctx.exception.status_code, 409)

    async def test_hai_lenh_sat_nhau_thi_lenh_sau_that_bai(self):
        with self.assertRaises(HTTPException) as ctx:
            await self._chuyen(QUAN_LY, sau=None)
        self.assertEqual(ctx.exception.status_code, 409)

    async def test_yeu_cau_chua_ai_nhan_hoac_da_xong_thi_khong_chuyen(self):
        for hien_co in (_yc(status="cho_xu_ly", assigned_to=None), _yc(status="da_xong")):
            with self.subTest(hien_co["status"]), self.assertRaises(HTTPException) as ctx:
                await self._chuyen(QUAN_LY, hien_co=hien_co)
            self.assertEqual(ctx.exception.status_code, 409)

    async def test_thong_bao_hong_khong_lam_hong_viec_da_xong(self):
        with patch.object(api.store, "get_request", AsyncMock(return_value=_yc())), \
             patch.object(api.store, "chuyen_nguoi_xu_ly", AsyncMock(return_value=_yc(assigned_to=B["email"]))), \
             patch.object(api, "validate_assignee", AsyncMock(side_effect=lambda e: e)), \
             patch.object(api, "audit_action", AsyncMock()), \
             patch.object(api, "create_notification", AsyncMock(side_effect=RuntimeError("db"))):
            ra = await api.chuyen_nguoi_xu_ly(
                "HT-AAAAAA", api.ChuyenBody(assigned_to=B["email"], note="A nghỉ phép"), _req(), QUAN_LY
            )
        self.assertEqual(ra["assigned_to"], B["email"])

    def test_bat_buoc_ghi_ly_do(self):
        with self.assertRaises(Exception):
            api.ChuyenBody(assigned_to=B["email"], note="")


class TraVeTests(unittest.IsolatedAsyncioTestCase):
    async def _tra(self, actor, *, sau=_yc(status="cho_xu_ly", assigned_to=None)):
        with patch.object(api.store, "get_request", AsyncMock(return_value=_yc())), \
             patch.object(api.store, "tra_ve_hang_doi", AsyncMock(return_value=sau)) as tra, \
             patch.object(api, "audit_action", AsyncMock()):
            ra = await api.tra_ve_hang_doi("HT-AAAAAA", api.TraVeBody(note="Nhận nhầm"), _req(), actor)
        return ra, tra

    async def test_nguoi_dang_giu_tu_tra_duoc(self):
        ra, tra = await self._tra(A)
        self.assertEqual(ra["status"], "cho_xu_ly")
        self.assertEqual(tra.await_args.kwargs["tu"], A["email"])

    async def test_quan_ly_tra_duoc(self):
        ra, _ = await self._tra(QUAN_LY)
        self.assertIsNone(ra["assigned_to"])

    async def test_nguoi_ngoai_khong_tra_duoc(self):
        with self.assertRaises(HTTPException) as ctx:
            await self._tra(B)
        self.assertEqual(ctx.exception.status_code, 403)


class TangDuLieuTests(unittest.IsolatedAsyncioTestCase):
    async def _goi(self, ham, **kw):
        bang = MagicMock()
        bang.find_one_and_update = AsyncMock(return_value=None)
        db = MagicMock()
        db.__getitem__.return_value = bang
        with patch.object(store, "get_db", return_value=db):
            await ham("HT-AAAAAA", **kw)
        return bang.find_one_and_update.await_args.args

    async def test_chuyen_khoa_theo_nguoi_giu_va_ghi_lich_su(self):
        loc, cap_nhat = await self._goi(store.chuyen_nguoi_xu_ly, tu="a", den="b", boi="ql", ly_do="nghỉ")
        self.assertEqual(loc, {"code": "HT-AAAAAA", "assigned_to": "a", "status": store.STATUS_DANG_XU_LY})
        self.assertEqual(cap_nhat["$set"]["assigned_to"], "b")
        self.assertEqual(cap_nhat["$push"]["lich_su_phu_trach"]["viec"], "chuyen")

    async def test_tra_ve_dua_lai_dung_trang_thai_hang_doi(self):
        """Hàng đợi chỉ lấy `cho_xu_ly` + chưa ai giữ (`claim`): trả về phải đặt đúng cả hai."""
        loc, cap_nhat = await self._goi(store.tra_ve_hang_doi, tu="a", boi="a", ly_do="nhầm")
        self.assertEqual(loc["assigned_to"], "a")
        self.assertEqual(cap_nhat["$set"]["status"], store.STATUS_CHO)
        self.assertIsNone(cap_nhat["$set"]["assigned_to"])

    def test_khach_khong_thay_lich_su_phu_trach(self):
        """Lịch sử chứa email nhân viên; đường công khai dùng danh sách trường cho phép."""
        ban = api._ban_cho_khach(_yc(lich_su_phu_trach=[{"tu": "a@local.test"}]))
        self.assertNotIn("lich_su_phu_trach", ban)
        self.assertNotIn("assigned_to", ban)


if __name__ == "__main__":
    unittest.main()
