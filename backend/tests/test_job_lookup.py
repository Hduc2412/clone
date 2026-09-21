"""Kiểm thử việc tra danh mục đơn khi câu hỏi nhắc tới địa điểm.

Ca sinh ra module này: *"Học đơn ở Kaigo nhưng tôi muốn đi Tokyo thì có đi được
không?"* — hệ thống có sẵn đơn ở Tokyo trong danh mục, nhưng chatbot chỉ đọc kho
tri thức nên trả lời chung chung. Những lớp dưới đây giữ ba thứ dễ hỏng nhất:
việc dò tỉnh phải **tất định**, danh sách phải **chỉ gồm đơn công khai**, và câu
chữ phải đúng cho cả hai kiểu hỏi (theo tỉnh và theo vùng).
"""
import unittest
from unittest.mock import AsyncMock, patch

from app.db import job_orders as store
from app.rag import job_lookup


def don(code: str, prefecture: str, **extra) -> dict:
    data = {
        "code": code,
        "title": f"Điều dưỡng {prefecture}",
        "prefecture": prefecture,
        "requirements": {"japanese_required": "N4", "age_min": 20, "age_max": 35},
        "deadline": "2026-11-30",
    }
    data.update(extra)
    return data


class DoDiaDiemTests(unittest.TestCase):
    """Dò bằng bảng danh mục, không hỏi mô hình — nên phải lặp lại y hệt mỗi lần."""

    def test_nhac_tinh_thi_suy_ra_luon_vung(self):
        self.assertEqual(
            job_lookup.detect_location("tôi muốn đi Tokyo thì có đi được không"),
            ("Tokyo", "kanto"),
        )

    def test_go_khong_dau_va_viet_thuong_van_do_duoc(self):
        self.assertEqual(
            job_lookup.detect_location("co don nao o osaka khong")[0], "Osaka"
        )

    def test_nhac_vung_ma_khong_nhac_tinh(self):
        self.assertEqual(
            job_lookup.detect_location("vùng Kansai có đơn nào không"),
            (None, "kansai"),
        )

    def test_cau_khong_nhac_dia_diem_thi_khong_do_ra_gi(self):
        self.assertEqual(
            job_lookup.detect_location("chi phí đi Nhật hết bao nhiêu"),
            (None, None),
        )


class ChiLayDonCongKhaiTests(unittest.IsolatedAsyncioTestCase):
    """Đơn nháp hoặc đã đóng không được lọt ra ngoài qua đường chat."""

    async def test_truy_van_luon_kem_bo_loc_cong_khai(self):
        with patch.object(store, "list_job_orders", AsyncMock(return_value=[])) as goi:
            await job_lookup.find_orders("Tokyo", "kanto")

        self.assertEqual(goi.await_count, 2)
        for lan in goi.await_args_list:
            query = lan.args[0]
            for khoa, gia_tri in store.public_filter().items():
                self.assertEqual(query.get(khoa), gia_tri)
            # `public=True` chọn phép chiếu công khai: không lộ thông tin nội bộ
            # của đơn ra ngoài kể cả khi đơn đó đúng là đang tuyển.
            self.assertTrue(lan.kwargs["public"])

    async def test_don_cua_chinh_tinh_khong_bi_ke_lai_o_phan_cung_vung(self):
        async def tra(query, **kwargs):
            if query.get("prefecture"):
                return [don("DH-0001", "Tokyo")]
            return [don("DH-0001", "Tokyo"), don("DH-0003", "Saitama")]

        with patch.object(store, "list_job_orders", AsyncMock(side_effect=tra)):
            tai_tinh, cung_vung = await job_lookup.find_orders("Tokyo", "kanto")

        self.assertEqual([r["code"] for r in tai_tinh], ["DH-0001"])
        self.assertEqual([r["code"] for r in cung_vung], ["DH-0003"])


class CauChuTests(unittest.TestCase):
    """Khối chữ sinh bằng mã, nên sai chữ ở đây là sai trong mọi câu trả lời."""

    def test_co_don_tai_tinh_thi_ke_ra_kem_yeu_cau(self):
        block = job_lookup.render_block(
            "Tokyo", "kanto", [don("DH-0001", "Tokyo")], []
        )
        self.assertIn("Hiện có 1 đơn đang tuyển tại Tokyo", block)
        self.assertIn("DH-0001", block)
        self.assertIn("tiếng Nhật từ N4", block)
        self.assertIn("tuổi 20–35", block)

    def test_tinh_khong_co_don_thi_noi_thang_va_goi_y_lan_can(self):
        block = job_lookup.render_block(
            "Tokyo", "kanto", [], [don("DH-0003", "Saitama")]
        )
        self.assertIn("KHÔNG có đơn nào đang tuyển tại Tokyo", block)
        self.assertIn("Các đơn khác cùng vùng Kantō", block)

    def test_hoi_theo_vung_thi_khong_goi_la_don_khac(self):
        # Không có tỉnh nào để mà "khác": đây là toàn bộ danh sách của vùng.
        block = job_lookup.render_block(None, "kanto", [], [don("DH-0003", "Saitama")])
        self.assertIn("Các đơn đang tuyển ở vùng Kantō", block)
        self.assertNotIn("khác cùng vùng", block)

    def test_ca_vung_khong_con_don_nao(self):
        block = job_lookup.render_block("Tokyo", "kanto", [], [])
        self.assertIn("Không có đơn nào đang tuyển ở khu vực này", block)

    def test_luon_nhac_noi_lam_viec_khong_phu_thuoc_noi_hoc(self):
        # Ràng buộc nghiệp vụ nói thẳng, để mô hình không tự suy ra điều ngược lại.
        block = job_lookup.render_block("Tokyo", "kanto", [don("DH-0001", "Tokyo")], [])
        self.assertIn("không phụ thuộc nơi học tiếng", block)

    def test_khong_do_ra_dia_diem_thi_khoi_chu_rong(self):
        self.assertEqual(job_lookup.render_block(None, None, [], []), "")


class KhongChamDatabaseKhiKhongCanTests(unittest.IsolatedAsyncioTestCase):
    async def test_cau_khong_nhac_dia_diem_thi_khong_truy_van(self):
        with patch.object(store, "list_job_orders", AsyncMock()) as goi:
            block = await job_lookup.context_for("chi phí đi Nhật hết bao nhiêu")
        self.assertEqual(block, "")
        goi.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
