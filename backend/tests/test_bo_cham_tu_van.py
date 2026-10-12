"""Bộ chấm câu trả lời mô hình thật (`scripts/danh_gia_tu_van_that._cham`).

Bộ chấm quyết định một lượt đo là ĐẠT hay HỎNG, nên bản thân nó cũng phải được kiểm.
Đợt 08/10 (dot3) nó chấm HỎNG một câu đúng — "hoàn thành khóa học **chưa** đồng
nghĩa với việc đủ điều kiện tiếng Nhật" — vì chỉ tìm cụm từ, không xét phủ định. Ghim
cả hai chiều: câu phủ định không bị bắt nhầm, câu khẳng định sai vẫn bị bắt.
"""
import unittest

from app.advisor import qa
from scripts import danh_gia_tu_van_that as dg

MO_HINH = qa.NGUON_MO_HINH
LOI_KHANG_DINH = "coi hoàn thành chương trình tại trung tâm như chứng chỉ / đủ yêu cầu của đơn"


class ChuongTrinhTrungTamTests(unittest.TestCase):
    def test_cau_phu_dinh_dung_thi_dat(self):
        cau = (
            "Hệ thống ghi nhận bạn đã hoàn thành chương trình N4 tại trung tâm nhưng chưa xác minh "
            "chứng chỉ, nên việc hoàn thành khóa học chưa đồng nghĩa với việc đủ điều kiện tiếng Nhật của đơn."
        )
        self.assertEqual(dg._cham("chuong_trinh", cau, MO_HINH), [])

    # Kiểm ĐÚNG điểm hỏng, không chỉ "có lỗi nào đó": câu sai mà không nhắc chứng chỉ thì
    # luật "không nói rõ chưa phải chứng chỉ" cũng bật, và che mất luật khẳng định (đột
    # biến lọt 09/10). Câu thử nên có chữ "chứng chỉ" để chỉ còn đúng một luật được đo.
    def test_khang_dinh_du_dieu_kien_thi_hong(self):
        cau = "Chương trình N4 tại trung tâm thay cho chứng chỉ, nên bạn đủ điều kiện tiếng Nhật của đơn này."
        self.assertEqual(dg._cham("chuong_trinh", cau, MO_HINH), [LOI_KHANG_DINH])

    def test_coi_nhu_co_chung_chi_thi_hong(self):
        cau = "Học xong khóa N4 nghĩa là bạn đã có chứng chỉ rồi."
        self.assertEqual(dg._cham("chuong_trinh", cau, MO_HINH), [LOI_KHANG_DINH])

    def test_khong_noi_gi_ve_chung_chi_thi_hong(self):
        cau = "Bạn học rất tốt, cứ tiếp tục nhé."
        self.assertIn(
            "không nói rõ hoàn thành chương trình chưa phải chứng chỉ",
            dg._cham("chuong_trinh", cau, MO_HINH),
        )


class QuyTacChungTests(unittest.TestCase):
    def test_khong_ra_cau_tu_van_thi_hong_ngay(self):
        self.assertTrue(dg._cham("tien_do", "bất kỳ", "du_phong"))

    def test_phu_hop_nhat_phu_dinh_khong_bi_bat(self):
        cau = "Hiện mình chưa nói được đơn nào phù hợp nhất vì bạn chưa nêu nguyện vọng."
        self.assertNotIn(
            "khẳng định đơn 'phù hợp nhất/hợp hơn' khi các đơn chưa được xếp theo nguyện vọng",
            dg._cham("doi_don", cau + " DH-0016", MO_HINH),
        )

    def test_hoc_phi_khong_kem_tong_thi_hong(self):
        cau = "Học phí là 35 triệu. Có đơn DH-0016."
        self.assertIn("nêu học phí mà không nêu tổng chi phí chương trình", dg._cham("doi_don", cau, MO_HINH))

    def test_dang_hoc_n3_noi_thanh_da_co_thi_hong(self):
        cau = "Hồ sơ của bạn đang ở chặng đủ điều kiện sơ bộ và bạn đã đạt N3."
        self.assertIn("nói 'đang học N3' thành trình độ đã có", dg._cham("tien_do", cau, MO_HINH))

    def test_tien_do_dung(self):
        cau = "Hồ sơ đơn DH-0001 đang ở chặng đủ điều kiện sơ bộ. Bạn đang học hướng tới N3, chưa phải trình độ đã có."
        self.assertEqual(dg._cham("tien_do", cau, MO_HINH), [])


class DuLieuMauNhatQuanTests(unittest.TestCase):
    """Khối đưa cho mô hình ở hai ca tiến độ phải nói CÙNG một người (12/10).

    Đợt dot3 (08/10) ghép hồ sơ "chưa học" với khối tiến độ viết tay "N4 có chứng chỉ" —
    câu trả lời khi ấy không chứng minh được gì về việc mô hình dùng đúng dữ liệu tiến độ.
    """

    def setUp(self):
        from tests import hau_kiem_mau as mau

        self.mau = mau

    def test_khoi_ho_so_va_doi_chieu_khong_con_ho_so_chua_hoc(self):
        # Chỉ hai khối nói về NGƯỜI này. Danh mục khóa học thì đúng là có "nhận từ Chưa học".
        for ma in dg.CA_TIEN_DO:
            k = self.mau.cac_khoi_tien_do(ma)
            for ten in ("ho_so", "doi_chieu"):
                with self.subTest(ma=ma, khoi=ten):
                    self.assertNotIn("Chưa học", k[ten])

    def test_khong_khoi_nao_lot_ma_may(self):
        for ma in dg.CA_TIEN_DO:
            with self.subTest(ma=ma):
                for ma_may in ("khong_yeu_cau", "cao_dang", "vien_duong_lao", "tokutei_ginou"):
                    self.assertNotIn(ma_may, "\n".join(self.mau.cac_khoi_tien_do(ma).values()))

    def test_tien_do_dat_va_chang_du_dieu_kien_so_bo_khop_nhau(self):
        k = self.mau.cac_khoi_tien_do("tien_do")
        self.assertIn("Tiếng Nhật: N4", k["ho_so"])
        self.assertIn("N4 — có chứng chỉ, nhân viên đã đối chứng", k["ho_so"])
        self.assertIn('chặng "Đủ điều kiện sơ bộ"', k["ho_so"])
        self.assertIn("đang học hướng tới N3", k["ho_so"])
        self.assertIn("KẾT LUẬN: đạt các điều kiện bắt buộc", k["doi_chieu"])
        self.assertIn("ứng viên N4", k["doi_chieu"])

    def test_chuong_trinh_n5_tu_khai_va_chua_dat_n4(self):
        k = self.mau.cac_khoi_tien_do("chuong_trinh")
        self.assertIn("Tiếng Nhật: N5", k["ho_so"])
        self.assertIn("Hoàn thành chương trình N4 tại trung tâm — chưa xác minh chứng chỉ", k["ho_so"])
        self.assertNotIn("Đủ điều kiện sơ bộ", k["ho_so"])
        self.assertIn("KẾT LUẬN: chưa đạt điều kiện bắt buộc", k["doi_chieu"])
        self.assertIn("ứng viên N5", k["doi_chieu"])

    def test_script_do_dua_dung_bo_khoi_nhat_quan_cho_mo_hinh(self):
        """Nối dây: `_mot_ca` của bộ đo phải đưa bộ khối mới, không còn khối viết tay."""
        import asyncio
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, patch

        goi = AsyncMock(return_value=SimpleNamespace(cau="x", nguon="mo_hinh", model="gia", ly_do=""))
        with patch.object(dg.qa, "tra_loi_chi_tiet", goi):
            asyncio.run(dg._mot_ca("tien_do", "don", "Hồ sơ tôi tới bước nào?"))
            dau_vao = goi.call_args.kwargs
            self.assertIn('chặng "Đủ điều kiện sơ bộ"', dau_vao["ho_so"])
            self.assertNotIn("Chưa học", dau_vao["ho_so"])
            self.assertIn("KẾT LUẬN: đạt các điều kiện bắt buộc", dau_vao["doi_chieu"])
            # Ca không thuộc nhóm tiến độ vẫn dùng bộ khối chung như trước.
            asyncio.run(dg._mot_ca("con_thieu", "don", "Tôi còn thiếu gì?"))
            self.assertIn("Chưa học", goi.call_args.kwargs["doi_chieu"])

    def test_tuoi_trong_doi_chieu_tinh_tu_nam_sinh_cua_ho_so(self):
        # 1999 → 27 tuổi vào ngày đo; con số này phải do engine tính, không viết tay.
        for ma in dg.CA_TIEN_DO:
            with self.subTest(ma=ma):
                self.assertIn("27 tuổi", self.mau.cac_khoi_tien_do(ma)["doi_chieu"])


if __name__ == "__main__":
    unittest.main()
