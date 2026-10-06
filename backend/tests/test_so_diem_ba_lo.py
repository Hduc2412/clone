"""Ba lỗ của sổ điểm — mỗi lỗ một nhóm ca.

Sổ điểm lưu **từng sự kiện thay vì một con số tổng**, và đó là quyết định có chủ
ý: luôn truy ngược được vì sao điểm thay đổi. Ba lỗi dưới đây đều phá đúng tính
chất ấy, và không lỗi nào làm hệ thống báo gì.

1. **Lọc ngày lệch bảy tiếng.** Mốc ghi là UTC, người lọc nghĩ theo giờ Việt Nam.
2. **Lý do chỉ có dấu cách.** `min_length` đếm ký tự, nên năm khoảng trắng qua được.
3. **Mất điểm khi database lỗi.** Bắt ngoại lệ rồi `print` một dòng.
"""
import json
import pathlib
import tempfile
import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from app.api import staff_scores
from app.services import score_outbox, score_service


class LocNgayTheoGioVietNamTests(unittest.TestCase):
    """Mốc ghi là UTC, người lọc nghĩ theo giờ của họ.

    Bản trước dựng `datetime` **không mang múi giờ** rồi so thẳng — pymongo coi nó
    là UTC, nên cửa sổ lệch đúng bảy tiếng. Hậu quả rất cụ thể: việc nhân viên làm
    **sau 17h giờ Việt Nam** rơi sang ô điểm ngày hôm sau. Người gọi điện cho ứng
    viên lúc 8 giờ tối thấy bảng điểm hôm nay trống, hôm sau tự dưng có thêm điểm.
    """

    def test_dau_ngay_la_17h_UTC_hom_truoc(self):
        tu, _ = staff_scores._window("2026-10-01", None)
        self.assertEqual(tu, datetime(2026, 9, 30, 17, 0, 0, tzinfo=UTC))

    def test_cuoi_ngay_lap_day_den_micro_giay(self):
        """Sự kiện lúc 23:59:59.4 vẫn thuộc ngày đó; `<=` với 23:59:59.0 loại nó."""
        _, den = staff_scores._window(None, "2026-10-01")
        self.assertEqual(
            den, datetime(2026, 10, 1, 16, 59, 59, 999999, tzinfo=UTC)
        )

    def test_moc_tra_ve_luon_mang_mui_gio(self):
        """Mốc không mang múi giờ là chỗ sinh ra toàn bộ lỗi này."""
        tu, den = staff_scores._window("2026-10-01", "2026-10-02")
        self.assertIsNotNone(tu.tzinfo)
        self.assertIsNotNone(den.tzinfo)

    def test_viec_lam_luc_20h_gio_viet_nam_nam_trong_ngay_do(self):
        """Ca gần với đời thật nhất: nhân viên gọi điện buổi tối."""
        tu, den = staff_scores._window("2026-10-01", "2026-10-01")
        # 20h ngày 01/10 giờ Việt Nam = 13h cùng ngày theo UTC.
        luc_20h = datetime(2026, 10, 1, 13, 0, 0, tzinfo=UTC)
        self.assertTrue(tu <= luc_20h <= den, "việc làm buổi tối rơi ra ngoài ngày")

    def test_chuoi_da_co_mui_gio_thi_giu_nguyen_y_nguoi_gui(self):
        tu, _ = staff_scores._window("2026-10-01T00:00:00+00:00", None)
        self.assertEqual(tu, datetime(2026, 10, 1, 0, 0, tzinfo=UTC))

    def test_ngay_viet_sai_bao_loi_ro(self):
        from fastapi import HTTPException

        with self.assertRaises(HTTPException) as ctx:
            staff_scores._window("ngay-mai", None)
        self.assertEqual(ctx.exception.status_code, 400)


class LyDoTruDiemPhaiCoChuTests(unittest.TestCase):
    """Điểm trừ tay là thứ duy nhất làm giảm điểm của một người.

    Quy tắc đặt ra là trừ điểm **luôn phải có lý do trong nhật ký**. Một dòng toàn
    khoảng trắng thì nhật ký vẫn đủ dòng mà người bị trừ không biết vì sao — đúng
    thứ quy tắc ấy sinh ra để tránh.
    """

    def _tao(self, note: str):
        return staff_scores.AdjustRequest(points=-5, note=note)

    def test_nam_dau_cach_bi_tu_choi(self):
        with self.assertRaises(Exception):
            self._tao("     ")

    def test_tab_va_xuong_dong_cung_bi_tu_choi(self):
        with self.assertRaises(Exception):
            self._tao("  \t\n  ")

    def test_ly_do_that_thi_nhan(self):
        self.assertEqual(self._tao("đi muộn ba buổi").note, "đi muộn ba buổi")

    def test_cat_khoang_trang_hai_dau_truoc_khi_luu(self):
        """Lưu `"  đi muộn  "` rồi hiển thị thụt lề là thứ không ai cố ý tạo ra."""
        self.assertEqual(self._tao("   đi muộn ba buổi   ").note, "đi muộn ba buổi")

    def test_bon_ky_tu_that_van_bi_tu_choi(self):
        with self.assertRaises(Exception):
            self._tao("  abcd  ")


class MatDiemKhiDatabaseLoiTests(unittest.IsolatedAsyncioTestCase):
    """Lỗ nặng nhất, vì nó hỏng hoàn toàn trong im lặng.

    Bản trước bắt mọi ngoại lệ rồi `print` một dòng ra log máy chủ. Trên máy chạy
    thật dòng ấy trôi mất trong vài phút, và điểm mất hẳn: tổng vẫn ra một con số,
    chỉ là con số đó không còn khớp với việc đã làm. **Người bị thiếu điểm cũng
    không biết để hỏi** — họ đâu có đếm.
    """

    def setUp(self):
        self.thu_muc = tempfile.TemporaryDirectory()
        self.duong = pathlib.Path(self.thu_muc.name) / score_outbox.TEN_TEP
        self._va = patch.object(
            score_outbox, "duong_dan", lambda: self.duong
        )
        self._va.start()

    def tearDown(self):
        self._va.stop()
        self.thu_muc.cleanup()

    async def _ghi_diem_khi_db_hong(self, loi=RuntimeError("mất kết nối")):
        with patch.object(score_service.store, "record", AsyncMock(side_effect=loi)):
            return await score_service.award(
                staff_email="tu.van@example.com",
                action="application.departed",
                reference_type="recruitment_application",
                reference_code="HS-ABC123",
            )

    async def test_database_hong_thi_diem_vao_so_cho_chu_khong_mat(self):
        ra = await self._ghi_diem_khi_db_hong()
        self.assertIsNone(ra, "nơi gọi vẫn nhận None, nghiệp vụ đi tiếp")
        cho = score_outbox.dang_cho()
        self.assertEqual(len(cho), 1)
        self.assertEqual(cho[0]["staff_email"], "tu.van@example.com")
        self.assertEqual(cho[0]["action"], "application.departed")
        self.assertEqual(cho[0]["points"], 20)

    async def test_so_cho_ghi_ca_ly_do_va_thoi_diem(self):
        """Chờ quá lâu là dấu hiệu không ai chạy bù — phải biết nó nằm đó từ bao giờ."""
        await self._ghi_diem_khi_db_hong()
        dong = score_outbox.dang_cho()[0]
        self.assertIn("RuntimeError", dong["ly_do_hoan"])
        self.assertTrue(dong["ghi_luc"])

    async def test_su_co_ghi_diem_khong_lam_gay_viec_nghiep_vu(self):
        """Nhân viên vừa chốt xong một hồ sơ; lỗi sổ điểm không được làm hỏng việc đó."""
        try:
            await self._ghi_diem_khi_db_hong()
        except Exception as exc:  # noqa: BLE001
            self.fail(f"ngoại lệ lọt ra ngoài: {exc!r}")

    async def test_ghi_bu_dua_duoc_vao_database_thi_xoa_khoi_so_cho(self):
        await self._ghi_diem_khi_db_hong()
        with patch.object(
            score_service.store, "record", AsyncMock(return_value={"code": "DS-1"})
        ):
            ket = await score_outbox.ghi_bu()
        self.assertEqual(ket, {"cho": 1, "vao_duoc": 1, "con_lai": 0})
        self.assertEqual(score_outbox.dang_cho(), [])

    async def test_ghi_bu_van_hong_thi_GIU_LAI_de_lan_sau_thu_tiep(self):
        await self._ghi_diem_khi_db_hong()
        with patch.object(
            score_service.store,
            "record",
            AsyncMock(side_effect=RuntimeError("vẫn chưa sống")),
        ):
            ket = await score_outbox.ghi_bu()
        self.assertEqual(ket["con_lai"], 1)
        self.assertEqual(len(score_outbox.dang_cho()), 1)

    async def test_ban_ghi_da_co_trong_database_cung_coi_la_xong(self):
        """`record` trả `None` nghĩa là trùng khóa — điểm đã có mặt, đó mới là đích."""
        await self._ghi_diem_khi_db_hong()
        with patch.object(score_service.store, "record", AsyncMock(return_value=None)):
            ket = await score_outbox.ghi_bu()
        self.assertEqual(ket["vao_duoc"], 1)
        self.assertEqual(score_outbox.dang_cho(), [])

    async def test_khong_ghi_truong_phu_tro_vao_database(self):
        """`ghi_luc` và `ly_do_hoan` là chuyện của sổ chờ, không thuộc bản ghi điểm."""
        await self._ghi_diem_khi_db_hong()
        viet = AsyncMock(return_value={"code": "DS-1"})
        with patch.object(score_service.store, "record", viet):
            await score_outbox.ghi_bu()
        ban_ghi = viet.await_args.args[0]
        self.assertNotIn("ghi_luc", ban_ghi)
        self.assertNotIn("ly_do_hoan", ban_ghi)

    async def test_nhieu_lan_hong_thi_xep_hang(self):
        for _ in range(3):
            await self._ghi_diem_khi_db_hong()
        self.assertEqual(len(score_outbox.dang_cho()), 3)

    def test_dong_hong_dinh_dang_khong_lam_gay_ca_so(self):
        """Một dòng hỏng không được làm mất những dòng còn lại."""
        self.duong.parent.mkdir(parents=True, exist_ok=True)
        self.duong.write_text(
            json.dumps({"code": "DS-1", "points": 5}, ensure_ascii=False)
            + "\n{ dong hong\n"
            + json.dumps({"code": "DS-2", "points": 2}, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        cho = score_outbox.dang_cho()
        self.assertEqual([d["code"] for d in cho], ["DS-1", "DS-2"])

    def test_chua_co_tep_thi_tra_rong_chu_khong_no(self):
        self.assertEqual(score_outbox.dang_cho(), [])

    async def test_so_cho_rong_thi_ghi_bu_khong_cham_database(self):
        goi = AsyncMock()
        with patch.object(score_service.store, "record", goi):
            ket = await score_outbox.ghi_bu()
        goi.assert_not_awaited()
        self.assertEqual(ket["cho"], 0)


class GhiBuLucKhoiDongTests(unittest.TestCase):
    """Khởi động là thời điểm đúng để bù: database vừa được kiểm tra kết nối."""

    def test_bo_kiem_thu_khong_dung_thu_muc_storage_that(self):
        """Chạy trong container cũng không được ghi điểm giả vào volume runtime."""
        from app.core.config import BACKEND_DIR, settings

        self.assertNotEqual(
            pathlib.Path(settings.storage_path).resolve(),
            (BACKEND_DIR / "storage").resolve(),
        )

    def test_main_goi_ghi_bu_trong_lifespan(self):
        import ast

        nguon = (
            pathlib.Path(__file__).resolve().parent.parent / "main.py"
        ).read_text(encoding="utf-8")
        cay = ast.parse(nguon)
        ham = next(
            n
            for n in ast.walk(cay)
            if isinstance(n, ast.AsyncFunctionDef) and n.name == "lifespan"
        )
        goi = {
            n.func.attr
            for n in ast.walk(ham)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        }
        self.assertIn("ghi_bu", goi)

    def test_su_co_khi_ghi_bu_khong_lam_app_khong_len(self):
        """Sổ chờ vẫn còn nguyên; lần khởi động sau thử tiếp. Không đáng để app chết."""
        nguon = (
            pathlib.Path(__file__).resolve().parent.parent / "main.py"
        ).read_text(encoding="utf-8")
        i = nguon.index("ghi_bu")
        khoi = nguon[max(0, i - 400) : i + 300]
        self.assertIn("try:", khoi)
        self.assertIn("except", khoi)


if __name__ == "__main__":
    unittest.main()
