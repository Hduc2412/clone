"""Kiểm thử các quy tắc trong prompt.

Không kiểm được mô hình có nghe lời hay không — việc đó phải chạy thật, và đó là
việc của `scripts/nghiem_thu_chatbot.py`. Cái kiểm được ở đây là **prompt có thật
sự mang những quy tắc đó xuống hay không**, và câu từ chối chuẩn có khớp với bộ
nhận diện của hệ thống hay không.

Nghe như kiểm thử hình thức, nhưng ba quy tắc dưới đây đều sinh ra từ câu trả lời
hỏng đo được trên dữ liệu thật. Ai đó rút gọn prompt sau này mà bỏ nhầm một dòng
thì lỗi cũ quay lại, và nó quay lại **âm thầm** — câu trả lời vẫn trôi chảy, chỉ
là sai thẩm quyền hoặc thiếu phương án.
"""
import unittest

from app.conversation.fallback_messages import (
    ALL_FALLBACKS,
    MODEL_REFUSAL,
    looks_like_refusal,
)
from app.rag.prompt_builder import build_context, build_prompt


class CauTuChoiChuanTests(unittest.TestCase):
    """Câu từ chối phải khớp chính xác với bộ nhận diện, không phải dò gần đúng."""

    def test_he_thong_nhan_ra_cau_tu_choi_chuan(self):
        self.assertTrue(looks_like_refusal(MODEL_REFUSAL))

    def test_nam_trong_danh_sach_cau_du_phong(self):
        self.assertIn(MODEL_REFUSAL, ALL_FALLBACKS)

    def test_prompt_yeu_cau_dung_nguyen_van_cau_do(self):
        prompt = build_prompt("nội dung nào đó", "câu hỏi nào đó")
        self.assertIn(MODEL_REFUSAL, prompt)

    def test_cau_tu_choi_co_so_hotline(self):
        from app.conversation.fallback_messages import SUPPORT_PHONE

        self.assertIn(SUPPORT_PHONE, MODEL_REFUSAL)


class BaQuyTacSinhTuLoiThatTests(unittest.TestCase):
    """Mỗi quy tắc ứng với một câu trả lời hỏng đã quan sát được."""

    def setUp(self):
        self.prompt = build_prompt("nội dung tài liệu", "câu hỏi của khách")

    def test_cam_ket_luan_thay_nguoi_hoi(self):
        """Bot từng đáp "đúng vậy, bạn sẽ không đủ điều kiện" cho câu hỏi y tế."""
        self.assertIn("KHÔNG kết luận người hỏi đủ hay không", self.prompt)

    def test_bat_neu_du_cac_phuong_an(self):
        """Cùng câu hỏi từng nhận hai đáp án khác nhau vì mô hình chọn một phương án."""
        self.assertIn("nhiều phương án", self.prompt)

    def test_cam_doan_ket_qua_va_hua_chac_chan(self):
        self.assertIn("Không đoán kết quả phỏng vấn", self.prompt)

    def test_cam_so_sanh_va_tu_quang_cao(self):
        """Bot từng đáp "công ty DC là một lựa chọn tốt" cho câu hỏi so sánh."""
        self.assertIn("Không so sánh công ty DC với công ty khác", self.prompt)
        self.assertIn("tốt nhất", self.prompt)

    def test_cam_ket_luan_y_te(self):
        self.assertIn("Không đưa kết luận y tế", self.prompt)

    def test_con_giu_quy_tac_chi_dung_tai_lieu(self):
        self.assertIn("Chỉ dùng THÔNG TIN TỪ TÀI LIỆU", self.prompt)


class NoiGiamKhiTinKhongVuiTests(unittest.TestCase):
    """Cấm phán quyết thôi chưa đủ — phải dạy mô hình nói thế nào cho đúng mực.

    Người hỏi có thể vừa biết mình mang bệnh, hoặc đang lo mình quá tuổi. Một câu
    máy móc kiểu "bạn sẽ trượt" là thứ không ai nên nhận từ một cái máy, kể cả khi
    nội dung của nó đúng với tài liệu.
    """

    def setUp(self):
        self.prompt = build_prompt("nội dung tài liệu", "câu hỏi của khách")

    def test_co_vi_du_cach_noi_nen_dung(self):
        self.assertIn("chưa phù hợp với trường hợp này", self.prompt)

    def test_liet_ke_ro_nhung_cau_khong_duoc_viet(self):
        for cấm in ("bạn sẽ trượt", "bạn bị loại", "bạn không đủ điều kiện"):
            with self.subTest(cấm=cấm):
                self.assertIn(cấm, self.prompt)

    def test_cam_tu_ngu_phan_xet_ve_nguoi(self):
        self.assertIn("Không dùng từ mang tính phán xét về người", self.prompt)

    def test_luon_de_ngo_buoc_tiep_theo(self):
        self.assertIn("luôn mời trao đổi với nhân viên", self.prompt)


class CauTrucPromptTests(unittest.TestCase):
    def test_co_ca_ngu_canh_va_cau_hoi(self):
        prompt = build_prompt("ĐOẠN TÀI LIỆU", "CÂU HỎI CỦA KHÁCH")
        self.assertIn("ĐOẠN TÀI LIỆU", prompt)
        self.assertIn("CÂU HỎI CỦA KHÁCH", prompt)

    def test_co_lich_su_thi_khong_chao_lai(self):
        prompt = build_prompt("nội dung", "câu hỏi", history_text="Khach: xin chào")
        self.assertIn("Không mở đầu bằng lời chào", prompt)
        self.assertIn("Khach: xin chào", prompt)

    def test_khong_co_lich_su_thi_duoc_chao(self):
        prompt = build_prompt("nội dung", "câu hỏi")
        self.assertIn("Chỉ chào ngắn gọn", prompt)
        self.assertNotIn("LỊCH SỬ HỘI THOẠI", prompt)


class NgưCanhCoNguonTests(unittest.TestCase):
    """Mỗi đoạn trong ngữ cảnh phải kèm tiêu đề và đường dẫn gốc."""

    def test_moi_doan_kem_tieu_de_va_nguon(self):
        class Hit:
            def __init__(self, title, text, url):
                self.payload = {"title": title, "text": text, "url": url}

        context = build_context([
            Hit("Quy trình đóng phí", "nội dung một", "https://vi.du/a"),
            Hit("Điều kiện đi Nhật", "nội dung hai", "https://vi.du/b"),
        ])
        self.assertIn("[Quy trình đóng phí]", context)
        self.assertIn("(Nguồn: https://vi.du/a)", context)
        self.assertIn("[Điều kiện đi Nhật]", context)

    def test_khong_co_doan_nao_thi_ngu_canh_rong(self):
        self.assertEqual(build_context([]), "")


if __name__ == "__main__":
    unittest.main()
