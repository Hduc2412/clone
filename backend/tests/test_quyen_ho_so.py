"""Quyền làm việc với hồ sơ ứng viên đi theo **người đang phụ trách đơn còn mở**.

Lỗi gốc, đo được ngày 06/10 bằng hai tài khoản `consultant`: A nhận hồ sơ đăng
ký của khách từ hàng đợi, rồi bị 403 ở hồ sơ ứng viên, ở danh sách CV, và không
thấy nhật ký giới thiệu nào của khách. Bộ đo cũ chạy bằng admin nên không thấy.

Các ca dưới đây kiểm cả hai chiều. Chiều **mất quyền** quan trọng ngang chiều
được quyền: nếu chỉ kiểm chiều được, một bản sửa "cho mọi nhân viên xem mọi hồ
sơ" cũng xanh.
"""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.services import quyen_ho_so

A = {"email": "a@local.test", "role": "consultant"}
B = {"email": "b@local.test", "role": "consultant"}
QUAN_LY = {"email": "ql@local.test", "role": "manager"}

HO_SO = {"code": "UV-AAAAAA", "assigned_to": None}
NHAT_KY = {"code": "RL-1", "profile_code": "UV-AAAAAA", "assigned_to": None}


def don(*, nguoi, ho_so="UV-AAAAAA"):
    """Đơn đang mở mà `list_recruitment_applications(active_only=True)` trả về."""
    return [{"application_code": "HS-1", "profile_code": ho_so, "assigned_to": nguoi}]


class QuyTacTests(unittest.IsolatedAsyncioTestCase):
    async def _co_quyen(self, nguoi, ho_so, *, don_mo):
        with patch.object(
            quyen_ho_so, "list_recruitment_applications", AsyncMock(return_value=don_mo)
        ) as tra:
            ra = await quyen_ho_so.co_quyen_ho_so(ho_so, nguoi)
        return ra, tra

    async def test_nguoi_dang_phu_trach_don_thi_duoc(self):
        ra, _ = await self._co_quyen(A, HO_SO, don_mo=don(nguoi=A["email"]))
        self.assertTrue(ra)

    async def test_khong_phu_trach_don_nao_thi_khong(self):
        ra, _ = await self._co_quyen(B, HO_SO, don_mo=[])
        self.assertFalse(ra)

    async def test_phu_trach_don_cua_khach_khac_thi_khong(self):
        """B phụ trách một đơn — nhưng của ứng viên khác."""
        ra, _ = await self._co_quyen(B, HO_SO, don_mo=don(nguoi=B["email"], ho_so="UV-BBBBBB"))
        self.assertFalse(ra)

    async def test_chi_tinh_don_con_mo(self):
        """Đơn đã đóng thì không còn cho quyền: tra với `active_only=True`."""
        _ra, tra = await self._co_quyen(A, HO_SO, don_mo=[])
        self.assertTrue(tra.await_args.kwargs.get("active_only"))
        self.assertEqual(tra.await_args.kwargs.get("assigned_to"), A["email"])

    async def test_phan_cong_truc_tiep_khong_can_tra_don(self):
        """Đường rẻ trước: được phân công thẳng thì không đọc bảng đơn."""
        ra, tra = await self._co_quyen(A, {**HO_SO, "assigned_to": A["email"]}, don_mo=[])
        self.assertTrue(ra)
        tra.assert_not_awaited()

    async def test_quan_ly_khong_can_tra_don(self):
        ra, tra = await self._co_quyen(QUAN_LY, HO_SO, don_mo=[])
        self.assertTrue(ra)
        tra.assert_not_awaited()


class NhatKyTheoHoSoHienTaiTests(unittest.IsolatedAsyncioTestCase):
    """Hồ sơ chuyển A → B: quyền với nhật ký cũ phải chuyển theo.

    Đúng kịch bản chủ đồ án tái hiện ngày 06/10. Nhật ký được tạo lúc hồ sơ còn
    ở A, nên `log.assigned_to == A` — một ẢNH CHỤP. Quản lý chuyển hồ sơ cho B.
    Bản sửa thứ nhất dùng ảnh chụp ấy làm đường cho phép, nên A vẫn đọc được còn
    B bị 403 — ngược hẳn với quyền trên chính hồ sơ.
    """

    NHAT_KY_CU = {"code": "RL-1", "profile_code": "UV-AAAAAA", "assigned_to": A["email"]}
    HO_SO_DA_CHUYEN = {"code": "UV-AAAAAA", "assigned_to": B["email"]}

    async def _doc(self, nguoi, *, ho_so=None, don_mo=()):
        with patch.object(
            quyen_ho_so.profile_store,
            "get_by_code",
            AsyncMock(return_value=self.HO_SO_DA_CHUYEN if ho_so is None else ho_so),
        ), patch.object(
            quyen_ho_so, "list_recruitment_applications", AsyncMock(return_value=list(don_mo))
        ):
            return await quyen_ho_so.co_quyen_nhat_ky(dict(self.NHAT_KY_CU), nguoi)

    async def test_nguoi_cu_mat_quyen_doc_nhat_ky_cu(self):
        self.assertFalse(await self._doc(A))

    async def test_nguoi_moi_doc_duoc_nhat_ky_cu(self):
        self.assertTrue(await self._doc(B))

    async def test_nhat_ky_va_ho_so_luon_cung_mot_ket_luan(self):
        """Với mọi người, quyền trên nhật ký phải trùng quyền trên hồ sơ hiện tại."""
        for nguoi in (A, B, QUAN_LY):
            with self.subTest(nguoi=nguoi["email"]):
                with patch.object(
                    quyen_ho_so, "list_recruitment_applications", AsyncMock(return_value=[])
                ):
                    tren_ho_so = await quyen_ho_so.co_quyen_ho_so(self.HO_SO_DA_CHUYEN, nguoi)
                self.assertEqual(await self._doc(nguoi), tren_ho_so)

    async def test_ho_so_khong_con_thi_chi_quan_ly(self):
        """Hồ sơ đã bị xóa: không còn ai để quyền đi theo — chỉ quản lý."""
        with patch.object(quyen_ho_so.profile_store, "get_by_code", AsyncMock(return_value=None)):
            self.assertFalse(await quyen_ho_so.co_quyen_nhat_ky(dict(self.NHAT_KY_CU), A))
            self.assertTrue(await quyen_ho_so.co_quyen_nhat_ky(dict(self.NHAT_KY_CU), QUAN_LY))

    async def test_danh_sach_loc_theo_ho_so_khong_theo_anh_chup(self):
        """Danh sách của B có nhật ký cũ; danh sách của A thì không."""
        async def truc_tiep(email):
            return {"UV-AAAAAA"} if email == B["email"] else set()

        with patch.object(quyen_ho_so, "ma_ho_so_truc_tiep", truc_tiep), patch.object(
            quyen_ho_so, "ma_ho_so_qua_don", AsyncMock(return_value=set())
        ):
            q_a = await quyen_ho_so.dieu_kien_nhat_ky({"session_id": "s"}, A)
            q_b = await quyen_ho_so.dieu_kien_nhat_ky({"session_id": "s"}, B)
        self.assertNotIn("assigned_to", q_a)
        self.assertEqual(q_a["profile_code"], {"$in": []})
        self.assertEqual(q_b["profile_code"], {"$in": ["UV-AAAAAA"]})


class DanhSachHoSoTests(unittest.IsolatedAsyncioTestCase):
    async def _dk(self, nguoi, query, *, ma):
        with patch.object(quyen_ho_so, "ma_ho_so_qua_don", AsyncMock(return_value=set(ma))):
            return await quyen_ho_so.dieu_kien_ho_so(query, nguoi)

    async def test_them_ho_so_dang_phu_trach_qua_don(self):
        q = await self._dk(A, {"status": "x"}, ma=["UV-AAAAAA"])
        self.assertEqual(q["status"], "x")
        self.assertIn({"assigned_to": A["email"]}, q["$or"])
        self.assertIn({"code": {"$in": ["UV-AAAAAA"]}}, q["$or"])

    async def test_nhan_vien_khong_dung_bo_loc_de_xem_cua_nguoi_khac(self):
        """Truyền `assigned_to=b@…` vào bộ lọc không được mở ra phần của B."""
        q = await self._dk(A, {"assigned_to": B["email"]}, ma=[])
        self.assertNotIn("assigned_to", q)
        self.assertEqual(q["$or"], [{"assigned_to": A["email"]}])

    async def test_quan_ly_giu_nguyen_truy_van(self):
        goc = {"assigned_to": B["email"], "status": "x"}
        self.assertEqual(await self._dk(QUAN_LY, dict(goc), ma=["UV-AAAAAA"]), goc)

    async def test_truy_van_san_co_or_thi_ghep_and(self):
        """Không đè `$or` của câu truy vấn gốc — đè là nới rộng lặng lẽ."""
        goc = {"$or": [{"status": "a"}, {"status": "b"}]}
        q = await self._dk(A, goc, ma=["UV-AAAAAA"])
        self.assertEqual(q["$and"][0]["$or"], goc["$or"])
        self.assertIn({"assigned_to": A["email"]}, q["$and"][1]["$or"])


class DuongApiTests(unittest.IsolatedAsyncioTestCase):
    """Ba đường lỗi gốc đo được: hồ sơ, danh sách CV, chi tiết nhật ký."""

    async def asyncSetUp(self):
        self.don_mo = []
        vá = patch.object(
            quyen_ho_so,
            "list_recruitment_applications",
            AsyncMock(side_effect=lambda **kw: [
                d for d in self.don_mo if d["assigned_to"] == kw.get("assigned_to")
            ]),
        )
        vá.start()
        self.addCleanup(vá.stop)

    async def _ho_so(self, nguoi):
        from app.api import profiles

        with patch.object(profiles.store, "get_by_code", AsyncMock(return_value=dict(HO_SO))):
            return await profiles.profile_detail("UV-AAAAAA", current_user=nguoi)

    async def _danh_sach_cv(self, nguoi):
        from app.api import documents

        with patch.object(
            documents.profiles, "get_by_code", AsyncMock(return_value=dict(HO_SO))
        ), patch.object(documents.store, "list_for_profile", AsyncMock(return_value=[])):
            return await documents.list_profile_documents("UV-AAAAAA", current_user=nguoi)

    async def _nhat_ky(self, nguoi):
        from app.api import matching

        with patch.object(
            matching.log_store, "get_log", AsyncMock(return_value=dict(NHAT_KY))
        ), patch.object(
            quyen_ho_so.profile_store, "get_by_code", AsyncMock(return_value=dict(HO_SO))
        ):
            return await matching.recommendation_log_detail("RL-1", current_user=nguoi)

    async def test_nguoi_nhan_don_mo_duoc_ca_ba(self):
        self.don_mo = don(nguoi=A["email"])
        await self._ho_so(A)
        await self._danh_sach_cv(A)
        await self._nhat_ky(A)

    async def test_nguoi_khong_phu_trach_bi_chan_ca_ba(self):
        self.don_mo = don(nguoi=A["email"])
        for duong in (self._ho_so, self._danh_sach_cv, self._nhat_ky):
            with self.subTest(duong=duong.__name__):
                with self.assertRaises(HTTPException) as ra:
                    await duong(B)
                self.assertEqual(ra.exception.status_code, 403)

    async def test_don_chuyen_cho_nguoi_khac_thi_quyen_di_theo(self):
        """Quản lý chuyển đơn từ A sang B: B được, A mất — không cần sửa gì thêm.

        Đây là lý do quyền được TÍNH lúc đọc thay vì chép sang hồ sơ ứng viên lúc
        nhận: chép thì sau bước chuyển này hồ sơ ứng viên vẫn nằm ở A.
        """
        self.don_mo = don(nguoi=B["email"])
        await self._ho_so(B)
        with self.assertRaises(HTTPException):
            await self._ho_so(A)

    async def test_don_dong_thi_mat_quyen(self):
        self.don_mo = []  # `active_only=True` không còn trả đơn đã đóng
        with self.assertRaises(HTTPException):
            await self._ho_so(A)


if __name__ == "__main__":
    unittest.main()
