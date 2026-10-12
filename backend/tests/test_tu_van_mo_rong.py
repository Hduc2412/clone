"""Trợ lý tư vấn đọc đúng ngữ cảnh, gợi ý đơn khác từ engine, và suy giảm có ích.

Kiểm theo ý nghĩa nghiệp vụ của yêu cầu 07/10, không kiểm chuỗi trả lời của mô hình:
mô hình là bản giả ghi lại prompt nó nhận, nên ca nào cũng hỏi "dữ liệu đúng có tới
được mô hình không" và "khi mô hình im, khách nhận được gì".

Dữ liệu đều giả.
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import Request

from app.advisor import qa
from app.agent import state
from app.consultation import du_phong, khoi_mo_rong
from app.db import candidate_profiles as profiles
from app.db import recommendation_logs
from tests import hau_kiem_mau as mau

PHIEN = "3db5442f-f6d1-41ee-8928-cf4392392d00"


def _yeu_cau() -> Request:
    return Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1)})


def _ho_so(trang_thai: str = "confirmed") -> dict:
    return {**mau.HO_SO_THO, "status": trang_thai}


def _dong_don_dang_xem() -> dict:
    """Dòng nhật ký một đơn của DH-0001 — chưa đạt vì tiếng Nhật."""
    return {
        "code": "DH-0001", "title": "Điều dưỡng viện dưỡng lão Tokyo", "employer_name": "Cơ sở A",
        "prefecture": "Tokyo", "region_group": "kanto", "employer_type": "vien_duong_lao",
        "program": "tokutei_ginou", "deadline": "2026-12-15", "eligible": False, "score": 0,
        "rank": None, "gaps": [], "missing_info": [], "labels": {},
        "hard_rows": [
            {"key": "japanese", "label": "Tiếng Nhật", "requirement_text": "yêu cầu N4",
             "candidate_text": "ứng viên Chưa học", "result": "KHONG_DAT"},
            {"key": "birth_year", "label": "Độ tuổi", "requirement_text": "20 đến 35 tuổi",
             "candidate_text": "chưa khai năm sinh", "result": "CHUA_RO", "missing_field": "birth_year"},
        ],
    }


async def _run_matching(profile, *, trigger, chi_don=None, **_):
    if chi_don:
        return {"code": "RL-MOT", "items": [_dong_don_dang_xem()], "total_considered": 1}, True
    return mau.LOG_CA_DANH_MUC, True


class PhongTheoDonTests(unittest.IsolatedAsyncioTestCase):
    async def _hoi(self, cau_hoi: str, *, mo_hinh_tra=("Được.", "ok", "m"), trang_thai="confirmed"):
        from app.api import consultation_room as phong

        goi = AsyncMock(return_value=mo_hinh_tra)
        ghi: list[dict] = []

        async def _add_turn(**kw):
            ghi.append(kw)
            return {"question": kw["question"]}

        don = {"code": "DH-0001", "title": "Điều dưỡng viện dưỡng lão Tokyo",
               "requirements": {"japanese_required": "N4"}, "reference": {}}
        with patch.object(phong.profiles, "get_by_session", AsyncMock(return_value=_ho_so(trang_thai))), \
             patch.object(phong.job_orders, "get_job_order", AsyncMock(return_value=don)), \
             patch.object(phong.matching_service, "run_matching", _run_matching), \
             patch.object(phong.courses, "list_published", AsyncMock(return_value=mau.KHOA)), \
             patch.object(phong.advisor_turns, "count_turns", AsyncMock(return_value=0)), \
             patch.object(phong.advisor_turns, "list_turns", AsyncMock(return_value=[])), \
             patch.object(phong.advisor_turns, "add_turn", _add_turn), \
             patch.object(phong.session_memory, "ghi_moi_quan_tam", AsyncMock()), \
             patch.object(phong.session_memory, "ghi_da_giai_thich", AsyncMock()), \
             patch.object(phong.session_memory, "lay", AsyncMock(return_value={})), \
             patch.object(qa.client, "sinh_van_ban", goi):
            ra = await phong.hoi_them(PHIEN, "DH-0001", phong.CauHoiBody(question=cau_hoi), _yeu_cau())
        prompt = goi.await_args.args[0] if goi.await_args else ""
        return ra, prompt, ghi

    async def test_cv_da_doc_va_nguon_xuat_hien_trong_ngu_canh(self):
        _, prompt, _ = await self._hoi("Bạn thấy hồ sơ tôi thế nào?")
        self.assertIn("Đọc từ CV, khách chưa xác nhận", prompt)
        self.assertIn("Nguyễn Thị Mẫu", prompt)
        self.assertIn("Khách nói trong hội thoại, chưa xác nhận", prompt)

    async def test_goi_y_don_khac_lay_tu_engine_va_bo_don_dang_xem(self):
        _, prompt, _ = await self._hoi("Đơn này chưa được thì tôi có lựa chọn nào khác?")
        khoi = prompt[prompt.index("[Các đơn khác đang tuyển"):]
        self.assertIn("DH-0016", khoi)
        self.assertNotIn("- DH-0001", khoi)

    async def test_chua_co_nguyen_vong_thi_khong_dien_giai_diem(self):
        _, prompt, _ = await self._hoi("Có đơn nào hợp với tôi hơn không?")
        khoi = prompt[prompt.index("[Các đơn khác đang tuyển"):prompt.index("[Khóa học")]
        self.assertIn("CHƯA được xếp theo mức phù hợp", khoi)
        self.assertNotIn("/100", khoi)

    async def test_ho_so_chua_xac_nhan_thi_khong_doi_chieu_ca_danh_muc(self):
        _, prompt, _ = await self._hoi("Có đơn nào khác không?", trang_thai="extracted")
        self.assertIn("chưa được ứng viên xác nhận", prompt)
        self.assertNotIn("DH-0016", prompt)

    async def test_khoa_hoc_co_nguon_vao_ngu_canh(self):
        _, prompt, _ = await self._hoi("Tôi nên học gì để chuẩn bị?")
        self.assertIn("Học tiếng Nhật tại trung tâm (KH-0001)", prompt)
        self.assertIn("là một chặng trong tổng chi phí chương trình 90.000.000đ", prompt)

    async def test_prompt_cho_phep_nhan_xet_va_co_dau_ngoai_pham_vi(self):
        _, prompt, _ = await self._hoi("Tôi có điểm mạnh gì?")
        self.assertIn("Nhận xét, phân tích và khuyên hướng đi", prompt)
        self.assertIn(qa.DAU_NGOAI_PHAM_VI, prompt)
        self.assertNotIn('trả lời đúng một câu: "Câu này mình chưa có', prompt)

    async def test_mo_hinh_loi_thi_tra_tom_tat_tu_ket_qua_doi_chieu(self):
        ra, _, ghi = await self._hoi(
            "Tôi còn thiếu gì về đơn hàng này?", mo_hinh_tra=(None, "khong_goi_duoc", "m")
        )
        self.assertEqual(ra["source"], "khong_goi_duoc")
        self.assertTrue(ra["answer"].startswith(du_phong.MO_DAU))
        self.assertIn("Tiếng Nhật", ra["answer"])
        # Thiếu thông tin và không đạt là hai thứ khác nhau, kể cả ở bản dự phòng.
        self.assertIn("chưa phải là không đạt", ra["answer"])
        self.assertIn("DH-0016", ra["answer"])
        # Lộ trình học chỉ lấy khóa có thật trong danh mục, không lặp chữ "yêu cầu".
        self.assertIn("KH-0001", ra["answer"])
        self.assertNotIn("yêu cầu yêu cầu", ra["answer"])
        # Câu hỏi không mất, lý do được ghi.
        self.assertEqual(ghi[0]["question"], "Tôi còn thiếu gì về đơn hàng này?")
        self.assertTrue(ghi[0]["ly_do"].startswith("khong_goi_duoc"))

    async def test_nhieu_cach_hoi_cung_mot_nhu_cau_nhan_cung_mot_ngu_canh(self):
        """Không chọn dữ liệu theo từ khóa: đổi cách hỏi thì chỉ dòng câu hỏi đổi.

        Việc hiểu "lựa chọn khác", "còn gì cho tôi", "đơn nào hợp hơn" là việc của mô
        hình. Phần backend đưa đủ dữ liệu liên quan cho mọi cách hỏi, nên không có câu
        nào rơi vào nhánh "không có dữ liệu" chỉ vì khách không dùng đúng chữ.
        """
        cach_hoi = (
            "Đơn này chưa được thì tôi có lựa chọn nào khác?",
            "Ngoài đơn này còn gì cho em không ạ",
            "có đơn nào hợp với mình hơn ko",
        )
        cac_prompt = []
        for c in cach_hoi:
            _, prompt, _ = await self._hoi(c)
            cac_prompt.append(prompt.replace(c, "<CÂU HỎI>"))
        self.assertEqual(len(set(cac_prompt)), 1)
        self.assertIn("DH-0016", cac_prompt[0])

    async def test_nhac_lai_so_khach_vua_noi_khong_bi_loai(self):
        ra, _, _ = await self._hoi(
            "Em 32 tuổi có được không?",
            mo_hinh_tra=("Bạn 32 tuổi, nằm trong mức 20 đến 35 tuổi của đơn này.", "ok", "m"),
        )
        self.assertEqual(ra["source"], "mo_hinh")

    async def test_hau_kiem_loai_thi_ghi_ly_do_tach_khoi_mo_hinh_tu_choi(self):
        _, _, ghi = await self._hoi("Lương bao nhiêu?", mo_hinh_tra=("Lương 999.000 yên.", "ok", "m"))
        self.assertTrue(ghi[0]["ly_do"].startswith("hau_kiem:"))
        _, _, ghi = await self._hoi("Ký túc xá?", mo_hinh_tra=(qa.DAU_NGOAI_PHAM_VI, "ok", "m"))
        self.assertEqual(ghi[0]["ly_do"], "mo_hinh_ngoai_pham_vi")


class AgentCapHoSoTests(unittest.IsolatedAsyncioTestCase):
    async def _hoi(self, *, log, don_dang_xet=None, mo_hinh_tra=('{"reply": "Được."}', "ok", "m")):
        from app.api import agent as agent_api

        goi = AsyncMock(return_value=mo_hinh_tra)
        hs = _ho_so()
        tt = state.suy_ra(profile=hs, log=log, don_dang_xet=don_dang_xet)
        chay = AsyncMock(return_value=mau.LOG_CA_DANH_MUC)
        with patch.object(agent_api, "_nap", AsyncMock(return_value=(hs, tt, log))), \
             patch.object(agent_api.matching_service, "ca_danh_muc_cho_tu_van", chay), \
             patch.object(agent_api.courses, "list_published", AsyncMock(return_value=mau.KHOA)), \
             patch.object(agent_api.advisor_turns, "count_turns", AsyncMock(return_value=0)), \
             patch.object(agent_api.advisor_turns, "list_turns", AsyncMock(return_value=[])), \
             patch.object(agent_api.advisor_turns, "add_turn", AsyncMock()), \
             patch.object(agent_api.session_memory, "lay", AsyncMock(return_value={})), \
             patch.object(agent_api, "_ghi_moc", AsyncMock()), \
             patch.object(qa.client, "sinh_van_ban", goi):
            ra = await agent_api.hoi_tro_ly(PHIEN, agent_api.CauHoiBody(question="Có đơn nào hợp với tôi?"), _yeu_cau())
        return ra, (goi.await_args.args[0] if goi.await_args else ""), chay

    async def test_chua_tung_doi_chieu_ca_danh_muc_thi_goi_engine(self):
        """Khách vào thẳng từ trang một đơn: Agent phải hỏi engine, không tự chọn đơn."""
        _, prompt, chay = await self._hoi(log=None)
        chay.assert_awaited_once()
        self.assertIn("DH-0016", prompt)

    async def test_don_dang_xem_chua_dat_vao_ngu_canh_kem_tieu_chi_truot(self):
        _, prompt, _ = await self._hoi(log=mau.LOG_CA_DANH_MUC, don_dang_xet="DH-0001")
        self.assertIn("[Đơn khách đang xem: DH-0001", prompt)
        self.assertIn("Chưa đạt — Tiếng Nhật", prompt)
        self.assertIn("[Các đơn hồ sơ CHƯA đạt", prompt)
        self.assertIn("KH-0001", prompt)

    async def test_mo_hinh_loi_thi_tom_tat_tu_nhat_ky(self):
        ra, _, _ = await self._hoi(log=mau.LOG_CA_DANH_MUC, mo_hinh_tra=(None, "khong_goi_duoc", "m"))
        self.assertEqual(ra["source"], "khong_goi_duoc")
        self.assertTrue(ra["answer"].startswith(du_phong.MO_DAU))
        self.assertIn("18 đơn", ra["answer"])
        self.assertIn("DH-0016", ra["answer"])
        # Hai lỗi bắt trên trình duyệt 07/10: tên trường máy lọt ra màn hình, và
        # khách chưa học tiếng không được nhắc khóa có sẵn trong danh mục.
        self.assertNotRegex(ra["answer"], r"[a-z]+_[a-z_]+")
        self.assertIn("Lương mong muốn", ra["answer"])
        self.assertIn("KH-0001", ra["answer"])
        self.assertIn("nhận người chưa học", ra["answer"])

    async def test_dau_ngoai_pham_vi_khong_lot_ra_man_hinh(self):
        ra, _, _ = await self._hoi(
            log=mau.LOG_CA_DANH_MUC, mo_hinh_tra=('{"reply": "[NGOAI_PHAM_VI]"}', "ok", "m")
        )
        self.assertEqual(ra["source"], "khong_biet")
        self.assertNotIn(qa.DAU_NGOAI_PHAM_VI, ra["answer"])


class KhoiMoRongTests(unittest.TestCase):
    def test_khong_co_khoa_thi_noi_ro_va_khong_bia(self):
        khoi = khoi_mo_rong.render_khoa_hoc([])
        self.assertIn("chưa có khóa nào được công bố", khoi)
        self.assertNotIn("KH-", khoi)

    def test_xep_hang_duoc_thi_in_diem_va_noi_khong_phai_kha_nang_trung_tuyen(self):
        log = {"total_considered": 2, "items": [{
            **mau.LOG_CA_DANH_MUC["items"][1], "code": "DH-0002", "score": 65,
            "soft_rows": [{"key": "region", "label": "Khu vực", "requirement_text": "Tokyo",
                           "candidate_text": "Tokyo", "outcome": "same_prefecture", "points": 40,
                           "max_points": 40, "missing_field": None, "kind": "mem"}],
        }]}
        khoi = khoi_mo_rong.render_don_khac(log)
        self.assertIn("điểm nguyện vọng 65/100", khoi)
        self.assertIn("KHÔNG phải khả năng trúng tuyển", khoi)

    def test_chi_lay_don_dat_dieu_kien(self):
        khoi = khoi_mo_rong.render_don_khac(mau.LOG_CA_DANH_MUC)
        self.assertIn("DH-0016", khoi)
        self.assertNotIn("- DH-0001", khoi)

    def test_tieu_chi_truot_dem_theo_tieu_chi(self):
        khoi = khoi_mo_rong.render_ly_do_truot(mau.LOG_CA_DANH_MUC)
        self.assertIn("- Tiếng Nhật: 1 đơn", khoi)

    def test_du_phong_ho_so_chua_xac_nhan(self):
        cau = du_phong.theo_ho_so(None, ho_so_da_xac_nhan=False)
        self.assertIn("chưa được xác nhận", cau)
        self.assertTrue(cau.endswith("nhé."))


class NhatKyCaDanhMucTests(unittest.IsolatedAsyncioTestCase):
    """Nhật ký một đơn không được thay thế nhật ký cả danh mục (lỗi đo 07/10: 5 hồ sơ)."""

    async def test_lan_doi_chieu_gan_nhat_bo_qua_nhat_ky_mot_don(self):
        bang = MagicMock()
        bang.find_one = AsyncMock(return_value=None)
        db = MagicMock()
        db.__getitem__.return_value = bang
        with patch.object(recommendation_logs, "get_db", return_value=db):
            await recommendation_logs.latest_for_profile("UV-1")
        loc = bang.find_one.await_args.args[0]
        self.assertEqual(loc["profile_code"], "UV-1")
        self.assertEqual(loc["chi_don"], {"$in": [None]})
        self.assertIn("tu_van_theo_don", loc["trigger"]["$nin"])
        self.assertIn("tu_van_hoi_them", loc["trigger"]["$nin"])

    async def test_nhat_ky_mot_don_mang_ma_don(self):
        from app.services import matching_service as ms

        ghi = AsyncMock(side_effect=lambda d: d)
        with patch.object(ms, "load_pool", AsyncMock(return_value=[{"code": "DH-0001", "status": "open"}])), \
             patch.object(ms.recommendation_logs, "find_cached", AsyncMock(return_value=None)), \
             patch.object(ms.recommendation_logs, "create_log", ghi), \
             patch.object(ms.engine, "match_orders", MagicMock(return_value=MagicMock(
                 as_dict=lambda: {"engine_version": "1", "as_of": "2026-10-07", "total_considered": 1,
                                  "eligible_count": 0, "missing_info": [], "items": []},
                 top=lambda n: []))), \
             patch.object(ms.engine, "build_facts", MagicMock()):
            log, _ = await ms.run_matching({"code": "UV-1", "version": 1}, trigger="tu_van_theo_don", chi_don="DH-0001")
        self.assertEqual(log["chi_don"], "DH-0001")

    async def test_ca_danh_muc_chi_chay_khi_ho_so_da_xac_nhan(self):
        from app.services import matching_service as ms

        chay = AsyncMock(return_value=({"code": "RL"}, False))
        with patch.object(ms, "run_matching", chay):
            self.assertIsNone(await ms.ca_danh_muc_cho_tu_van(_ho_so("extracted"), trigger="t"))
            chay.assert_not_awaited()
            self.assertEqual(await ms.ca_danh_muc_cho_tu_van(_ho_so(profiles.STATUS_CONFIRMED), trigger="t"), {"code": "RL"})
        self.assertIsNone(chay.await_args.kwargs.get("chi_don"))


if __name__ == "__main__":
    unittest.main()
