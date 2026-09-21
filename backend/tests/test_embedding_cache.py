"""Kiểm thử nhớ đệm vector câu hỏi.

Mỗi lượt chat đi ra Internet hai lần: nhúng câu hỏi (~700 ms) rồi sinh chữ
(~2400 ms). Việc nhúng cho cùng một câu hỏi luôn ra cùng một kết quả, nên gọi
lại là trả tiền và trả thời gian cho một phép tính đã có đáp án.

Ba thứ được canh ở đây, và cả ba đều là kiểu lỗi âm thầm:

1. **Nhớ nhầm giữa hai loại tác vụ.** Cùng một đoạn chữ nhúng kiểu QUERY và kiểu
   DOCUMENT cho ra hai vector khác nhau. Lấy nhầm thì kết quả tìm kiếm tệ đi mà
   không có lỗi nào được ném ra.
2. **Người gọi sửa vào danh sách trả về.** Nếu trả thẳng vật trong đệm, một chỗ
   sửa nhầm sẽ làm hỏng kết quả của một câu hỏi khác hẳn.
3. **Nhớ cả lần hỏng.** Một trục trặc mạng thoáng qua sẽ biến thành câu hỏi đó
   hỏng vĩnh viễn cho tới khi khởi động lại.
"""
import unittest
from unittest.mock import patch

from app.llm import gemini


def tra_ve(vector):
    return {"embedding": {"values": vector}}


class DemHoatDongTests(unittest.TestCase):
    def setUp(self):
        gemini.clear_embedding_cache()

    def test_goi_lan_hai_khong_ra_mang(self):
        with patch.object(gemini, "_post_with_retry", return_value=tra_ve([0.1, 0.2])) as goi:
            gemini.create_embedding("chi phí bao nhiêu")
            gemini.create_embedding("chi phí bao nhiêu")
        self.assertEqual(goi.call_count, 1)

    def test_bo_khoang_trang_thua_van_trung_dem(self):
        with patch.object(gemini, "_post_with_retry", return_value=tra_ve([0.1])) as goi:
            gemini.create_embedding("chi phí bao nhiêu")
            gemini.create_embedding("  chi phí bao nhiêu\n")
        self.assertEqual(goi.call_count, 1)

    def test_cau_khac_nhau_thi_goi_rieng(self):
        with patch.object(gemini, "_post_with_retry", return_value=tra_ve([0.1])) as goi:
            gemini.create_embedding("chi phí bao nhiêu")
            gemini.create_embedding("điều kiện là gì")
        self.assertEqual(goi.call_count, 2)

    def test_hoa_thuong_khac_nhau_la_hai_cau_khac_nhau(self):
        """Chữ khác nhau thì vector khác nhau — không được gộp làm một."""
        with patch.object(gemini, "_post_with_retry", return_value=tra_ve([0.1])) as goi:
            gemini.create_embedding("Chi phí")
            gemini.create_embedding("chi phí")
        self.assertEqual(goi.call_count, 2)


class KhongLanLoaiTacVuTests(unittest.TestCase):
    """Cùng đoạn chữ, hai kiểu tác vụ — hai vector khác nhau, không được lẫn."""

    def setUp(self):
        gemini.clear_embedding_cache()

    def test_query_va_document_khong_dung_chung_o_dem(self):
        with patch.object(gemini, "_post_with_retry") as goi:
            goi.side_effect = [tra_ve([1.0]), tra_ve([2.0])]
            q = gemini.create_embedding("quy trình đóng phí", gemini.TASK_QUERY)
            d = gemini.create_embedding("quy trình đóng phí", gemini.TASK_DOCUMENT)
        self.assertEqual(goi.call_count, 2)
        self.assertNotEqual(q, d)

    def test_moi_loai_van_duoc_nho_rieng(self):
        with patch.object(gemini, "_post_with_retry") as goi:
            goi.side_effect = [tra_ve([1.0]), tra_ve([2.0])]
            gemini.create_embedding("x", gemini.TASK_QUERY)
            gemini.create_embedding("x", gemini.TASK_DOCUMENT)
            gemini.create_embedding("x", gemini.TASK_QUERY)
            gemini.create_embedding("x", gemini.TASK_DOCUMENT)
        self.assertEqual(goi.call_count, 2)


class KhongDeNguoiGoiLamHongDemTests(unittest.TestCase):
    def setUp(self):
        gemini.clear_embedding_cache()

    def test_sua_vao_ban_tra_ve_khong_anh_huong_dem(self):
        with patch.object(gemini, "_post_with_retry", return_value=tra_ve([0.1, 0.2])):
            lan_dau = gemini.create_embedding("chi phí")
            lan_dau[0] = 999.0
            lan_sau = gemini.create_embedding("chi phí")
        self.assertEqual(lan_sau, [0.1, 0.2])


class KhongNhoLanHongTests(unittest.TestCase):
    def setUp(self):
        gemini.clear_embedding_cache()

    def test_loi_khong_duoc_nho_lai(self):
        loi = {"error": {"message": "mat ket noi"}}
        with patch.object(gemini, "_post_with_retry") as goi:
            goi.side_effect = [loi, tra_ve([0.5])]
            hong = gemini.create_embedding("chi phí")
            lai = gemini.create_embedding("chi phí")
        self.assertIsNone(hong)
        self.assertEqual(lai, [0.5], "lần sau phải thử lại thật, không trả về lỗi cũ")
        self.assertEqual(goi.call_count, 2)


class GioiHanKichThuocTests(unittest.TestCase):
    def setUp(self):
        gemini.clear_embedding_cache()

    def test_khong_phinh_vo_han(self):
        with patch.object(gemini, "_post_with_retry", return_value=tra_ve([0.1])):
            for i in range(gemini._CACHE_SIZE + 50):
                gemini.create_embedding(f"câu hỏi số {i}")
        self.assertEqual(len(gemini._embedding_cache), gemini._CACHE_SIZE)

    def test_bo_muc_cu_nhat_truoc(self):
        with patch.object(gemini, "_post_with_retry", return_value=tra_ve([0.1])):
            for i in range(gemini._CACHE_SIZE):
                gemini.create_embedding(f"câu {i}")
            # Dùng lại câu đầu tiên rồi đẩy thêm một câu mới: câu đầu phải sống,
            # câu thứ hai mới là câu bị bỏ.
            gemini.create_embedding("câu 0")
            gemini.create_embedding("câu mới")
        keys = {key[0] for key in gemini._embedding_cache}
        self.assertIn("câu 0", keys)
        self.assertNotIn("câu 1", keys)


if __name__ == "__main__":
    unittest.main()
