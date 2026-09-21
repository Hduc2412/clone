"""Kiểm thử cách chọn đoạn đưa vào ngữ cảnh.

Bản cũ dùng một ngưỡng tuyệt đối duy nhất (0,65). Điểm của cả kho lại nằm gọn
trong dải hẹp 0,56–0,73, nên con số đó cắt ngang giữa vùng có nghĩa: cùng một câu
hỏi, gõ có dấu thì đoạn đúng được 0,72 và lọt, gõ không dấu thì còn 0,64 và bị
loại — bot trả lời "không có thông tin" về đúng bài mang tên câu hỏi.

Nay dùng hai điều kiện đi cùng nhau: một **sàn tuyệt đối** để chặn câu ngoài phạm
vi, và một **dải tương đối** để quyết định lấy bao nhiêu đoạn. Thiếu điều kiện nào
cũng hỏng, theo hai kiểu ngược nhau — hai lớp dưới đây giữ cả hai.
"""
import unittest

from app.rag.retriever import MIN_TOP_SCORE, RELATIVE_BAND, select


class Diem:
    """Bản giả của một điểm Qdrant, chỉ cần `score`."""

    def __init__(self, score: float, title: str = ""):
        self.score = score
        self.payload = {"title": title}


class SanTuyetDoiTests(unittest.TestCase):
    """Chặn câu ngoài phạm vi — nếu thiếu, bot có nguyên liệu để bịa."""

    def test_doan_dau_qua_thap_thi_khong_lay_gi(self):
        points = [Diem(0.5866), Diem(0.5864), Diem(0.5859)]
        self.assertEqual(select(points), [])

    def test_cau_ngoai_pham_vi_co_nhieu_doan_sat_nhau_van_bi_chan(self):
        """Hỏi "giá bitcoin": tám đoạn chênh nhau chưa tới 0,002 điểm.

        Chỉ dùng dải tương đối thì cả tám lọt vào ngữ cảnh — đúng tình huống dễ
        sinh ra câu bịa nhất.
        """
        points = [Diem(0.5866 - i * 0.0002) for i in range(8)]
        self.assertEqual(select(points), [])

    def test_doan_dau_vua_du_san_thi_duoc_lay(self):
        points = [Diem(MIN_TOP_SCORE)]
        self.assertEqual(len(select(points)), 1)


class DaiTuongDoiTests(unittest.TestCase):
    """Quyết định lấy bao nhiêu đoạn, không phụ thuộc mức điểm tuyệt đối."""

    def test_giu_doan_dung_tung_bi_nguong_cu_cat_mat(self):
        """Ca thật: "Quy trinh dong phi don dieu duong nhu the nao?".

        Bài mang đúng tên câu hỏi xếp hạng ba với 0,6423 — ngưỡng cũ 0,65 cắt
        mất, nên bot nói là không có thông tin về chính bài đó.
        """
        points = [
            Diem(0.6644, "Quy trình đi Nhật đơn điều dưỡng"),
            Diem(0.6642, "Cách đăng ký đơn hàng điều dưỡng"),
            Diem(0.6423, "Quy trình đóng phí đơn điều dưỡng"),
        ]
        titles = [point.payload["title"] for point in select(points)]
        self.assertIn("Quy trình đóng phí đơn điều dưỡng", titles)

    def test_bo_doan_tut_lai_qua_xa(self):
        points = [Diem(0.73), Diem(0.72), Diem(0.60)]
        self.assertEqual(len(select(points)), 2)

    def test_doan_dung_bang_mep_dai_thi_van_giu(self):
        points = [Diem(0.70), Diem(0.70 - RELATIVE_BAND)]
        self.assertEqual(len(select(points)), 2)

    def test_chi_mot_doan_vuot_troi_thi_chi_lay_mot(self):
        points = [Diem(0.73), Diem(0.64), Diem(0.63)]
        self.assertEqual(len(select(points)), 1)


class TruongHopBienTests(unittest.TestCase):
    def test_khong_co_diem_nao(self):
        self.assertEqual(select([]), [])

    def test_khong_doi_thu_tu_xep_hang(self):
        points = [Diem(0.73, "A"), Diem(0.72, "B"), Diem(0.71, "C")]
        self.assertEqual([p.payload["title"] for p in select(points)], ["A", "B", "C"])


if __name__ == "__main__":
    unittest.main()
