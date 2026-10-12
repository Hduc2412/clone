"""Chỉ tiêu đơn, đơn quá hạn, và tình trạng đơn cho khung chat (12/10).

Luật chủ đồ án chốt: đăng ký không đổi gì; "Trúng tuyển" trừ một chỉ tiêu; đủ chỉ tiêu
thì "Đã hoàn thành chỉ tiêu" và tự ẩn; người đã tính rút/hủy thì trả chỉ tiêu và báo
Admin nhưng KHÔNG tự mở lại đơn; đơn quá hạn tự ẩn rồi báo Admin gỡ.
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.consultation import order_context
from app.db import job_orders as store
from app.rag import job_lookup
from app.services import chi_tieu, het_han_don

HO_SO = {"application_code": "HS-001", "job_order_code": "DH-0001", "status": "waiting_interview"}


class DemChiTieuTests(unittest.IsolatedAsyncioTestCase):
    def _va(self, *, danh_dau=True, go_dau="DH-0001", don_sau=None, don_tra=None):
        bao = AsyncMock()
        tang = AsyncMock(return_value=don_sau or {"code": "DH-0001", "status": "open", "hired_count": 1, "quota": 5})
        giam = AsyncMock(return_value=don_tra or {"code": "DH-0001", "status": "filled", "hired_count": 4, "quota": 5})
        cac = [
            patch.object(chi_tieu, "_danh_dau", AsyncMock(return_value=danh_dau)),
            patch.object(chi_tieu, "_go_dau", AsyncMock(return_value=go_dau)),
            patch.object(chi_tieu.don_store, "increment_hired", tang),
            patch.object(chi_tieu.don_store, "decrement_hired", giam),
            patch.object(chi_tieu, "bao_admin", bao),
        ]
        for c in cac:
            c.start()
            self.addCleanup(c.stop)
        return tang, giam, bao

    async def test_trung_tuyen_tru_mot_chi_tieu(self):
        tang, giam, bao = self._va()
        await chi_tieu.khi_doi_trang_thai(HO_SO, "passed")
        tang.assert_awaited_once_with("DH-0001")
        giam.assert_not_awaited()
        bao.assert_not_awaited()  # chưa đủ chỉ tiêu thì không làm phiền Admin

    async def test_dang_ky_va_cac_buoc_khac_khong_doi_gi(self):
        tang, giam, bao = self._va()
        for trang_thai in ("collecting_documents", "screening", "eligible", "training", "waiting_interview",
                           "visa_processing", "departed", "rejected"):
            await chi_tieu.khi_doi_trang_thai(HO_SO, trang_thai)
        tang.assert_not_awaited()
        giam.assert_not_awaited()

    async def test_da_tinh_roi_thi_khong_tinh_lan_hai(self):
        tang, _, _ = self._va(danh_dau=False)
        await chi_tieu.khi_doi_trang_thai(HO_SO, "passed")
        tang.assert_not_awaited()

    async def test_ho_so_khong_gan_don_thi_khong_tinh(self):
        tang, _, _ = self._va()
        await chi_tieu.khi_doi_trang_thai({"application_code": "HS-002", "status": "waiting_interview"}, "passed")
        tang.assert_not_awaited()

    async def test_du_chi_tieu_thi_bao_admin_da_tu_an(self):
        _, _, bao = self._va(don_sau={"code": "DH-0001", "status": "filled", "hired_count": 5, "quota": 5})
        await chi_tieu.khi_doi_trang_thai(HO_SO, "passed")
        loai, ma, tieu_de = bao.await_args.args[:3]
        self.assertEqual((loai, ma), ("job_order.filled", "DH-0001"))
        self.assertIn("5/5", tieu_de)
        self.assertIn("Đã hoàn thành chỉ tiêu", tieu_de)

    async def test_rut_sau_khi_da_tinh_thi_tra_va_bao_nhung_khong_mo_lai(self):
        tang, giam, bao = self._va()
        await chi_tieu.khi_doi_trang_thai({**HO_SO, "status": "visa_processing"}, "withdrawn")
        giam.assert_awaited_once_with("DH-0001")
        tang.assert_not_awaited()
        loai, _, tieu_de = bao.await_args.args[:3]
        self.assertEqual(loai, "job_order.slot_released")
        self.assertIn("mở lại nếu muốn tuyển bù", tieu_de)

    async def test_rut_khi_chua_tung_tinh_thi_khong_tra(self):
        _, giam, bao = self._va(go_dau=None)
        await chi_tieu.khi_doi_trang_thai(HO_SO, "cancelled")
        giam.assert_not_awaited()
        bao.assert_not_awaited()

    async def test_loi_khong_lot_ra_ngoai(self):
        # Hồ sơ đã đổi trạng thái rồi — lỗi đếm chỉ tiêu không được làm nhân viên tưởng thao tác hỏng.
        with patch.object(chi_tieu, "_danh_dau", AsyncMock(side_effect=RuntimeError("mất kết nối"))):
            self.assertIsNone(await chi_tieu.khi_doi_trang_thai(HO_SO, "passed"))


class TuDuChiTieuTests(unittest.IsolatedAsyncioTestCase):
    async def test_tu_du_chi_tieu_thi_tat_cong_khai_nhu_khi_doi_tay(self):
        # Kiểm sống 12/10 bắt được: đơn tự đủ chỉ tiêu vẫn mang `published = True`.
        bang = MagicMock()
        bang.find_one_and_update = AsyncMock(return_value={"code": "DH-1", "status": "open", "hired_count": 2, "quota": 2})
        with patch.object(store, "get_db", return_value={store.COLLECTION: bang}), \
             patch.object(store, "change_status", AsyncMock(return_value={"status": "filled"})) as doi:
            await store.increment_hired("DH-1")
        self.assertEqual(doi.await_args.kwargs["new_status"], "filled")
        self.assertTrue(doi.await_args.kwargs["unpublish"])

    async def test_chua_du_thi_khong_doi_trang_thai(self):
        bang = MagicMock()
        bang.find_one_and_update = AsyncMock(return_value={"code": "DH-1", "status": "open", "hired_count": 1, "quota": 2})
        with patch.object(store, "get_db", return_value={store.COLLECTION: bang}), \
             patch.object(store, "change_status", AsyncMock()) as doi:
            await store.increment_hired("DH-1")
        doi.assert_not_awaited()


class NoiVaoHoSoTests(unittest.IsolatedAsyncioTestCase):
    async def test_doi_trang_thai_ho_so_goi_bo_dem(self):
        from app.api import applications as api

        tu_van = {"email": "tv@example.com", "role": "consultant", "full_name": "TV"}
        existing = {**HO_SO, "assigned_to": tu_van["email"]}
        with patch.object(api, "get_recruitment_application", AsyncMock(return_value=existing)), \
             patch.object(api, "update_recruitment_application", AsyncMock(return_value={**existing, "status": "passed"})), \
             patch.object(api, "create_application_event", AsyncMock()), \
             patch.object(api, "audit_action", AsyncMock()), \
             patch.object(api.chi_tieu, "khi_doi_trang_thai", AsyncMock()) as dem:
            await api.update_application("HS-001", api.ApplicationUpdateRequest(status="passed"), MagicMock(), tu_van)
        dem.assert_awaited_once_with(existing, "passed")


class CongKhaiTests(unittest.TestCase):
    def test_con_lai_tinh_tu_chi_tieu_va_bo_so_da_tuyen(self):
        ra = store.cho_cong_khai({"code": "DH-1", "quota": 5, "hired_count": 2})
        self.assertEqual(ra["con_lai"], 3)
        self.assertNotIn("hired_count", ra)

    def test_khong_bao_gio_am(self):
        self.assertEqual(store.cho_cong_khai({"quota": 2, "hired_count": 3})["con_lai"], 0)

    def test_doc_cong_khai_van_lay_so_da_tuyen_de_tinh(self):
        self.assertNotIn("hired_count", store._PUBLIC_FETCH)
        self.assertEqual(store.PUBLIC_PROJECTION["hired_count"], 0)

    def test_khoi_don_cho_tro_ly_co_chi_tieu(self):
        khoi = order_context.render({"code": "DH-1", "title": "T", "quota": 5, "con_lai": 3,
                                     "requirements": {}, "reference": {}})
        self.assertIn("Chỉ tiêu: còn 3/5 người", khoi)


class TinhTrangDonChoChatTests(unittest.TestCase):
    def test_nhan_ma_don_nhieu_cach_viet(self):
        self.assertEqual(job_lookup.ma_don_trong_cau("đơn dh 0003 với DH-0012 và DH0003"), ["DH-0003", "DH-0012"])
        self.assertEqual(job_lookup.ma_don_trong_cau("tôi muốn đi Tokyo"), [])

    def test_ly_do_tung_trang_thai(self):
        hom_nay = "2026-10-12"
        self.assertIn("đủ chỉ tiêu", job_lookup.ly_do_khong_hien({"status": "filled"}, hom_nay))
        self.assertIn("hết hạn", job_lookup.ly_do_khong_hien({"status": "expired", "deadline": "2026-10-01"}, hom_nay))
        self.assertIn("đóng", job_lookup.ly_do_khong_hien({"status": "closed"}, hom_nay))
        self.assertIn("tạm dừng", job_lookup.ly_do_khong_hien({"status": "paused"}, hom_nay))
        # Vẫn "Đang tuyển" nhưng đã qua hạn: khách thấy đơn biến mất, bot phải nói vì hết hạn.
        self.assertIn("01/10/2026", job_lookup.ly_do_khong_hien({"status": "open", "deadline": "2026-10-01", "published": True}, hom_nay))
        self.assertIsNone(job_lookup.ly_do_khong_hien({"status": "open", "deadline": "2026-12-01", "published": True}, hom_nay))

    def test_khoi_noi_con_bao_nhieu_va_khong_hua_mo_lai(self):
        khoi = job_lookup.render_trang_thai(
            [{"code": "DH-0001", "title": "Tokyo", "status": "open", "deadline": "2026-12-24",
              "published": True, "quota": 5, "con_lai": 2},
             {"code": "DH-0002", "title": "Osaka", "status": "filled", "quota": 3, "con_lai": 0}],
            hom_nay="2026-10-12",
        )
        self.assertIn("DH-0001 · Tokyo: đang tuyển, còn 2/5 chỉ tiêu", khoi)
        self.assertIn("DH-0002 · Osaka: đã đủ chỉ tiêu", khoi)
        self.assertIn("KHÔNG hứa đơn sẽ mở lại", khoi)

    def test_don_nhap_khong_bao_gio_duoc_nhac(self):
        self.assertNotIn("draft", store.TRANG_THAI_NOI_CHO_KHACH)


class QuetHetHanTests(unittest.IsolatedAsyncioTestCase):
    async def test_moi_don_moi_han_mot_thong_bao(self):
        don = [{"code": "DH-0009", "title": "Kobe", "deadline": "2026-10-01", "status": "open"}]
        thong_bao = MagicMock()
        thong_bao.find_one = AsyncMock(side_effect=[None, {"type": het_han_don.LOAI}])
        db = MagicMock(notifications=thong_bao)
        bao = AsyncMock()
        with patch.object(het_han_don.don_store, "don_qua_han_chua_go", AsyncMock(return_value=don)), \
             patch.object(het_han_don, "get_db", return_value=db), \
             patch.object(het_han_don, "bao_admin", bao):
            self.assertEqual(await het_han_don.quet("2026-10-12"), ["DH-0009"])
            self.assertEqual(await het_han_don.quet("2026-10-12"), [])  # quét lại: không thêm
        bao.assert_awaited_once()
        loai, ma, tieu_de, chi_tiet = bao.await_args.args
        self.assertEqual((loai, ma, chi_tiet), ("job_order.expired", "DH-0009", {"deadline": "2026-10-01"}))
        self.assertIn("01/10/2026", tieu_de)
        self.assertIn("Hết hạn", tieu_de)


class QuyenThongBaoDonTests(unittest.IsolatedAsyncioTestCase):
    async def test_consultant_khong_tat_duoc_thong_bao_ve_don(self):
        from app.api import appointments

        tv = {"email": "tv@example.com", "role": "consultant"}
        with patch.object(appointments, "get_notification_by_reference",
                          AsyncMock(return_value={"reference_type": "job_order", "reference_code": "DH-0001"})), \
             patch.object(appointments, "mark_notification_read", AsyncMock(return_value=True)) as danh_dau:
            with self.assertRaises(HTTPException) as loi:
                await appointments.read_notification("DH-0001", tv)
            self.assertEqual(loi.exception.status_code, 403)
            danh_dau.assert_not_awaited()
            ok = await appointments.read_notification("DH-0001", {"email": "ql@example.com", "role": "manager"})
            self.assertTrue(ok["is_read"])


if __name__ == "__main__":
    unittest.main()
