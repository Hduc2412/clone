"""Nội dung khối điều kiện và khối đơn — những câu nói với khách về tiền và sức khỏe.

Hai module này trước nay **không có ca kiểm thử nào của riêng mình**. Phát hiện
ngày 29/09/2026 khi soát lại bộ kiểm thử: chúng chỉ được chạy qua một cách tình
cờ, từ ca kiểm thử của `advice`, và không ca nào khẳng định nội dung.

Đó là khoảng trống đáng lo nhất trong cả bộ, vì hai lý do.

**Thứ nhất, đây không phải chữ trang trí.** Bot tư vấn không đọc website; nó chỉ
biết đúng những gì nằm trong bốn khối dữ liệu đưa vào. Nên mỗi dòng ở đây là một
câu bot có thể nói với ứng viên về tiền của họ và về sức khỏe của họ.

**Thứ hai, mỗi dòng dưới đây tồn tại vì một lỗi đã đo được.** Không phải phòng xa:

- Dòng *"KHÔNG mất tiền"*: đo ngày 28/09, bot suy đoán "chi phí khám sẽ được
  thanh toán tại bệnh viện được chỉ định" — ngụ ý khách phải trả, trong khi công
  ty ghi rõ ngược lại. Xóa dòng ấy đi thì bot lặng lẽ quay về đoán, và không ca
  kiểm thử nào báo.
- Câu nhắc *danh sách bệnh chưa đầy đủ*: nguồn dùng chữ "các bệnh truyền nhiễm
  **như**". Nêu ba bệnh trơ trọi là để khách hiểu rằng không có ba bệnh ấy thì
  chắc chắn đạt — một câu mà buổi khám có thể lật lại.
- Khối *LƯU Ý VỀ CHI PHÍ* trong khối đơn: đo ngày 27/09, mô hình ghép hai con số
  từ hai nguồn khác nhau thành "Tổng 110.000.000đ, trong đó học phí 35.000.000đ".

Bộ này khóa lại từng dòng đó.
"""
import unittest

from app.consultation import eligibility, order_context


DON_MAU = {
    "code": "DH-0001",
    "title": "Điều dưỡng viện dưỡng lão Tokyo",
    "employer_name": "Viện dưỡng lão Sakura",
    "employer_type": "vien_duong_lao",
    "program": "tokutei_ginou",
    "prefecture": "Tokyo",
    # `deadline` nằm ở CẤP NGOÀI, không trong `requirements`. Cả `engine.py` lẫn
    # `order_context.py` đều đọc `order["deadline"]`. Đặt sai chỗ thì khối chữ
    # lặng lẽ thiếu dòng hạn nộp — bản nháp đầu của ca kiểm thử này mắc đúng lỗi
    # đó, và nó đỏ vì fixture sai chứ không vì mã sai.
    "deadline": "2026-12-15",
    "requirements": {
        "japanese_required": "N4",
        "education_required": "cao_dang",
        "experience_min": 0,
        "age_min": 20,
        "age_max": 35,
        "gender_pref": "khong_yeu_cau",
    },
    "reference": {
        "salary_min": 195000,
        "salary_max": 215000,
        "allowances": ["Hỗ trợ ký túc xá"],
        "interview_date": "2026-10-28",
        "departure_expected": "2027-03",
        "highlights": ["Cơ sở mới xây"],
    },
}


class KhoiSucKhoeTests(unittest.TestCase):
    def test_noi_ro_kham_khong_mat_tien(self):
        """Đo 28/09: thiếu dòng này, bot nói khách phải tự trả tiền khám."""
        khoi = eligibility.render_suc_khoe()
        self.assertIn("KHÔNG mất tiền", khoi)

    def test_neu_ten_ba_benh_nguon_co_ghi(self):
        khoi = eligibility.render_suc_khoe()
        for benh in eligibility.BENH_LOAI_TRU:
            self.assertIn(benh, khoi)

    def test_luon_kem_cau_nhac_danh_sach_chua_day_du(self):
        """Nguồn dùng chữ "như", nên ba bệnh ấy không phải danh sách đóng.

        Nêu trơ trọi là để khách hiểu rằng không có ba bệnh ấy thì chắc chắn đạt.
        """
        khoi = eligibility.render_suc_khoe()
        self.assertIn(eligibility.LOI_NHAC, khoi)

    def test_khong_tu_ket_luan_dat_hay_khong_dat_ve_suc_khoe(self):
        """Kết luận là của buổi khám, không phải của phần mềm.

        Chấm "đạt sức khỏe" dựa trên lời khai rồi để khách trượt ở phòng khám thì
        tệ hơn không chấm gì: khách mất tiền đặt cọc và mất niềm tin cùng lúc.
        """
        khoi = eligibility.render_suc_khoe().casefold()
        for cum in ("bạn đạt", "bạn không đạt", "đủ điều kiện sức khỏe",
                    "chắc chắn đi được"):
            self.assertNotIn(cum, khoi)
        self.assertIn("khám", khoi)


class KhoiMucNenTests(unittest.TestCase):
    def test_du_nam_dong_dieu_kien_nen(self):
        khoi = eligibility.render_muc_nen()
        for dk in eligibility.MUC_NEN:
            self.assertIn(dk.tieu_chi, khoi)
            self.assertIn(dk.yeu_cau, khoi)

    def test_noi_dung_tuoi_18_den_40(self):
        self.assertIn("18", eligibility.render_muc_nen())
        self.assertIn("40", eligibility.render_muc_nen())

    def test_noi_ro_khong_yeu_cau_bang_cap(self):
        """Nói ngược lại là loại oan người đủ điều kiện ngay ở câu đầu tiên."""
        self.assertIn("Không yêu cầu bằng cấp", eligibility.render_muc_nen())

    def test_co_nguon_dan_trong_as_dict(self):
        """Mọi con số nói với khách phải truy được về một trang của công ty."""
        self.assertTrue(eligibility.as_dict()["source_url"].startswith("https://"))


class KhoiDonTests(unittest.TestCase):
    def test_chua_chon_don_thi_khoi_rong(self):
        self.assertEqual(order_context.render(None), "")

    def test_tach_ro_dieu_kien_bat_buoc_va_thong_tin_tham_khao(self):
        """Ranh giới này quyết định ai bị loại, nên phải hiện rõ trong chính khối chữ.

        Lương và chi phí không bao giờ loại ai. Trộn hai nhóm vào một danh sách là
        mời mô hình dùng mức lương làm điều kiện.
        """
        khoi = order_context.render(DON_MAU)
        self.assertIn("Điều kiện bắt buộc", khoi)
        self.assertIn("Thông tin tham khảo", khoi)
        self.assertLess(
            khoi.index("Điều kiện bắt buộc"),
            khoi.index("Thông tin tham khảo"),
            "điều kiện bắt buộc phải đứng trước phần tham khảo",
        )
        self.assertIn("không mục nào trong đây làm ứng viên bị loại", khoi)

    def test_co_ma_don_va_khong_moi_so_sanh_voi_don_khac(self):
        khoi = order_context.render(DON_MAU)
        self.assertIn("DH-0001", khoi)
        self.assertIn("không so sánh với đơn khác", khoi)

    def test_han_nop_hien_dang_ngay_thang_nam_viet(self):
        """`2026-12-15` đọc lên cho khách là một con số vô nghĩa."""
        self.assertIn("15/12/2026", order_context.render(DON_MAU))

    def test_khong_co_chi_phi_thi_khong_co_khoi_luu_y(self):
        """Đơn mẫu không có chi phí — khối lưu ý chỉ xuất hiện khi thật sự có số.

        Nêu lưu ý về một con số không tồn tại là làm khách tưởng có một khoản phí
        nào đó chưa được nói ra.
        """
        self.assertNotIn("LƯU Ý VỀ CHI PHÍ", order_context.render(DON_MAU))

    def test_co_chi_phi_thi_phai_noi_ro_chua_biet_quan_he_voi_hoc_phi(self):
        """Đo 27/09: mô hình ghép hai con số từ hai nguồn thành một câu sai —
        "Tổng 110.000.000đ, trong đó học phí 35.000.000đ"."""
        don = {
            **DON_MAU,
            "reference": {**DON_MAU["reference"], "cost_total_vnd": 110_000_000},
        }
        khoi = order_context.render(don)
        self.assertIn("LƯU Ý VỀ CHI PHÍ", khoi)
        self.assertIn("Chưa rõ", khoi)
        self.assertIn("không được cộng hay trừ", khoi)

    def test_khoi_tat_dinh(self):
        """Cùng một đơn phải ra cùng một khối chữ, không phụ thuộc thứ tự khóa."""
        dao = {k: DON_MAU[k] for k in reversed(list(DON_MAU))}
        self.assertEqual(order_context.render(DON_MAU), order_context.render(dao))


if __name__ == "__main__":
    unittest.main()
