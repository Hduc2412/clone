"""Kiểm thử khối ngữ cảnh tư vấn: bot phải biết nó đang nói với ai.

## Lỗ hổng được lấp

Đo trên máy chủ thật ngày 22/09/2026: một khách đã khai N4, ba năm kinh nghiệm
chăm sóc, muốn đi Tokyo — và bộ đối chiếu đã xếp hạng 11 đơn cho chính họ. Nhưng
khi người ấy hỏi trong cửa sổ chat, bot trả lời như với người hoàn toàn xa lạ và
chỉ sang số tổng đài.

Nguyên nhân không nằm ở mô hình: `chat_service` chưa bao giờ đọc hồ sơ, dù chat
và trang tư vấn dùng chung đúng một mã phiên.

## Ba điều lớp test này giữ

1. **Ba mức tin cậy không được gộp làm một.** "Đã xác nhận" là ứng viên đã nhìn
   tận mắt và bấm đồng ý; "đọc từ CV" là máy đọc ra, chưa ai xác nhận. Gộp lại
   thì bot nói chắc nịch về thứ máy vừa đoán — đúng kiểu hỏng mà R1 và R3 sinh
   ra để chặn.
2. **"Chưa rõ" không được biến thành "không có".** Trường vắng nghĩa là chưa ai
   hỏi tới. Mô hình rất dễ tự suy "CV không ghi chứng chỉ" thành "ứng viên không
   có chứng chỉ", rồi từ đó kết luận về một con người thật.
3. **Số điện thoại của khách không đi vào ngữ cảnh.** Không có lý do nghiệp vụ
   nào để bot nhắc lại số ấy, nên cách rẻ nhất là nó không bao giờ nhìn thấy.
"""
import unittest
from unittest.mock import AsyncMock, patch

from app.consultation import context_builder, next_question
from app.db import candidate_profiles as profiles
from app.services import chat_service


def o(value, source="user_confirmed"):
    return {"value": value, "source": source, "confidence": 1.0}


def ho_so(**overrides):
    document = {
        "code": "UV-TEST01",
        "session_id": "s" * 32,
        "status": profiles.STATUS_CONFIRMED,
        "version": 1,
        "fields": {
            "full_name": o("Nguyễn Thị Lan"),
            "japanese_level": o("N4"),
            "experience_years": o(3, "cv"),
            "phone": o("0912345678"),
        },
        "preferences": {"desired_prefecture": o("Tokyo", "chat")},
    }
    document.update(overrides)
    profiles.decorate(document)
    return document


class BaMucTinCayTests(unittest.TestCase):
    def test_tach_rieng_da_xac_nhan_voi_doc_tu_cv_voi_nghe_trong_chat(self):
        khoi = context_builder.render(ho_so())

        self.assertIn("Đã xác nhận", khoi)
        self.assertIn("Đọc từ CV, khách chưa xác nhận", khoi)
        self.assertIn("Khách nói trong hội thoại, chưa xác nhận", khoi)

    def test_moi_gia_tri_nam_dung_nhom_cua_no(self):
        khoi = context_builder.render(ho_so())
        cac_dong = khoi.splitlines()

        def nhom_cua(chu: str) -> str:
            """Tiêu đề nhóm gần nhất phía trên dòng chứa `chu`."""
            vi_tri = next(i for i, d in enumerate(cac_dong) if chu in d)
            for dong in reversed(cac_dong[:vi_tri]):
                if dong.endswith(":") and not dong.startswith("  "):
                    return dong
            return ""

        self.assertIn("Đã xác nhận", nhom_cua("Nguyễn Thị Lan"))
        self.assertIn("CV", nhom_cua("3 năm"))
        self.assertIn("hội thoại", nhom_cua("Tokyo"))

    def test_nhan_tieng_viet_chu_khong_phai_ma_danh_muc(self):
        khoi = context_builder.render(
            ho_so(fields={"education_level": o("cao_dang"), "gender": o("nu")})
        )
        self.assertIn("Cao đẳng", khoi)
        self.assertNotIn("cao_dang", khoi)


class ChuaRoKhacKhongCoTests(unittest.TestCase):
    def test_noi_ro_chua_ai_hoi_toi_chu_khong_phai_khach_khong_co(self):
        khoi = context_builder.render(ho_so())

        self.assertIn("Chưa rõ", khoi)
        self.assertIn("KHÔNG phải là khách không có", khoi)

    def test_truong_da_co_thi_khong_con_nam_trong_phan_chua_ro(self):
        day_du = ho_so(
            fields={
                "full_name": o("Nguyễn Thị Lan"),
                "japanese_level": o("N4"),
                "education_level": o("cao_dang"),
                "experience_years": o(3),
                "birth_year": o(1999),
                "gender": o("nu"),
            },
            preferences={
                "desired_prefecture": o("Tokyo"),
                "desired_employer_type": o("vien_duong_lao"),
                "salary_expectation_jpy": o(200000),
                "budget_vnd": o(150_000_000),
            },
        )
        self.assertEqual(context_builder.con_thieu(day_du), [])
        self.assertNotIn("Chưa rõ", context_builder.render(day_du))

    def test_chua_hoc_tieng_nhat_la_mot_cau_tra_loi_chu_khong_phai_thieu(self):
        # "chua_hoc" là một giá trị đã khai, không phải ô trống. Coi nó là thiếu
        # thì bot sẽ hỏi lại đúng thứ khách vừa trả lời.
        khach = ho_so(fields={"full_name": o("A"), "japanese_level": o("chua_hoc")})
        self.assertNotIn("japanese_level", context_builder.con_thieu(khach))


class BietHoSoKhongCoNghiaLaDuocPhanQuyetTests(unittest.TestCase):
    """Chính tính năng này tạo ra cám dỗ phán quyết, nên nó phải tự chặn.

    Đo trên máy chủ thật ngày 22/09/2026, ngay lượt đầu sau khi khối hồ sơ được
    nối vào ngữ cảnh: bot đáp *"Với hồ sơ của bạn, bạn hoàn toàn đủ điều kiện
    tham gia chương trình"*. Luật cấm phán quyết đã nằm sẵn trong prompt từ lâu
    và vẫn bị bỏ qua — vì biết về người ta làm mô hình sẵn lòng kết luận hơn hẳn.

    Đây là lý do cảnh báo phải đi **kèm dữ liệu** chứ không để riêng ở phần luật:
    ai đọc khối này cũng thấy ngay ràng buộc đi cùng nó.
    """

    def test_khoi_ho_so_luon_kem_lenh_cam_phan_quyet(self):
        khoi = context_builder.render(ho_so())
        self.assertIn("KHÔNG dùng những thông tin này để kết luận", khoi)

    def test_liet_ke_ro_nhung_cum_tu_khong_duoc_noi(self):
        khoi = context_builder.render(ho_so())
        for cum in ("đủ điều kiện", "hoàn toàn phù hợp", "chắc chắn đi được"):
            self.assertIn(cum, khoi)

    def test_chi_ro_ai_moi_la_nguoi_ket_luan(self):
        # Chỉ nói "đừng" thì mô hình lách bằng cách diễn đạt khác. Phải cho nó
        # một việc thay thế để làm.
        khoi = context_builder.render(ho_so())
        self.assertIn("bộ đối chiếu", khoi)
        self.assertIn("nhân viên", khoi)


class KhongDuaSoDienThoaiVaoNguCanhTests(unittest.TestCase):
    def test_so_dien_thoai_cua_khach_khong_xuat_hien_trong_khoi(self):
        khoi = context_builder.render(ho_so())
        self.assertNotIn("0912345678", khoi)


class CauHoiBoSungTests(unittest.TestCase):
    def test_dung_lai_cau_hoi_cua_bo_doi_chieu(self):
        """Một nguồn duy nhất: thêm tiêu chí vào bộ đối chiếu thì bot hỏi thêm câu ấy."""
        from app.matching.engine import MISSING_PROMPTS

        for cau in next_question.chon(ho_so()):
            self.assertIn(cau, MISSING_PROMPTS.values())

    def test_nhieu_nhat_hai_cau(self):
        trong = ho_so(fields={}, preferences={})
        self.assertLessEqual(len(next_question.chon(trong)), 2)

    def test_theo_dung_thu_tu_uu_tien_cua_bo_doi_chieu(self):
        """Hỏi trường quyết định nhất trước, không hỏi theo bảng chữ cái."""
        from app.matching.engine import MISSING_ORDER, MISSING_PROMPTS

        trong = ho_so(fields={}, preferences={})
        cac_cau = next_question.chon(trong)
        mong_doi = [MISSING_PROMPTS[key] for key in MISSING_ORDER[:2]]
        self.assertEqual(cac_cau, mong_doi)

    def test_ho_so_du_thi_khong_hoi_gi_them(self):
        day_du = ho_so(
            fields={
                "full_name": o("A"),
                "japanese_level": o("N4"),
                "education_level": o("cao_dang"),
                "experience_years": o(3),
                "birth_year": o(1999),
                "gender": o("nu"),
            },
            preferences={
                "desired_prefecture": o("Tokyo"),
                "desired_employer_type": o("vien_duong_lao"),
                "salary_expectation_jpy": o(200000),
                "budget_vnd": o(150_000_000),
            },
        )
        self.assertEqual(next_question.render(day_du), "")


class KhachLaThiKhongCoKhoiNaoTests(unittest.IsolatedAsyncioTestCase):
    async def test_phien_chua_co_ho_so_thi_khoi_rong(self):
        with patch.object(profiles, "get_by_session", AsyncMock(return_value=None)):
            self.assertEqual(await chat_service._profile_context("x" * 32), "")

    async def test_ho_so_hong_khong_lam_hong_cau_tra_loi(self):
        """Hồ sơ làm câu trả lời tốt hơn, không phải điều kiện để có câu trả lời."""
        with patch.object(
            profiles, "get_by_session", AsyncMock(side_effect=RuntimeError("Mongo sập"))
        ), self.assertLogs("app.services.chat_service", level="WARNING"):
            self.assertEqual(await chat_service._profile_context("x" * 32), "")


if __name__ == "__main__":
    unittest.main()
