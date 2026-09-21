"""Kiểm thử bộ phân loại ý định.

Bản cũ so chuỗi con trên câu đã bỏ dấu, nên một tiếng nằm lọt trong tiếng khác
vẫn tính là khớp: "phí" trong "phía", "khoản" trong "khoảng". Đo trên mười câu
thì sai bốn. Nay so theo **tiếng trọn vẹn**.

Lớp `GioiHanTests` ghi lại phần **không** chữa được, và cố ý khẳng định hành vi
sai đó. Không phải để chấp nhận nó, mà để người sau đọc là biết ngay: đây là giới
hạn của việc phân loại bằng từ khóa, sửa nó phải đổi cách làm chứ không phải siết
thêm quy tắc so khớp.
"""
import io
import contextlib
import unittest

from app.conversation.intent_classifier import INTENT_PATTERNS, classify


def phan_loai(query: str) -> str:
    """Gọi `classify` mà không để log rác ra màn hình kiểm thử."""
    with contextlib.redirect_stdout(io.StringIO()):
        return classify(query)


class KhongConKhopChuoiConTests(unittest.TestCase):
    """Những ca bản cũ phân loại sai vì một tiếng lọt trong tiếng khác."""

    def test_phia_khong_con_bi_hieu_la_phi(self):
        self.assertEqual(phan_loai("Công ty ở phía bắc có chi nhánh không?"), "chung")

    def test_khoang_khong_con_bi_hieu_la_khoan(self):
        """"khoảng" là từ chỉ mức độ, "khoản" là tiền — hai nghĩa khác hẳn."""
        self.assertEqual(phan_loai("Chi phí khoảng bao nhiêu tiền?"), "chi_phi")

    def test_vay_khong_con_bi_hieu_la_vay_muon(self):
        self.assertEqual(phan_loai("Vậy à, thế còn điều kiện sức khỏe?"), "dieu_kien")


class PhanLoaiDungTests(unittest.TestCase):
    def test_cac_y_dinh_thuong_gap(self):
        cases = [
            ("Lương tháng bao nhiêu?", "luong_thuong"),
            ("Đặt lịch tư vấn giúp tôi", "booking"),
            ("Hồ sơ gồm những giấy tờ gì?", "quy_trinh"),
            ("Ký túc xá có mất phí không?", "ky_tuc_xa"),
            ("Phỏng vấn đơn hàng thế nào?", "phong_van"),
            ("Học tiếng Nhật ở đâu?", "hoc_tap"),
        ]
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(phan_loai(query), expected)

    def test_tien_coc_thuoc_nhom_chi_phi(self):
        """Câu này từng bị xếp vào quy_trinh chỉ vì hai chữ "bắt đầu"."""
        self.assertEqual(phan_loai("Khi bắt đầu thì tiền cọc là bao nhiêu?"), "chi_phi")

    def test_cau_khong_co_tu_khoa_nao_thi_la_chung(self):
        self.assertEqual(phan_loai("Chào bạn"), "chung")

    def test_chuoi_rong(self):
        self.assertEqual(phan_loai(""), "chung")


class BangTuKhoaTests(unittest.TestCase):
    def test_khong_co_tu_khoa_nao_bi_viet_lap(self):
        """Từ khóa lặp làm câu chứa nó được cộng hai điểm thay vì một."""
        for intent, keywords in INTENT_PATTERNS.items():
            with self.subTest(intent=intent):
                self.assertEqual(
                    len(keywords), len(set(keywords)), f"nhóm {intent} có từ khóa lặp"
                )


class GioiHanTests(unittest.TestCase):
    """Phần so khớp theo tiếng trọn vẹn **không** chữa được.

    Ở cả hai câu dưới đây, tiếng gây nhầm là một tiếng có thật trong câu, chỉ
    mang nghĩa khác. Không có quy tắc so khớp nào phân biệt được hai nghĩa đó —
    muốn đúng thì phải đổi cách phân loại, không phải siết thêm quy tắc.
    """

    def test_tuoi_tre_van_bi_hieu_la_hoi_dieu_kien(self):
        self.assertEqual(phan_loai("Tuổi trẻ có nên đi không?"), "dieu_kien")

    def test_luong_thien_van_bi_hieu_la_hoi_luong(self):
        self.assertEqual(phan_loai("Tôi muốn sống lương thiện bên Nhật"), "luong_thuong")


if __name__ == "__main__":
    unittest.main()
