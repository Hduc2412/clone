"""Phân nhánh phòng tư vấn theo đơn — thuần, không database, không mạng.

Ca đáng giá nhất bộ này: `test_qua_tuoi_thi_khong_moi_hoc_tieng`. Thấy "chưa phù
hợp" rồi mời học tiếng là phản xạ tự nhiên nhưng sai — người quá tuổi học xong
vẫn không đi được, và lời mời ấy thành ra bán khóa học cho người không có cửa.
"""
import unittest

from app.consultation import advice
from app.matching.engine import CHUA_RO, DAT, KHONG_DAT, CriterionRow, MatchItem


KHOA = {
    "code": "KH-0001",
    "title": "Học tiếng Nhật tại trung tâm",
    "level_from": "chua_hoc",
    "level_to": "N4",
    "months_min": 6,
    "months_max": 7,
    "tuition_vnd": 35_000_000,
    "package_total_vnd": 90_000_000,
}

# `advice` chỉ cần mức tiếng Nhật đơn yêu cầu, không cần cả bản ghi đơn:
# `MatchItem` không mang theo `requirements`, nên truyền bản ghi đơn vào chỉ tạo
# cảm giác có dữ liệu mà thật ra rỗng.
YEU_CAU_TIENG_NHAT = "N4"


def dong(key, label, ket_qua, missing=None):
    return CriterionRow(
        key=key,
        label=label,
        requirement_text=f"yêu cầu {label}",
        candidate_text=f"ứng viên {label}",
        result=ket_qua,
        missing_field=missing,
    )


def muc(*rows, eligible=False, score=0):
    return MatchItem(
        code="DH-0001",
        title="Điều dưỡng viện dưỡng lão Tokyo",
        employer_name="Sakura",
        prefecture="tokyo",
        region_group="kanto",
        employer_type="vien_duong_lao",
        program="tokutei",
        deadline="2026-11-30",
        eligible=eligible,
        score=score,
        rank=1,
        hard_rows=tuple(rows),
        soft_rows=(),
        gaps=(),
        missing_info=(),
    )


DAT_HET = (
    dong("status", "Trạng thái đơn", DAT),
    dong("deadline", "Hạn nộp hồ sơ", DAT),
    dong("japanese", "Tiếng Nhật", DAT),
    dong("education", "Bằng cấp", DAT),
    dong("age", "Độ tuổi", DAT),
)


class PhanNhanhTests(unittest.TestCase):
    def test_du_dieu_kien_thi_nhanh_phu_hop(self):
        ra = advice.build(muc(*DAT_HET, eligible=True, score=75), required_japanese="N4",
                          profile_level="N4", courses=[KHOA])
        self.assertEqual(ra.branch, advice.PHU_HOP)
        self.assertTrue(ra.can_register)

    def test_chua_khai_thi_nhanh_thieu_thong_tin_chu_khong_phai_truot(self):
        """Chưa hỏi tới không phải là không đạt — quy tắc cốt lõi của bộ đối chiếu."""
        rows = (*DAT_HET[:2], dong("japanese", "Tiếng Nhật", CHUA_RO, "japanese_level"),
                *DAT_HET[3:])
        ra = advice.build(muc(*rows), required_japanese="N4", profile_level=None, courses=[KHOA])
        self.assertEqual(ra.branch, advice.THIEU_THONG_TIN)
        self.assertFalse(ra.can_register)

    def test_chac_chan_truot_thi_noi_ngay_du_con_o_chua_ro(self):
        """Bắt người quá tuổi khai thêm bằng cấp rồi mới báo trượt là phí thời gian của họ."""
        rows = (
            dong("age", "Độ tuổi", KHONG_DAT),
            dong("education", "Bằng cấp", CHUA_RO, "education_level"),
        )
        ra = advice.build(muc(*rows), required_japanese="N4", profile_level="N4", courses=[KHOA])
        self.assertEqual(ra.branch, advice.CHUA_PHU_HOP)

    def test_chi_nhanh_phu_hop_moi_cho_dang_ky(self):
        for nhanh_rows, eligible in (
            ((dong("age", "Độ tuổi", KHONG_DAT),), False),
            ((dong("japanese", "Tiếng Nhật", CHUA_RO, "japanese_level"),), False),
        ):
            ra = advice.build(muc(*nhanh_rows, eligible=eligible), required_japanese="N4",
                              profile_level=None, courses=[KHOA])
            self.assertFalse(ra.can_register)


class MoiHocDungLucTests(unittest.TestCase):
    def test_chan_vi_tieng_nhat_thi_ra_lo_trinh(self):
        rows = (*DAT_HET[:2], dong("japanese", "Tiếng Nhật", KHONG_DAT), *DAT_HET[3:])
        ra = advice.build(muc(*rows), required_japanese="N4", profile_level="chua_hoc", courses=[KHOA])
        self.assertIsNotNone(ra.learning)
        self.assertEqual(ra.learning.months_text, "6–7 tháng")
        self.assertIn("35.000.000đ", ra.block)
        # Bắt buộc nêu tổng gói, không được để học phí đứng trơ trọi.
        self.assertIn("90.000.000đ", ra.block)

    def test_qua_tuoi_thi_khong_moi_hoc_tieng(self):
        """Học xong vẫn không đi được. Nói thẳng còn hơn để họ phát hiện sau khi đóng tiền."""
        rows = (
            dong("japanese", "Tiếng Nhật", KHONG_DAT),
            dong("age", "Độ tuổi", KHONG_DAT),
        )
        ra = advice.build(muc(*rows), required_japanese="N4", profile_level="chua_hoc", courses=[KHOA])
        self.assertIsNone(ra.learning)
        self.assertIn("không bù được", ra.learning_note)
        self.assertIn("Độ tuổi", ra.learning_note)
        self.assertNotIn("35.000.000", ra.block)

    def test_truot_vi_ly_do_khac_thi_khong_nhac_toi_hoc(self):
        rows = (dong("education", "Bằng cấp", KHONG_DAT),)
        ra = advice.build(muc(*rows), required_japanese="N4", profile_level="chua_hoc", courses=[KHOA])
        self.assertIsNone(ra.learning)
        self.assertEqual(ra.learning_note, "")

    def test_danh_muc_khoa_rong_thi_giai_thich_chu_khong_im_lang(self):
        rows = (dong("japanese", "Tiếng Nhật", KHONG_DAT),)
        ra = advice.build(muc(*rows), required_japanese="N4", profile_level="chua_hoc", courses=[])
        self.assertIsNone(ra.learning)
        self.assertIn("chưa có khóa nào", ra.learning_note)
        # Không con số nào lọt ra khi chưa có dữ liệu.
        self.assertNotIn("tháng", ra.block.split("VỀ VIỆC HỌC THÊM")[-1].split(".")[0])

    def test_chua_biet_trinh_do_thi_khong_doan_lo_trinh(self):
        rows = (dong("japanese", "Tiếng Nhật", KHONG_DAT),)
        ra = advice.build(muc(*rows), required_japanese="N4", profile_level=None, courses=[KHOA])
        self.assertIsNone(ra.learning)
        self.assertIn("Chưa biết trình độ", ra.learning_note)


class CauHoiBoSungTests(unittest.TestCase):
    def test_dung_lai_cau_hoi_cua_bo_doi_chieu(self):
        from app.matching.engine import MISSING_PROMPTS

        rows = (dong("japanese", "Tiếng Nhật", CHUA_RO, "japanese_level"),)
        ra = advice.build(muc(*rows), required_japanese="N4", profile_level=None, courses=[])
        self.assertTrue(set(ra.questions) <= set(MISSING_PROMPTS.values()))

    def test_nhieu_nhat_hai_cau(self):
        rows = tuple(
            dong(f"k{i}", f"L{i}", CHUA_RO, truong)
            for i, truong in enumerate(
                ("japanese_level", "education_level", "experience_years", "birth_year")
            )
        )
        ra = advice.build(muc(*rows), required_japanese="N4", profile_level=None, courses=[])
        self.assertLessEqual(len(ra.questions), advice.TOI_DA_CAU_HOI)

    def test_khong_lap_cau_hoi(self):
        rows = (
            dong("a", "A", CHUA_RO, "japanese_level"),
            dong("b", "B", CHUA_RO, "japanese_level"),
        )
        ra = advice.build(muc(*rows), required_japanese="N4", profile_level=None, courses=[])
        self.assertEqual(len(ra.questions), len(set(ra.questions)))


class KhoiChuTests(unittest.TestCase):
    def test_khoi_noi_ro_chua_ro_khong_phai_khong_dat(self):
        rows = (dong("japanese", "Tiếng Nhật", CHUA_RO, "japanese_level"),)
        ra = advice.build(muc(*rows), required_japanese="N4", profile_level=None, courses=[])
        self.assertIn("KHÔNG phải là không đạt", ra.block)

    def test_don_chua_dat_thi_khong_khoe_diem_so(self):
        """Ghi '45/100 · KHÔNG ĐẠT' cạnh nhau là mời người đọc đem đi so sánh."""
        rows = (dong("age", "Độ tuổi", KHONG_DAT),)
        ra = advice.build(muc(*rows, score=45), required_japanese="N4", profile_level="N4", courses=[])
        self.assertNotIn("ĐIỂM PHÙ HỢP", ra.block)

    def test_don_dat_thi_co_diem_so(self):
        ra = advice.build(muc(*DAT_HET, eligible=True, score=75), required_japanese="N4",
                          profile_level="N4", courses=[])
        self.assertIn("75/100", ra.block)


class KhongGoiMoHinhNgonNguTests(unittest.TestCase):
    def test_module_khong_import_gi_lien_quan_mo_hinh(self):
        import inspect

        nguon = inspect.getsource(advice).lower()
        for tu in ("gemini", "generate_response", "openai", "httpx", "requests"):
            self.assertNotIn(tu, nguon, f"advice.py không được dính tới {tu!r}")


if __name__ == "__main__":
    unittest.main()


class DieuKienSucKhoeTests(unittest.TestCase):
    """Nói điều kiện sức khỏe trước khi khách đóng đồng nào.

    Trước đây khách chỉ biết sau khi đặt cọc 10 triệu rồi đi khám. Đây là giá
    trị thật của việc đưa điều kiện mức nền vào phòng tư vấn.
    """

    def _block(self, *rows, **kw):
        return advice.build(muc(*rows, **kw), required_japanese="N4",
                            profile_level=kw.pop("level", "N4"), courses=[KHOA]).block

    def test_nhanh_phu_hop_thi_nhac_con_buoc_kham(self):
        block = advice.build(muc(*DAT_HET, eligible=True, score=75), required_japanese="N4",
                             profile_level="N4", courses=[KHOA]).block
        self.assertIn("CÒN MỘT BƯỚC KHÁM", block)
        for benh in ("Viêm gan B", "HIV", "Bệnh lao"):
            self.assertIn(benh, block)

    def test_luon_kem_loi_nhac_danh_sach_chua_day_du(self):
        """Nguồn ghi 'các bệnh truyền nhiễm **như**' — chữ *như* nghĩa là còn nữa.

        Nêu ba bệnh trơ trọi là để khách hiểu không có ba bệnh ấy thì chắc chắn đạt.
        """
        block = advice.build(muc(*DAT_HET, eligible=True), required_japanese="N4",
                             profile_level="N4", courses=[KHOA]).block
        self.assertIn("có thể còn bệnh khác", block)
        self.assertIn("buổi khám", block)

    def test_co_lo_trinh_hoc_thi_van_nhac_suc_khoe(self):
        rows = (*DAT_HET[:2], dong("japanese", "Tiếng Nhật", KHONG_DAT), *DAT_HET[3:])
        block = advice.build(muc(*rows), required_japanese="N4", profile_level="chua_hoc",
                             courses=[KHOA]).block
        self.assertIn("CÒN MỘT BƯỚC KHÁM", block)

    def test_qua_tuoi_thi_khong_don_them_dieu_kien_nua(self):
        """Người chắc chắn trượt vì tuổi không cần nghe thêm một điều kiện nữa."""
        rows = (
            dong("japanese", "Tiếng Nhật", KHONG_DAT),
            dong("age", "Độ tuổi", KHONG_DAT),
        )
        block = advice.build(muc(*rows), required_japanese="N4", profile_level="chua_hoc",
                             courses=[KHOA]).block
        self.assertNotIn("CÒN MỘT BƯỚC KHÁM", block)


class KhongLuuDuLieuSucKhoeTests(unittest.TestCase):
    def test_khong_co_truong_nao_giu_tinh_trang_benh(self):
        """Chẩn đoán bệnh theo người ta đi rất xa nếu lộ, mà giá trị nghiệp vụ
        bằng không — buổi khám mới là chỗ kết luận.

        Ca này chặn việc ai đó thêm một trường kiểu `has_hepatitis` về sau.
        """
        ra = advice.build(muc(*DAT_HET, eligible=True), required_japanese="N4",
                          profile_level="N4", courses=[KHOA])
        khoa_cam = ("health", "disease", "benh", "hepatitis", "hiv", "diagnosis")
        for khoa_ in advice.as_dict(ra):
            for cam in khoa_cam:
                self.assertNotIn(cam, khoa_.lower(),
                                 f"trả về không được có trường {khoa_!r}")
