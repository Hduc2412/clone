"""Ghép lộ trình học — thuần, không cần database, không cần mạng.

Ca quan trọng nhất của bộ này không phải "ghép đúng" mà là **không bịa**:
`test_khong_noi_suy_khi_khong_co_duong` và `test_thieu_hoc_phi_mot_khoa_thi_khong_cong_tong`.
Hai ca đó canh đúng chỗ mà một con số sai sẽ thành lời hứa với người đang tính
chuyện vay tiền đi nước ngoài.
"""
import unittest

from app.learning import path


def khoa(code, level_from, level_to, months_min, months_max=None, tuition=None, package=None):
    return {
        "code": code,
        "title": f"Khóa {code}",
        "level_from": level_from,
        "level_to": level_to,
        "months_min": months_min,
        "months_max": months_max,
        "tuition_vnd": tuition,
        "package_total_vnd": package,
    }


# Đúng dữ liệu thật đọc được từ kho tri thức ngày 24/09: một khóa duy nhất,
# 6–7 tháng, 35 triệu là một chặng trong tổng 90 triệu.
KHOA_THAT = khoa("KH-0001", "chua_hoc", "N4", 6, 7, 35_000_000, 90_000_000)


class KhongCoDuongThiKhongBiaTests(unittest.TestCase):
    def test_khong_noi_suy_khi_khong_co_duong(self):
        """Có khóa chưa-học → N4, nhưng khách đang ở N5 và cần N3.

        Cái sai dễ mắc là suy "N5 là nửa đường của khóa kia nên N5 → N3 mất
        chừng đó tháng". Nghe hợp lý nhưng không có gì đỡ lưng.
        """
        ra = path.build([KHOA_THAT], level_from="N5", level_to="N3")
        self.assertIsNone(ra)

    def test_danh_muc_rong_thi_tra_rong(self):
        self.assertIsNone(path.build([], level_from="chua_hoc", level_to="N4"))

    def test_thieu_trinh_do_hien_tai_thi_tra_rong(self):
        """Hồ sơ chưa khai tiếng Nhật — chưa biết, không phải chưa học."""
        self.assertIsNone(path.build([KHOA_THAT], level_from=None, level_to="N4"))

    def test_thieu_trinh_do_don_yeu_cau_thi_tra_rong(self):
        self.assertIsNone(path.build([KHOA_THAT], level_from="chua_hoc", level_to=None))

    def test_ma_trinh_do_la_thi_tra_rong(self):
        self.assertIsNone(path.build([KHOA_THAT], level_from="N9", level_to="N4"))

    def test_da_du_trinh_do_thi_tra_rong(self):
        """Không phải lỗi — nhưng cũng không phải lộ trình. Dùng `can_skip` để biết."""
        self.assertIsNone(path.build([KHOA_THAT], level_from="N3", level_to="N4"))
        self.assertTrue(path.can_skip("N3", "N4"))


class GhepDungTests(unittest.TestCase):
    def test_mot_khoa_bac_duoc_thi_ra_dung_khoa_do(self):
        ra = path.build([KHOA_THAT], level_from="chua_hoc", level_to="N4")
        self.assertIsNotNone(ra)
        self.assertEqual([k["code"] for k in ra.courses], ["KH-0001"])
        self.assertEqual(ra.months_min, 6)
        self.assertEqual(ra.months_max, 7)
        self.assertEqual(ra.tuition_vnd, 35_000_000)
        self.assertEqual(ra.package_total_vnd, 90_000_000)
        self.assertFalse(ra.tuition_incomplete)

    def test_noi_hai_chang_thi_cong_don(self):
        so_cap = khoa("KH-0001", "chua_hoc", "N5", 4, 4, 20_000_000)
        len_n4 = khoa("KH-0002", "N5", "N4", 3, 4, 15_000_000)
        ra = path.build([so_cap, len_n4], level_from="chua_hoc", level_to="N4")
        self.assertEqual([k["code"] for k in ra.courses], ["KH-0001", "KH-0002"])
        self.assertEqual(ra.months_min, 7)
        self.assertEqual(ra.months_max, 8)
        self.assertEqual(ra.tuition_vnd, 35_000_000)

    def test_khoa_day_vuot_muc_can_van_dung_duoc(self):
        """Đơn cần N4 mà chỉ có khóa dạy tới N3 thì vẫn đủ điều kiện."""
        ra = path.build(
            [khoa("KH-0009", "chua_hoc", "N3", 10, 12, 50_000_000)],
            level_from="chua_hoc",
            level_to="N4",
        )
        self.assertEqual([k["code"] for k in ra.courses], ["KH-0009"])

    def test_chon_duong_it_thang_hon(self):
        nhanh = khoa("KH-0002", "chua_hoc", "N4", 6, 6, 35_000_000)
        cham_a = khoa("KH-0003", "chua_hoc", "N5", 5, 5, 20_000_000)
        cham_b = khoa("KH-0004", "N5", "N4", 5, 5, 20_000_000)
        ra = path.build([cham_a, cham_b, nhanh], level_from="chua_hoc", level_to="N4")
        self.assertEqual([k["code"] for k in ra.courses], ["KH-0002"])
        self.assertEqual(ra.months_min, 6)


class TatDinhTests(unittest.TestCase):
    def test_xao_tron_danh_muc_van_ra_cung_ket_qua(self):
        """Thứ tự bản ghi database trả về không được làm đổi lời tư vấn."""
        danh_muc = [
            khoa("KH-0003", "chua_hoc", "N5", 4, 4, 20_000_000),
            khoa("KH-0004", "N5", "N4", 3, 3, 15_000_000),
            khoa("KH-0005", "N4", "N3", 5, 5, 25_000_000),
        ]
        chuan = path.build(danh_muc, level_from="chua_hoc", level_to="N3")
        for xoay in range(len(danh_muc)):
            dao = danh_muc[xoay:] + danh_muc[:xoay]
            lai = path.build(dao, level_from="chua_hoc", level_to="N3")
            self.assertEqual(
                [k["code"] for k in lai.courses], [k["code"] for k in chuan.courses]
            )
            self.assertEqual(lai.months_min, chuan.months_min)

    def test_hai_duong_bang_thang_thi_pha_the_hoa_bang_ma_khoa(self):
        a = khoa("KH-0001", "chua_hoc", "N4", 6, 6, 30_000_000)
        b = khoa("KH-0002", "chua_hoc", "N4", 6, 6, 40_000_000)
        self.assertEqual(
            [k["code"] for k in path.build([b, a], level_from="chua_hoc", level_to="N4").courses],
            ["KH-0001"],
        )


class HocPhiTests(unittest.TestCase):
    def test_thieu_hoc_phi_mot_khoa_thi_khong_cong_tong(self):
        """Thiếu một mắt thì tổng không còn là tổng.

        Thà nói "chưa có đủ thông tin học phí" hơn là đưa ra con số thiếu một
        chặng — khách sẽ chuẩn bị thiếu tiền và phát hiện ra lúc đã muộn.
        """
        co_gia = khoa("KH-0001", "chua_hoc", "N5", 4, 4, 20_000_000)
        chua_gia = khoa("KH-0002", "N5", "N4", 3, 3, None)
        ra = path.build([co_gia, chua_gia], level_from="chua_hoc", level_to="N4")
        self.assertIsNone(ra.tuition_vnd)
        self.assertTrue(ra.tuition_incomplete)
        # Thời gian vẫn cộng được vì cả hai khóa đều có số tháng.
        self.assertEqual(ra.months_min, 7)

    def test_khoa_hong_khai_nguoc_trinh_do_thi_bi_bo(self):
        """Dữ liệu hỏng không được đem đi tư vấn, và không được tạo vòng lặp."""
        nguoc = khoa("KH-0009", "N4", "chua_hoc", 3, 3, 10_000_000)
        self.assertIsNone(path.build([nguoc], level_from="chua_hoc", level_to="N4"))

    def test_khoa_khai_ngang_khong_gay_vong_lap(self):
        ngang = khoa("KH-0008", "N5", "N5", 2, 2, 5_000_000)
        ra = path.build([ngang], level_from="N5", level_to="N4")
        self.assertIsNone(ra)


class HienThiTests(unittest.TestCase):
    def test_khoang_thoi_gian_viet_dung_nhu_nguon(self):
        ra = path.build([KHOA_THAT], level_from="chua_hoc", level_to="N4")
        self.assertEqual(ra.months_text, "6–7 tháng")

    def test_mot_so_duy_nhat_thi_khong_viet_thanh_khoang(self):
        ra = path.build(
            [khoa("KH-0001", "chua_hoc", "N4", 6, 6, 1)],
            level_from="chua_hoc",
            level_to="N4",
        )
        self.assertEqual(ra.months_text, "6 tháng")

    def test_thieu_months_max_thi_lay_theo_months_min(self):
        ra = path.build(
            [khoa("KH-0001", "chua_hoc", "N4", 6, None, 1)],
            level_from="chua_hoc",
            level_to="N4",
        )
        self.assertEqual(ra.months_text, "6 tháng")

    def test_nhan_tieng_viet_chu_khong_phai_ma_danh_muc(self):
        self.assertEqual(path.label("chua_hoc"), "Chưa học")
        self.assertEqual(path.label(None), "chưa rõ")


class KhongGoiMoHinhNgonNguTests(unittest.TestCase):
    def test_module_khong_import_gi_lien_quan_mo_hinh(self):
        """Cùng chốt chặn như `matching/explain.py`.

        Một ngày nào đó có người muốn "cho AI tư vấn lộ trình cho tự nhiên hơn".
        Ca này bắt họ phải viết ở module khác, để phần tính toán còn tất định.
        """
        import inspect

        nguon = inspect.getsource(path)
        for tu in ("gemini", "generate_response", "llm", "openai", "httpx", "requests"):
            self.assertNotIn(tu, nguon.lower(), f"path.py không được dính tới {tu!r}")


if __name__ == "__main__":
    unittest.main()
