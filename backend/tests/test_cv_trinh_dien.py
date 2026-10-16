"""Bộ cặp CV – đơn dùng để trình diễn bộ đối chiếu (15/10/2026).

Mỗi cặp chạy **đúng bộ đối chiếu của hệ thống** trên hồ sơ lấy từ đáp án của CV mẫu
và đơn mẫu, không gọi mô hình. Bảng dùng khi trình diễn ở
`tests/fixtures/cv_thuc_te/BO_TRINH_DIEN.md`; ca kiểm thử này giữ cho bảng ấy đúng —
ai đổi đơn mẫu hay quy tắc làm lệch kịch bản trình diễn thì đỏ ngay.

Hồ sơ dựng từ đáp án, tức là coi như khách đã xác nhận đúng những gì CV ghi. Khi đọc
CV bằng mô hình thật, trường nào bộ đọc chưa nhận (ví dụ số năm kinh nghiệm phải tự
tính từ khoảng thời gian) sẽ thành "chưa rõ", và "chưa rõ" không loại ai.
"""
import json
import unittest
from pathlib import Path

from app.core.timeutil import local_today
from app.matching import engine
from app.matching.weights import load_weights
from scripts.seed_job_orders import build_documents

FX = Path(__file__).resolve().parent / "fixtures"
CV = {e["file"]: e for e in
      json.loads((FX / "cv" / "dap_an.json").read_text(encoding="utf-8"))
      + json.loads((FX / "cv_thuc_te" / "dap_an.json").read_text(encoding="utf-8"))}
NGUYEN_VONG = ("desired_prefecture", "desired_region_group", "desired_employer_type",
               "salary_expectation_jpy", "budget_vnd")

# (CV, đơn, kết quả, tiêu chí trượt, tiêu chí chưa rõ)
CAP = [
    # Đạt hẳn
    ("15_bui_thi_thanh_tam_kem_thu.pdf", "DH-0001", True, [], []),
    ("20_dang_thi_my_linh_tham_chieu.pdf", "DH-0001", True, [], []),
    ("23_pham_thi_ngoc_anh_tieng_anh.pdf", "DH-0001", True, [], []),
    ("30_ha_thi_lan_anh_ho_sinh.pdf", "DH-0001", True, [], []),
    # Đạt sơ bộ, còn mục chưa rõ — hệ thống hỏi thêm, không loại
    ("18_dinh_van_long_nat_test.pdf", "DH-0001", True, [], ["japanese"]),
    ("24_tran_thi_bich_rat_ngan.docx", "DH-0001", True, [], ["japanese", "education"]),
    # Trượt đúng một tiêu chí — mỗi tiêu chí bắt buộc một ví dụ
    ("09_pham_thi_thu_trang.pdf", "DH-0001", False, ["japanese"], []),
    ("26_ta_van_tung_lien_thong.pdf", "DH-0001", False, ["education"], []),
    ("04_pham_minh_tuan.pdf", "DH-0001", False, ["age"], []),
    ("26_ta_van_tung_lien_thong.pdf", "DH-0003", False, ["gender"], []),
    ("16_luong_thi_kim_oanh.docx", "DH-0014", False, ["experience"], []),
    ("15_bui_thi_thanh_tam_kem_thu.pdf", "DH-0017", False, ["deadline"], []),
    ("20_dang_thi_my_linh_tham_chieu.pdf", "DH-0019", False, ["status"], []),
    # Trượt nhiều tiêu chí
    ("19_phan_van_hai_40_tuoi.docx", "DH-0001", False, ["japanese", "education", "age"], []),
    ("13_nguyen_van_duc_khong_dau.docx", "DH-0001", False, ["japanese", "education"], []),
    # Cùng một CV: trượt đơn này nhưng đạt đơn khác — đối chiếu theo từng đơn
    ("09_pham_thi_thu_trang.pdf", "DH-0007", True, [], []),
    ("26_ta_van_tung_lien_thong.pdf", "DH-0004", True, [], []),
    ("16_luong_thi_kim_oanh.docx", "DH-0001", True, [], []),
]


def _ket_qua(file: str, ma_don: str):
    gt = {k: v for k, v in CV[file]["expected"].items() if v is not None and k not in NGUYEN_VONG}
    ho_so = {"fields": {k: {"value": v, "source": "user_confirmed"} for k, v in gt.items()}, "preferences": {}}
    hom_nay = local_today()
    facts = engine.build_facts(ho_so, hom_nay)
    don = [d for d in build_documents() if d["code"] == ma_don]
    kq = engine.match_orders(don, facts, weights=load_weights(), as_of=hom_nay)
    return kq.items[0]


class CapTrinhDienTests(unittest.TestCase):
    def test_moi_cap_ra_dung_ket_qua_va_dung_ly_do(self):
        for file, ma_don, dat, truot, chua_ro in CAP:
            with self.subTest(file, don=ma_don):
                item = _ket_qua(file, ma_don)
                self.assertEqual(item.eligible, dat)
                self.assertEqual(sorted(r.key for r in item.hard_rows if r.result == engine.KHONG_DAT), sorted(truot))
                self.assertEqual(sorted(r.key for r in item.hard_rows if r.result == engine.CHUA_RO), sorted(chua_ro))

    def test_phu_du_bay_tieu_chi_bat_buoc(self):
        """Mỗi tiêu chí bắt buộc có ít nhất một cặp trượt đúng riêng tiêu chí ấy."""
        don_tieu_chi = {c[3][0] for c in CAP if not c[2] and len(c[3]) == 1}
        self.assertEqual(don_tieu_chi, {"japanese", "education", "age", "gender", "experience", "deadline", "status"})


if __name__ == "__main__":
    unittest.main()
