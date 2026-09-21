"""Kiểm thử lá chắn số điện thoại trong câu trả lời của chatbot.

Chatbot nói gì thì khách tin nấy. Một số điện thoại do mô hình bịa ra mà lọt ra
ngoài là khách gọi cho người lạ, tưởng đang gọi công ty — nên đây là ca kiểm thử
về an toàn, không phải về chất lượng câu chữ.

Bản trước tắt hẳn lá chắn khi ý định là `lead`. Nhóm `ThayNgoaiLeTheoYDinh` giữ
cho lỗi đó không quay lại: nó kiểm rằng **ý định không còn ảnh hưởng gì** tới
việc chặn hay không.
"""
import unittest

from app.conversation.fallback_messages import SUPPORT_PHONE
from app.conversation.response_validator import FALLBACK, validate


LA = "0912345678"
DAI = "Đây là một câu trả lời đủ dài để qua được ngưỡng độ dài tối thiểu. "


class SoDienThoaiLaTests(unittest.TestCase):
    def test_chan_so_la(self):
        ok, answer = validate(DAI + f"Bạn gọi {LA} nhé.")
        self.assertFalse(ok)
        self.assertEqual(answer, FALLBACK)

    def test_cho_qua_so_hotline(self):
        ok, answer = validate(DAI + f"Bạn gọi {SUPPORT_PHONE} nhé.")
        self.assertTrue(ok)
        self.assertIn(SUPPORT_PHONE, answer)

    def test_hotline_viet_lien_khong_dau_cham(self):
        lien = SUPPORT_PHONE.replace(".", "")
        ok, _ = validate(DAI + f"Số của trung tâm là {lien}.")
        self.assertTrue(ok)

    def test_so_khach_vua_nhan_thi_duoc_nhac_lai(self):
        """Đúng trường hợp mà ngoại lệ cũ muốn bảo vệ — nay xử lý chính xác."""
        ok, answer = validate(
            DAI + f"Mình đã ghi nhận số {LA} của bạn.",
            user_message=f"Số của em là {LA}, anh gọi lại giúp em",
        )
        self.assertTrue(ok)
        self.assertIn(LA, answer)

    def test_so_khach_nhan_co_khoang_trang_van_khop(self):
        ok, _ = validate(
            DAI + "Mình đã ghi nhận số 0912345678 của bạn.",
            user_message="Số em là 0912 345 678 nhé",
        )
        self.assertTrue(ok)

    def test_van_chan_so_khac_du_khach_co_nhan_mot_so(self):
        """Khách cho số của mình không có nghĩa là bot được bịa thêm số khác."""
        ok, _ = validate(
            DAI + "Bạn gọi thêm 0988777666 để gặp bộ phận khác.",
            user_message=f"Số của em là {LA}",
        )
        self.assertFalse(ok)


class ThayNgoaiLeTheoYDinhTests(unittest.TestCase):
    """Ý định không còn được phép tắt lá chắn, dù là ý định nào."""

    def test_moi_y_dinh_deu_chan_so_la(self):
        for intent in ("chung", "lead", "booking", "chi_phi", "quy_trinh"):
            with self.subTest(intent=intent):
                ok, _ = validate(DAI + f"Gọi {LA} nhé.", intent)
                self.assertFalse(ok, f"ý định '{intent}' không được tắt lá chắn")

    def test_y_dinh_lead_van_cho_qua_hotline(self):
        ok, _ = validate(DAI + f"Gọi {SUPPORT_PHONE} nhé.", "lead")
        self.assertTrue(ok)


class KhongCatNhamDaySoTests(unittest.TestCase):
    """Chuỗi số dài không phải số điện thoại thì không được coi là số điện thoại."""

    def test_nam_thang_dung_canh_nhau_khong_bi_ghep(self):
        ok, _ = validate(DAI + "Chương trình bắt đầu từ năm 2026 và kéo dài 3 năm.")
        self.assertTrue(ok)

    def test_so_tien_khong_bi_nham_la_so_dien_thoai(self):
        ok, _ = validate(DAI + "Tổng chi phí là 90.000.000 đồng cho cả chương trình.")
        self.assertTrue(ok)

    def test_van_bat_duoc_so_la_nam_giua_cau_toan_so(self):
        ok, _ = validate(DAI + "Năm 2026, bạn gọi 0912345678 để biết thêm.")
        self.assertFalse(ok)


class CacKiemTraKhacTests(unittest.TestCase):
    def test_cau_qua_ngan_bi_chan(self):
        ok, answer = validate("Vâng ạ.")
        self.assertFalse(ok)
        self.assertEqual(answer, FALLBACK)

    def test_loi_qua_tai_tra_cau_rieng(self):
        from app.conversation.response_validator import RATE_LIMIT_FALLBACK

        ok, answer = validate("Lỗi Gemini: 429 RESOURCE_EXHAUSTED quota exceeded")
        self.assertFalse(ok)
        self.assertEqual(answer, RATE_LIMIT_FALLBACK)


if __name__ == "__main__":
    unittest.main()
