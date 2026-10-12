"""Bộ hành trình E2E trả hồ sơ của chính nó về hàng đợi trước khi xóa tài khoản tạm.

Ngày 06/10 tích lại 129 bản ghi mang người phụ trách là tài khoản tạm đã xóa: mỗi
lượt chạy để lại một hồ sơ đăng ký giao cho consultant B và một yêu cầu hỗ trợ giao
cho A. Đây là vệ sinh bộ đo, không phải chức năng cho khách.
"""
import ast
import asyncio
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from scripts import e2e_hanh_trinh as ht

TAM = ["e2e-tu-van-a@local.test", "e2e-tu-van-b@local.test", "e2e-quan-ly@local.test"]


def _chay(so, *, hs_truoc=None, ht_sua=1):
    db = MagicMock()
    db.recruitment_applications.find_one_and_update = AsyncMock(return_value=hs_truoc)
    db.application_events.insert_one = AsyncMock()
    db.support_requests.update_one = AsyncMock(return_value=MagicMock(modified_count=ht_sua))
    with patch("app.db.common.get_db", return_value=db), patch(
        "app.db.database.init_db", AsyncMock()
    ), patch("app.db.database.close_db", AsyncMock()):
        ra = asyncio.run(ht._tra_ve_hang_doi(TAM, so))
    return ra, db


class TraVeHangDoiTests(unittest.TestCase):
    def test_tra_ca_hai_va_ghi_su_kien(self):
        ra, db = _chay(
            {"ho_so_tuyen": "HS-1", "ho_tro": "HT-1"},
            hs_truoc={"application_code": "HS-1", "assigned_to": TAM[1]},
        )
        self.assertEqual(ra, (1, 1))
        loc_hs, dat_hs = db.recruitment_applications.find_one_and_update.await_args.args
        self.assertEqual(loc_hs, {"application_code": "HS-1", "assigned_to": {"$in": TAM}})
        self.assertIsNone(dat_hs["$set"]["assigned_to"])
        su_kien = db.application_events.insert_one.await_args.args[0]
        self.assertEqual((su_kien["action"], su_kien["details"]["from"]), ("released", TAM[1]))
        loc_ht, dat_ht = db.support_requests.update_one.await_args.args
        self.assertEqual(loc_ht, {"code": "HT-1", "assigned_to": {"$in": TAM}, "status": "dang_xu_ly"})
        self.assertEqual(dat_ht["$set"]["status"], "cho_xu_ly")

    def test_ho_so_khong_con_giao_cho_tai_khoan_tam_thi_khong_dung_toi(self):
        """Điều kiện `assigned_to ∈ tài khoản tạm` nằm trong câu cập nhật: ai đó đã
        nhận hồ sơ thật thì không bị giật lại."""
        ra, db = _chay({"ho_so_tuyen": "HS-1"}, hs_truoc=None)
        self.assertEqual(ra, (0, 0))
        db.application_events.insert_one.assert_not_awaited()

    def test_luot_hong_truoc_khi_co_ma_nao_thi_khong_dung_database(self):
        ra, db = _chay({})
        self.assertEqual(ra, (0, 0))
        db.recruitment_applications.find_one_and_update.assert_not_awaited()


class ThuTuTrongMainTests(unittest.TestCase):
    def test_tra_truoc_xoa_sau_trong_finally(self):
        src = (Path(ht.__file__)).read_text(encoding="utf-8")
        cay = ast.parse(src)
        main = next(n for n in cay.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        thu = next(n for n in ast.walk(main) if isinstance(n, ast.Try) and n.finalbody)
        doan = ast.unparse(thu.finalbody[0])
        self.assertIn("_tra_ve_hang_doi(tu_tao, so)", doan)
        self.assertLess(doan.index("_tra_ve_hang_doi"), doan.index("_xoa_nhan_vien"))


if __name__ == "__main__":
    unittest.main()
