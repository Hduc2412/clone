"""Lượt mở đầu "sau CV" phải nói đúng chuyện đã xảy ra, và chỉ nói một lần.

Hai lỗi bắt trên trình duyệt thật ngày 06/10, cùng một gốc — câu mở đầu suy ra
"đọc CV hỏng" từ việc hồ sơ không còn trường nguồn `cv`:

1. Khách khai bằng biểu mẫu, **không gửi tệp nào**, vẫn nghe "Mình đã nhận được
   tệp của bạn nhưng chưa rút được thông tin nào chắc chắn từ đó".
2. CV đọc được chín trường, khách bấm "Sửa hồ sơ" (biểu mẫu ghi lại mọi trường
   thành `user_confirmed`): câu đổi chữ, bộ chống trùng so theo chữ nên ghi thêm
   một lượt mở đầu thứ hai — đúng câu sai ở (1).
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent import mo_dau
from app.api import agent as api_agent

PHIEN = "3db5442f-f6d1-41ee-8928-cf4392392d00"
TEP_DOC_DUOC = {"code": "CV-AAAAAA", "status": "extracted", "extracted_fields": ["japanese_level"]}
TEP_HONG = {"code": "CV-BBBBBB", "status": "unreadable", "extracted_fields": []}


def ho_so(nguon: str) -> dict:
    return {
        "code": "UV-TEST01",
        "session_id": PHIEN,
        "status": "confirmed",
        "version": 2,
        "fields": {
            "japanese_level": {"value": "N4", "source": nguon},
            "education_level": {"value": "cao_dang", "source": nguon},
        },
        "preferences": {},
    }


class NguonHoSoTests(unittest.TestCase):
    def test_khong_co_tep_la_khai_tay(self):
        self.assertEqual(mo_dau.nguon_ho_so(None), mo_dau.KHAI_TAY)

    def test_tep_doc_duoc(self):
        self.assertEqual(mo_dau.nguon_ho_so(TEP_DOC_DUOC), mo_dau.CV_DOC_DUOC)

    def test_tep_khong_doc_duoc(self):
        self.assertEqual(mo_dau.nguon_ho_so(TEP_HONG), mo_dau.CV_HONG)

    def test_doc_xong_nhung_khong_rut_duoc_truong_nao(self):
        self.assertEqual(
            mo_dau.nguon_ho_so({**TEP_DOC_DUOC, "extracted_fields": []}), mo_dau.CV_HONG
        )


class BaCauMoDauTests(unittest.TestCase):
    def test_khai_tay_khong_nhac_toi_tep(self):
        cau = mo_dau.sau_khi_doc_cv(ho_so("user_confirmed"), nguon=mo_dau.KHAI_TAY)
        self.assertNotIn("tệp", cau)
        self.assertNotIn("CV", cau)
        self.assertNotIn("máy đọc", cau)
        self.assertIn("bạn khai", cau)
        self.assertIn("N4", cau)

    def test_cv_hong_noi_ro_chua_doc_duoc(self):
        cau = mo_dau.sau_khi_doc_cv(ho_so("user_confirmed"), nguon=mo_dau.CV_HONG)
        self.assertIn("chưa rút được", cau)
        # Không có gì do máy đọc thì không nhờ khách soát "thứ máy đọc được".
        self.assertNotIn("máy đọc", cau)

    def test_cv_doc_duoc_ke_lai_va_nho_soat(self):
        cau = mo_dau.sau_khi_doc_cv(ho_so("cv"), nguon=mo_dau.CV_DOC_DUOC)
        self.assertIn("Mình đã đọc CV của bạn", cau)
        self.assertIn("máy đọc được", cau)

    def test_cv_doc_duoc_roi_khach_sua_het_thi_khong_noi_doc_hong(self):
        """Đúng ca (2): đọc được, rồi mọi trường thành `user_confirmed`."""
        cau = mo_dau.sau_khi_doc_cv(ho_so("user_confirmed"), nguon=mo_dau.CV_DOC_DUOC)
        self.assertNotIn("chưa rút được", cau)
        self.assertNotIn("máy đọc", cau)
        self.assertIn("đã xác nhận", cau)


class MoDauMotLanMoiTepTests(unittest.IsolatedAsyncioTestCase):
    """Đi qua endpoint thật với bộ lưu lượt giả trong bộ nhớ."""

    async def _goi(self, profile, tep, kho):
        async def _them(**kw):
            kho.append(kw)
            return kw

        with patch.object(
            api_agent, "_nap", AsyncMock(return_value=(profile, MagicMock(), None))
        ), patch.object(
            api_agent.tai_lieu_cv, "list_for_session", AsyncMock(return_value=[tep] if tep else [])
        ), patch.object(
            api_agent.advisor_turns, "list_turns", AsyncMock(side_effect=lambda *a, **k: list(kho))
        ), patch.object(
            api_agent.advisor_turns, "add_turn", _them
        ), patch.object(
            api_agent, "_ghi_moc", AsyncMock()
        ), patch.object(
            api_agent.orchestrator, "cau_hoi_con_thieu", lambda _p: []
        ):
            return await api_agent.mo_dau_hoi_thoai(PHIEN, api_agent.MoDauBody(moc="sau_cv"))

    async def test_sua_ho_so_khong_sinh_them_luot_mo_dau(self):
        kho: list[dict] = []
        await self._goi(ho_so("cv"), TEP_DOC_DUOC, kho)
        # Khách bấm "Sửa hồ sơ": mọi trường thành `user_confirmed`, cùng một tệp.
        await self._goi(ho_so("user_confirmed"), TEP_DOC_DUOC, kho)
        self.assertEqual(len(kho), 1)
        self.assertEqual(kho[0]["moc"], "sau_cv:CV-AAAAAA")

    async def test_gui_tep_moi_thi_noi_lai(self):
        kho: list[dict] = []
        await self._goi(ho_so("cv"), TEP_DOC_DUOC, kho)
        await self._goi(ho_so("cv"), {**TEP_DOC_DUOC, "code": "CV-CCCCCC"}, kho)
        self.assertEqual([l["moc"] for l in kho], ["sau_cv:CV-AAAAAA", "sau_cv:CV-CCCCCC"])

    async def test_khai_tay_mot_luot_va_khong_noi_tep(self):
        kho: list[dict] = []
        ra = await self._goi(ho_so("user_confirmed"), None, kho)
        await self._goi(ho_so("user_confirmed"), None, kho)
        self.assertEqual(len(kho), 1)
        self.assertEqual(kho[0]["moc"], "sau_cv:khai_tay")
        self.assertNotIn("tệp", ra["reply"])

    async def test_phien_cu_co_luot_sau_cv_khong_khoa_thi_khong_noi_lai(self):
        """Lượt ghi trước bản sửa không mang `moc` — tải lại trang không được nói lần hai."""
        kho = [{"question": "[hệ thống] sau_cv", "answer": "câu cũ"}]
        await self._goi(ho_so("user_confirmed"), TEP_DOC_DUOC, kho)
        self.assertEqual(len(kho), 1)

    async def test_luot_sau_doi_chieu_khong_bi_tinh_la_sau_cv(self):
        kho = [{"question": "[hệ thống] sau_matching", "answer": "kết quả"}]
        await self._goi(ho_so("cv"), TEP_DOC_DUOC, kho)
        self.assertEqual(len(kho), 2)


if __name__ == "__main__":
    unittest.main()
