"""Hậu kiểm trên bộ câu mẫu có nhãn: giữ suy luận hợp lý, chặn thông tin bịa.

Không đo "câu hay hay dở". Đo đúng câu hỏi của yêu cầu 07/10: chốt chặn có **chặn
nhầm** lời nhận xét và khuyến nghị hợp lý không, và có **để lọt** thông tin bịa không.
Các câu sai mà chốt hiện chưa bắt được đánh dấu `biet_lot` trong `hau_kiem_mau.py` —
ca dưới khẳng định chúng là những chỗ lọt DUY NHẤT.
"""
import unittest

from app.advisor import qa
from tests import hau_kiem_mau as mau


def phan_loai(cau_hoi: str, cau: str) -> str:
    """Câu mô hình viết đi qua đúng đường của phòng tư vấn theo đơn rồi ra nhãn gì."""
    k = mau.cac_khoi()
    khoi_cho_phep = "\n".join((
        k["ho_so"], k["don"], k["doi_chieu"], k["don_khac"], k["khoa_hoc"], k["dieu_kien_nen"],
        qa.so_khach_vua_noi(cau_hoi),
    ))
    kq = qa.xu_ly_cau_tra_loi(cau, khoi_cho_phep)
    if kq.nguon == qa.NGUON_MO_HINH:
        return "giu"
    return "tu_choi" if kq.ly_do.startswith("mo_hinh") else "chan"


class HauKiemCoNhanTests(unittest.TestCase):
    def test_khong_chan_nham_cau_hop_ly(self):
        for cau_hoi, cau, nhan, ghi_chu, _ in mau.CAC_CA:
            if nhan == "giu":
                with self.subTest(ghi_chu):
                    self.assertEqual(phan_loai(cau_hoi, cau), "giu", cau)

    def test_loi_tu_choi_thanh_cau_chuan(self):
        for cau_hoi, cau, nhan, ghi_chu, _ in mau.CAC_CA:
            if nhan == "tu_choi":
                with self.subTest(ghi_chu):
                    self.assertEqual(phan_loai(cau_hoi, cau), "tu_choi", cau)

    def test_chan_thong_tin_bia_tru_cho_da_biet_lot(self):
        lot = []
        for cau_hoi, cau, nhan, ghi_chu, biet_lot in mau.CAC_CA:
            if nhan != "chan":
                continue
            ra = phan_loai(cau_hoi, cau)
            if biet_lot:
                lot.append(ghi_chu)
                self.assertEqual(
                    ra, "giu",
                    f"chốt đã bắt được ca '{ghi_chu}' — bỏ cờ biet_lot trong hau_kiem_mau.py",
                )
            else:
                with self.subTest(ghi_chu):
                    self.assertEqual(ra, "chan", cau)
        self.assertEqual(len(lot), 0, "số chỗ lọt đã biết thay đổi — cập nhật tài liệu")

    def test_danh_muc_rong_thi_khong_khoa_nao_nhac_duoc(self):
        """Danh mục rỗng: mã khóa cũ và khóa có chữ mô tả đều bị chặn.

        Giới hạn đã biết: tên khóa đọc như lời khuyên chung ("học tiếng Nhật tại trung
        tâm") thì chỉ nhìn chữ không phân biệt được với lời khuyên chung — nên quy tắc
        prompt bắt gọi khóa bằng mã, và mã thì luôn kiểm được.
        """
        from app.consultation import khoi_mo_rong

        k = mau.cac_khoi()
        khoi = "\n".join((k["ho_so"], k["don"], khoi_mo_rong.render_khoa_hoc([])))
        for cau in (
            "Bạn có thể học khóa KH-0001 của trung tâm.",
            "Bạn có thể học khóa luyện thi N4 của trung tâm.",
        ):
            with self.subTest(cau):
                self.assertEqual(qa.xu_ly_cau_tra_loi(cau, khoi).nguon, qa.NGUON_KHONG_BIET)

    def test_phan_mot_phan_ngoai_pham_vi_kem_cau_chi_duong(self):
        k = mau.cac_khoi()
        kq = qa.xu_ly_cau_tra_loi(
            "Đơn DH-0001 yêu cầu tiếng Nhật N4. [NGOAI_PHAM_VI]", "\n".join(k.values())
        )
        self.assertNotIn(qa.DAU_NGOAI_PHAM_VI, kq.cau)
        self.assertTrue(kq.cau.endswith(qa.CAU_PHAN_CON_LAI))
        self.assertEqual(kq.nguon, qa.NGUON_MO_HINH)


if __name__ == "__main__":
    unittest.main()
