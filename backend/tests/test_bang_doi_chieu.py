"""Dữ liệu cho bảng đối chiếu hồ sơ với một đơn (yêu cầu 08/10).

Bảng hiện dấu ✓ cho tiêu chí đạt và để trống hai trạng thái còn lại — nhưng đó chỉ
là cách HIỂN THỊ. Backend phải trả đủ ba trạng thái, đủ mọi tiêu chí, theo đúng thứ
tự engine chấm, và không lộ kết quả khi hồ sơ chưa được khách xác nhận.
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import Request

from app.consultation import advice as advice_mod
from app.core.timeutil import local_today
from app.db import candidate_profiles as profile_store
from app.matching import engine
from app.matching.weights import load_weights
from app.services import matching_service
from scripts.seed_job_orders import build_documents

PHIEN = "3db5442f-f6d1-41ee-8928-cf4392392d00"


def _don(ma: str) -> dict:
    return next(d for d in build_documents() if d["code"] == ma)


def _ho_so(trang_thai="confirmed", **fields) -> dict:
    return {
        "code": "UV-BANG01", "session_id": PHIEN, "status": trang_thai, "version": 2,
        "fields": {k: profile_store.cell(v, "user_confirmed") for k, v in fields.items()},
        "preferences": {},
    }


def _cham(don: dict, ho_so: dict) -> engine.MatchItem:
    ket = engine.match_orders([don], engine.build_facts(ho_so, local_today()), weights=load_weights(), as_of=local_today())
    return ket.items[0]


class DongTheoThuTuEngineTests(unittest.TestCase):
    def test_du_moi_tieu_chi_va_dung_thu_tu_engine(self):
        ho_so = _ho_so(japanese_level="chua_hoc", education_level="cao_dang")
        item = _cham(_don("DH-0001"), ho_so)
        kq = advice_mod.as_dict(advice_mod.build(item, required_japanese="N4", profile_level="chua_hoc"))
        self.assertEqual([r["key"] for r in kq["rows"]], [r.key for r in item.hard_rows])
        # Đủ ba trạng thái nằm trong cùng một danh sách — không gộp.
        self.assertTrue({"DAT", "KHONG_DAT", "CHUA_RO"} >= {r["result"] for r in kq["rows"]})
        self.assertIn("KHONG_DAT", {r["result"] for r in kq["rows"]})
        self.assertIn("CHUA_RO", {r["result"] for r in kq["rows"]})

    def test_don_bi_loai_khong_kem_dong_nguyen_vong(self):
        item = _cham(_don("DH-0001"), _ho_so(japanese_level="chua_hoc"))
        kq = advice_mod.as_dict(advice_mod.build(item, required_japanese="N4", profile_level="chua_hoc"))
        self.assertFalse(item.eligible)
        self.assertEqual(kq["soft_rows"], [])

    def test_don_dat_kem_dong_nguyen_vong_de_giai_thich_diem(self):
        ho_so = _ho_so(japanese_level="N3", education_level="dai_hoc", birth_year=local_today().year - 25)
        item = _cham(_don("DH-0001"), ho_so)
        self.assertTrue(item.eligible)
        kq = advice_mod.as_dict(advice_mod.build(item, required_japanese="N4", profile_level="N3"))
        self.assertEqual(len(kq["soft_rows"]), len(item.soft_rows))
        self.assertTrue(all("points" in r and "max_points" in r for r in kq["soft_rows"]))


class DonBiLoaiVanDuDongTests(unittest.IsolatedAsyncioTestCase):
    """Nhật ký rút gọn đơn bị loại (chỉ giữ dòng không đạt) — bảng vẫn phải đủ dòng."""

    async def test_dong_rut_gon_duoc_cham_lai_du_ma_khong_ghi_nhat_ky(self):
        don = _don("DH-0001")
        ho_so = _ho_so(japanese_level="chua_hoc", education_level="cao_dang")
        day_du = _cham(don, ho_so)
        rut_gon = matching_service._gon_lai(day_du.as_dict())
        self.assertLess(len(rut_gon["hard_rows"]), len(day_du.hard_rows))
        with patch.object(matching_service, "load_pool", AsyncMock(return_value=[don])), \
             patch.object(matching_service.recommendation_logs, "create_log", AsyncMock()) as ghi:
            ra = await matching_service.dong_day_du(ho_so, rut_gon, as_of=local_today())
        self.assertEqual([r["key"] for r in ra["hard_rows"]], [r.key for r in day_du.hard_rows])
        self.assertEqual([r["result"] for r in ra["hard_rows"]], [r.result for r in day_du.hard_rows])
        self.assertFalse(ra["eligible"])
        ghi.assert_not_awaited()

    async def test_dong_day_du_san_thi_tra_nguyen(self):
        row = {"code": "DH-0001", "eligible": True, "hard_rows": [{"key": "x"}]}
        with patch.object(matching_service, "load_pool", AsyncMock()) as nap:
            self.assertIs(await matching_service.dong_day_du(_ho_so(), row), row)
        nap.assert_not_awaited()


class ChuaXacNhanThiChuaLoKetQuaTests(unittest.IsolatedAsyncioTestCase):
    async def _hoi(self, trang_thai: str):
        from app.api import consultation_room as phong

        don = _don("DH-0001")
        ho_so = _ho_so(trang_thai, japanese_level="chua_hoc")
        item = matching_service._gon_lai(_cham(don, ho_so).as_dict())  # đúng hình nhật ký lưu

        async def _run(profile, *, trigger, chi_don=None, **_):
            return {"code": "RL-1", "as_of": local_today().isoformat(), "items": [item], "total_considered": 1}, True

        goi = AsyncMock(return_value=("Được.", "ok", "m"))
        with patch.object(phong.profiles, "get_by_session", AsyncMock(return_value=ho_so)), \
             patch.object(phong.job_orders, "get_job_order", AsyncMock(return_value=don)), \
             patch.object(phong.matching_service, "run_matching", _run), \
             patch.object(phong.matching_service, "load_pool", AsyncMock(return_value=[don])), \
             patch.object(phong.courses, "list_published", AsyncMock(return_value=[])), \
             patch.object(phong.advisor_turns, "count_turns", AsyncMock(return_value=0)), \
             patch.object(phong.advisor_turns, "list_turns", AsyncMock(return_value=[])), \
             patch.object(phong.advisor_turns, "add_turn", AsyncMock(return_value={"question": "q"})), \
             patch.object(phong.session_memory, "ghi_moi_quan_tam", AsyncMock()), \
             patch.object(phong.session_memory, "ghi_da_giai_thich", AsyncMock()), \
             patch.object(phong.session_memory, "lay", AsyncMock(return_value={})), \
             patch.object(phong.qa.client, "sinh_van_ban", goi):
            await phong.hoi_them(PHIEN, "DH-0001", phong.CauHoiBody(question="Tôi có hợp đơn này không?"),
                                 Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1)}))
        return goi.await_args.args[0]

    async def test_chua_xac_nhan_thi_tro_ly_khong_nhan_ket_qua(self):
        prompt = await self._hoi("extracted")
        self.assertIn("CHƯA được ứng viên xác nhận", prompt)
        self.assertNotIn("KẾT LUẬN:", prompt)

    async def test_da_xac_nhan_thi_tro_ly_nhan_du_ket_qua(self):
        prompt = await self._hoi("confirmed")
        self.assertIn("KẾT LUẬN:", prompt)


if __name__ == "__main__":
    unittest.main()
