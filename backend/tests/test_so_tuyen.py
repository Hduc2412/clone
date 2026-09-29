"""Ghi kết quả buổi sơ tuyển — mắt xích giữa phần mềm và con người.

Trình độ tiếng Nhật là tiêu chí loại người nhiều nhất trong bảy điều kiện bắt
buộc, và nó **không xác thực được bằng máy**: nhìn ảnh chụp bằng không phân biệt
được thật với giả. Nên việc ấy là của buổi gặp giữa người với người, còn hệ thống
chỉ ghi lại kết quả cùng cách đối chứng.

Hai điều bộ này phải canh, và cả hai đều là chuyện hỏng thì không ai thấy ngay:

1. **Một lời gọi đổi cả trình độ lẫn trạng thái.** Tách làm hai nút thì sớm muộn
   có hồ sơ bấm cái này quên cái kia, và hai chỗ trong hệ thống nói hai điều khác
   nhau về cùng một người.
2. **Không có cửa sau cho máy trạng thái.** Một đường ghi mới mà nới luật chuyển
   trạng thái thì máy trạng thái coi như không còn — và nó là thứ giữ cho hồ sơ
   không nhảy thẳng từ nháp sang đạt.
"""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.api import applications
from app.db import candidate_profiles as profiles


NHAN_VIEN = {"email": "tu.van@example.com", "role": "consultant", "full_name": "Tư Vấn"}

HO_SO_NANG_LUC = {
    "code": "HSUV-0001",
    "session_id": "11111111-1111-4111-8111-111111111111",
    "version": 3,
    "fields": {
        "full_name": {"value": "Nguyễn Thị Hoa", "source": "user_confirmed"},
        "japanese_level": {"value": "chua_hoc", "source": "user_confirmed"},
    },
    "preferences": {},
}

HO_SO_TUYEN_DUNG = {
    "application_code": "HS-ABC123",
    "profile_code": "HSUV-0001",
    "status": "screening",
    "assigned_to": NHAN_VIEN["email"],
}


def body(**ghi_de):
    mac_dinh = {
        "japanese_level": "N4",
        "chung_cu": profiles.CHUNG_CU_BAN_GOC,
        "hinh_thuc": "truc_tiep",
        "next_status": "eligible",
        "note": None,
    }
    return applications.KetQuaSoTuyenBody(**{**mac_dinh, **ghi_de})


class GhiKetQuaSoTuyenTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.ho_so_tuyen_dung = dict(HO_SO_TUYEN_DUNG)
        self.ho_so_nang_luc = {
            **HO_SO_NANG_LUC,
            "fields": {k: dict(v) for k, v in HO_SO_NANG_LUC["fields"].items()},
        }

    async def _goi(self, payload, *, ghi_ho_so=None, doi_trang_thai=None):
        ghi_ho_so = ghi_ho_so or AsyncMock(return_value={"code": "HSUV-0001"})
        doi_trang_thai = doi_trang_thai or AsyncMock(
            return_value={**self.ho_so_tuyen_dung, "status": payload.next_status}
        )
        with patch.object(
            applications, "get_recruitment_application",
            AsyncMock(return_value=self.ho_so_tuyen_dung),
        ), patch.object(
            profiles, "get_by_code", AsyncMock(return_value=self.ho_so_nang_luc)
        ), patch.object(
            profiles, "apply_changes", ghi_ho_so
        ), patch.object(
            applications, "update_recruitment_application", doi_trang_thai
        ), patch.object(
            applications, "create_application_event", AsyncMock()
        ), patch.object(
            applications, "audit_action", AsyncMock()
        ):
            ket_qua = await applications.ghi_ket_qua_so_tuyen(
                "HS-ABC123", payload, _request(), NHAN_VIEN
            )
        return ket_qua, ghi_ho_so, doi_trang_thai

    async def test_mot_loi_goi_doi_ca_trinh_do_lan_trang_thai(self):
        """Ca trung tâm của cả file. Ghi được cái này mà trượt cái kia là hai nơi
        nói hai điều khác nhau về cùng một người."""
        ket_qua, ghi_ho_so, doi_trang_thai = await self._goi(body())

        ghi_ho_so.assert_awaited_once()
        fields = ghi_ho_so.await_args.kwargs["fields"]
        self.assertEqual(fields["japanese_level"]["value"], "N4")

        doi_trang_thai.assert_awaited_once()
        self.assertEqual(
            doi_trang_thai.await_args.args[1]["status"], "eligible"
        )
        self.assertEqual(ket_qua["so_tuyen"]["new_status"], "eligible")

    async def test_trinh_do_ghi_nguon_staff(self):
        """Nguồn `staff` đứng đầu thứ tự ưu tiên, nên nó đè được lời khai của khách."""
        _, ghi_ho_so, _ = await self._goi(body())
        o = ghi_ho_so.await_args.kwargs["fields"]["japanese_level"]
        self.assertEqual(o["source"], "staff")

    async def test_ghi_lai_da_doi_chung_bang_cach_nao(self):
        """Không chỉ ghi đạt hay không đạt. Sau này có chuyện thì biết lúc ấy đã
        kiểm tới đâu và ai kiểm."""
        _, ghi_ho_so, _ = await self._goi(
            body(chung_cu=profiles.CHUNG_CU_TRA_CUU)
        )
        o = ghi_ho_so.await_args.kwargs["fields"]["japanese_level"]
        self.assertEqual(o["evidence_type"], profiles.CHUNG_CU_TRA_CUU)
        self.assertEqual(o["verification"], profiles.XAC_THUC_DOI_CHUNG)
        self.assertEqual(o["verified_by"], NHAN_VIEN["email"])

    async def test_khong_xuat_trinh_duoc_gi_thi_trinh_do_van_la_tu_khai(self):
        """Luật quan trọng nhất của mức xác thực.

        Không có nó thì nhân viên bấm hết biểu mẫu là mọi hồ sơ đều thành "đã xác
        thực", kể cả hồ sơ không có một mẩu căn cứ nào — và nhãn ấy đi theo ứng
        viên tới tận buổi phỏng vấn với công ty Nhật, nơi nó bị lật lại.
        """
        ket_qua, ghi_ho_so, _ = await self._goi(
            body(chung_cu=profiles.CHUNG_CU_KHONG_CO)
        )
        o = ghi_ho_so.await_args.kwargs["fields"]["japanese_level"]
        self.assertEqual(o["verification"], profiles.XAC_THUC_TU_KHAI)
        # Vẫn cho đi tiếp — đó là quyết định của người vừa gặp ứng viên. Nhưng
        # phải hiện ra, không được lặng lẽ mang nhãn "đã xác thực".
        self.assertIn("TỰ KHAI", ket_qua["canh_bao"])

    async def test_co_can_cu_thi_khong_canh_bao(self):
        ket_qua, _, _ = await self._goi(body(chung_cu=profiles.CHUNG_CU_BAN_GOC))
        self.assertIsNone(ket_qua["canh_bao"])


class KhongCoCuaSauChoMayTrangThaiTests(unittest.IsolatedAsyncioTestCase):
    """Đường ghi mới không được nới luật chuyển trạng thái."""

    async def _goi_voi_trang_thai(self, hien_tai: str, ke_tiep: str):
        ghi_ho_so = AsyncMock()
        doi_trang_thai = AsyncMock()
        with patch.object(
            applications, "get_recruitment_application",
            AsyncMock(return_value={**HO_SO_TUYEN_DUNG, "status": hien_tai}),
        ), patch.object(
            profiles, "get_by_code", AsyncMock(return_value=HO_SO_NANG_LUC)
        ), patch.object(
            profiles, "apply_changes", ghi_ho_so
        ), patch.object(
            applications, "update_recruitment_application", doi_trang_thai
        ):
            with self.assertRaises(HTTPException) as ctx:
                await applications.ghi_ket_qua_so_tuyen(
                    "HS-ABC123", body(next_status=ke_tiep), _request(), NHAN_VIEN
                )
        return ctx.exception, ghi_ho_so, doi_trang_thai

    async def test_nhap_khong_nhay_thang_sang_dat(self):
        loi, ghi_ho_so, doi_trang_thai = await self._goi_voi_trang_thai(
            "draft", "eligible"
        )
        self.assertEqual(loi.status_code, 409)
        # Và không được ghi gì cả: kiểm hết trước khi ghi bất cứ thứ gì.
        ghi_ho_so.assert_not_awaited()
        doi_trang_thai.assert_not_awaited()

    async def test_ho_so_da_dong_thi_khong_mo_lai_duoc(self):
        loi, ghi_ho_so, _ = await self._goi_voi_trang_thai("rejected", "eligible")
        self.assertEqual(loi.status_code, 409)
        ghi_ho_so.assert_not_awaited()

    async def test_so_tuyen_sang_tu_choi_thi_duoc(self):
        """Không phải buổi gặp nào cũng cho kết quả đạt."""
        ghi_ho_so = AsyncMock(return_value={"code": "HSUV-0001"})
        doi = AsyncMock(return_value={**HO_SO_TUYEN_DUNG, "status": "rejected"})
        with patch.object(
            applications, "get_recruitment_application",
            AsyncMock(return_value=dict(HO_SO_TUYEN_DUNG)),
        ), patch.object(
            profiles, "get_by_code", AsyncMock(return_value=HO_SO_NANG_LUC)
        ), patch.object(profiles, "apply_changes", ghi_ho_so), patch.object(
            applications, "update_recruitment_application", doi
        ), patch.object(
            applications, "create_application_event", AsyncMock()
        ), patch.object(applications, "audit_action", AsyncMock()):
            ket_qua = await applications.ghi_ket_qua_so_tuyen(
                "HS-ABC123", body(next_status="rejected"), _request(), NHAN_VIEN
            )
        self.assertEqual(ket_qua["so_tuyen"]["new_status"], "rejected")


class KiemTruocKhiGhiTests(unittest.IsolatedAsyncioTestCase):
    """Không ghi nửa chừng vì một giá trị sai lẽ ra phải chặn được từ đầu."""

    async def _mong_doi_loi(self, payload, *, ho_so_nang_luc=HO_SO_NANG_LUC,
                            ho_so_tuyen_dung=None):
        ghi_ho_so = AsyncMock()
        with patch.object(
            applications, "get_recruitment_application",
            AsyncMock(return_value=ho_so_tuyen_dung or dict(HO_SO_TUYEN_DUNG)),
        ), patch.object(
            profiles, "get_by_code", AsyncMock(return_value=ho_so_nang_luc)
        ), patch.object(profiles, "apply_changes", ghi_ho_so), patch.object(
            applications, "update_recruitment_application", AsyncMock()
        ):
            with self.assertRaises(HTTPException) as ctx:
                await applications.ghi_ket_qua_so_tuyen(
                    "HS-ABC123", payload, _request(), NHAN_VIEN
                )
        ghi_ho_so.assert_not_awaited()
        return ctx.exception

    async def test_trinh_do_ngoai_danh_muc_bi_tu_choi(self):
        loi = await self._mong_doi_loi(body(japanese_level="N9"))
        self.assertEqual(loi.status_code, 422)

    async def test_cach_doi_chung_ngoai_danh_muc_bi_tu_choi(self):
        loi = await self._mong_doi_loi(body(chung_cu="anh_chup_bang"))
        self.assertEqual(loi.status_code, 422)
        # Cố ý: không nhận ảnh chụp bằng. Nhìn ảnh không phân biệt được thật giả.
        self.assertIn("đối chứng", loi.detail)

    async def test_hinh_thuc_gap_ngoai_danh_muc_bi_tu_choi(self):
        loi = await self._mong_doi_loi(body(hinh_thuc="qua_tin_nhan"))
        self.assertEqual(loi.status_code, 422)

    async def test_ho_so_chua_gan_ho_so_nang_luc_thi_bao_ro(self):
        loi = await self._mong_doi_loi(
            body(), ho_so_tuyen_dung={**HO_SO_TUYEN_DUNG, "profile_code": None}
        )
        self.assertEqual(loi.status_code, 409)
        self.assertIn("chưa gắn hồ sơ năng lực", loi.detail)

    async def test_khong_tim_thay_ho_so_nang_luc_thi_khong_ghi_gi(self):
        loi = await self._mong_doi_loi(body(), ho_so_nang_luc=None)
        self.assertEqual(loi.status_code, 409)

    async def test_nguoi_khac_phu_trach_thi_bi_chan(self):
        ghi_ho_so = AsyncMock()
        with patch.object(
            applications, "get_recruitment_application",
            AsyncMock(return_value={**HO_SO_TUYEN_DUNG, "assigned_to": "ai.do@example.com"}),
        ), patch.object(profiles, "apply_changes", ghi_ho_so):
            with self.assertRaises(HTTPException) as ctx:
                await applications.ghi_ket_qua_so_tuyen(
                    "HS-ABC123", body(), _request(), NHAN_VIEN
                )
        self.assertEqual(ctx.exception.status_code, 403)
        ghi_ho_so.assert_not_awaited()


class GhiTrinhDoTruocTrangThaiSauTests(unittest.IsolatedAsyncioTestCase):
    """Thứ tự ghi có chủ ý, vì không có giao dịch.

    Trượt ở bước hai: hồ sơ năng lực đã có trình độ đã đối chứng, hồ sơ tuyển dụng
    còn ở bước sơ tuyển — nhân viên mở ra thấy việc chưa xong và làm lại.

    Ngược lại thì tệ hơn nhiều: hồ sơ tuyển dụng ghi "đạt" trong khi trình độ vẫn
    là lời khai chưa ai kiểm.
    """

    async def test_trinh_do_ghi_truoc_trang_thai(self):
        thu_tu = []
        ghi_ho_so = AsyncMock(side_effect=lambda *a, **k: thu_tu.append("trinh_do") or {"code": "x"})
        doi = AsyncMock(side_effect=lambda *a, **k: thu_tu.append("trang_thai") or dict(HO_SO_TUYEN_DUNG))
        with patch.object(
            applications, "get_recruitment_application",
            AsyncMock(return_value=dict(HO_SO_TUYEN_DUNG)),
        ), patch.object(
            profiles, "get_by_code", AsyncMock(return_value=HO_SO_NANG_LUC)
        ), patch.object(profiles, "apply_changes", ghi_ho_so), patch.object(
            applications, "update_recruitment_application", doi
        ), patch.object(
            applications, "create_application_event", AsyncMock()
        ), patch.object(applications, "audit_action", AsyncMock()):
            await applications.ghi_ket_qua_so_tuyen(
                "HS-ABC123", body(), _request(), NHAN_VIEN
            )
        self.assertEqual(thu_tu, ["trinh_do", "trang_thai"])

    async def test_trang_thai_ghi_truot_thi_bao_ro_da_ghi_duoc_gi(self):
        """Thông báo lỗi phải nói rõ nửa nào đã lưu, không thì nhân viên đoán."""
        with patch.object(
            applications, "get_recruitment_application",
            AsyncMock(return_value=dict(HO_SO_TUYEN_DUNG)),
        ), patch.object(
            profiles, "get_by_code", AsyncMock(return_value=HO_SO_NANG_LUC)
        ), patch.object(
            profiles, "apply_changes", AsyncMock(return_value={"code": "x"})
        ), patch.object(
            applications, "update_recruitment_application", AsyncMock(return_value=None)
        ):
            with self.assertRaises(HTTPException) as ctx:
                await applications.ghi_ket_qua_so_tuyen(
                    "HS-ABC123", body(), _request(), NHAN_VIEN
                )
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("Đã ghi trình độ", ctx.exception.detail)
        self.assertIn("KHÔNG đổi", ctx.exception.detail)

    async def test_ho_so_vua_bi_nguoi_khac_sua_thi_khong_doi_trang_thai(self):
        """Khóa lạc quan của hồ sơ năng lực phải chặn cả lượt ghi trạng thái."""
        doi = AsyncMock()
        with patch.object(
            applications, "get_recruitment_application",
            AsyncMock(return_value=dict(HO_SO_TUYEN_DUNG)),
        ), patch.object(
            profiles, "get_by_code", AsyncMock(return_value=HO_SO_NANG_LUC)
        ), patch.object(
            profiles, "apply_changes", AsyncMock(return_value=None)
        ), patch.object(applications, "update_recruitment_application", doi):
            with self.assertRaises(HTTPException) as ctx:
                await applications.ghi_ket_qua_so_tuyen(
                    "HS-ABC123", body(), _request(), NHAN_VIEN
                )
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("chưa có gì được lưu", ctx.exception.detail)
        doi.assert_not_awaited()


class MucXacThucTests(unittest.TestCase):
    def test_ban_goc_va_tra_cuu_deu_la_da_doi_chung(self):
        self.assertEqual(
            profiles.muc_xac_thuc(profiles.CHUNG_CU_BAN_GOC),
            profiles.XAC_THUC_DOI_CHUNG,
        )
        self.assertEqual(
            profiles.muc_xac_thuc(profiles.CHUNG_CU_TRA_CUU),
            profiles.XAC_THUC_DOI_CHUNG,
        )

    def test_khong_xuat_trinh_la_tu_khai(self):
        self.assertEqual(
            profiles.muc_xac_thuc(profiles.CHUNG_CU_KHONG_CO),
            profiles.XAC_THUC_TU_KHAI,
        )

    def test_ho_so_chua_co_o_tieng_nhat_thi_khong_gan_nhan(self):
        """Gắn nhãn "đã đối chứng" lên một ô không tồn tại là tạo dữ liệu từ hư không."""
        ra = profiles.danh_dau_xac_thuc(
            {"full_name": {"value": "A"}},
            chung_cu=profiles.CHUNG_CU_BAN_GOC,
            nguoi_ghi="x@example.com",
        )
        self.assertNotIn("japanese_level", ra)


def _request():
    from fastapi import Request

    return Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1234)})


if __name__ == "__main__":
    unittest.main()
