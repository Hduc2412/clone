"""Script dọn dữ liệu E2E chỉ được xóa phiên CÓ CĂN CỨ — không bao giờ theo nội dung khách nhập.

Rà soát 06/10 của chủ đồ án: bản đầu đánh dấu xóa mọi phiên có câu nhắn *"Em muốn
gặp để hỏi thêm về đơn này."* — một câu khách thật hoàn toàn có thể gõ. Nay căn
cứ chỉ là sổ ghi danh (bộ đo tự khai lúc mở phiên) và danh sách người duyệt lập.
"""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from app.core.config import settings
from scripts import don_du_lieu_e2e as don
from scripts import so_phien_e2e

T0 = datetime(2026, 10, 6, 4, 0, tzinfo=timezone.utc)


class _SoTam(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()) / "so_phien.jsonl"
        vá = patch.object(so_phien_e2e, "duong_so", lambda: self.tmp)
        vá.start()
        self.addCleanup(vá.stop)

    def viet_so(self, *dong):
        self.tmp.write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in dong), encoding="utf-8")


def dong_so(sid, *, db=None, luc=T0):
    return {"session_id": sid, "bo_do": "e2e_hanh_trinh", "lan_chay": "x", "url": "u",
            "db": db or settings.mongodb_db_name, "ghi_luc": luc.isoformat()}


class CanCuTests(_SoTam):
    def test_chi_so_ghi_danh_va_danh_sach(self):
        self.viet_so(dong_so("phien-so"))
        can = don.can_cu(["phien-duyet"], tu_ngay=T0)
        self.assertEqual(set(can), {"phien-so", "phien-duyet"})

    def test_phien_mang_dau_hieu_ma_khong_co_trong_so_thi_khong_duoc_chon(self):
        """Đúng kịch bản chủ đồ án nêu: khách thật gõ trùng câu nhắn của bộ đo.

        `can_cu` không nhìn dữ liệu nào cả — nên không có cách nào để một câu
        nhắn, một cái tên, hay một file trùng nội dung đưa phiên vào danh sách xóa.
        """
        self.viet_so(dong_so("phien-bo-do"))
        can = don.can_cu([], tu_ngay=T0)
        self.assertNotIn("phien-khach-that-go-trung-cau", can)
        self.assertEqual(set(can), {"phien-bo-do"})

    def test_so_cua_database_khac_bi_bo_qua(self):
        self.viet_so(dong_so("phien-db-khac", db="mot_db_khac"), dong_so("phien-db-nay"))
        self.assertEqual(set(don.can_cu([], tu_ngay=T0)), {"phien-db-nay"})

    def test_khong_co_so_thi_khong_co_gi(self):
        self.assertEqual(don.can_cu([], tu_ngay=T0), {})


class ChotThoiDiemTests(_SoTam):
    """Phiên trong sổ: mọi bản ghi phải tạo SAU lúc ghi danh — trừ hao DUNG_SAI."""

    def _can(self):
        self.viet_so(dong_so("p1", luc=T0))
        return don.can_cu([], tu_ngay=T0 - timedelta(days=30))

    def test_ban_ghi_sau_luc_ghi_danh_thi_qua(self):
        bg = {"candidate_profiles": [{"session_id": "p1", "code": "UV-1", "created_at": T0 + timedelta(minutes=1)}]}
        self.assertEqual(don.kiem_thoi_diem(bg, self._can()), [])

    def test_ban_ghi_cu_hon_luc_ghi_danh_thi_dung(self):
        """Mã phiên trùng với một phiên cũ hơn — không phải phiên bộ đo vừa mở."""
        bg = {"candidate_profiles": [{"session_id": "p1", "code": "UV-1", "created_at": T0 - timedelta(hours=1)}]}
        self.assertEqual(len(don.kiem_thoi_diem(bg, self._can())), 1)

    def test_nhat_ky_xet_theo_moc_cua_phien_qua_ma_ho_so(self):
        """Nhật ký không mang session_id thì lần qua mã hồ sơ để lấy đúng mốc."""
        bg = {
            "candidate_profiles": [{"session_id": "p1", "code": "UV-1", "created_at": T0 + timedelta(minutes=1)}],
            "recommendation_logs": [{"profile_code": "UV-1", "code": "RL-1", "created_at": T0 - timedelta(hours=2)}],
        }
        loi = don.kiem_thoi_diem(bg, self._can())
        self.assertEqual(len(loi), 1)
        self.assertIn("RL-1", loi[0])

    def test_khong_co_gio_tao_thi_dung(self):
        bg = {"support_requests": [{"session_id": "p1", "code": "HT-1"}]}
        self.assertEqual(len(don.kiem_thoi_diem(bg, self._can())), 1)


class SoGhiDanhTests(_SoTam):
    def test_ghi_roi_doc(self):
        so_phien_e2e.ghi("abc", bo_do="e2e_xuyen_suot", url="http://127.0.0.1:8020")
        ds = so_phien_e2e.doc()
        self.assertEqual(ds[0]["session_id"], "abc")
        self.assertEqual(ds[0]["db"], settings.mongodb_db_name)

    def test_gach_dung_phien_da_don(self):
        for s in ("a", "b", "c"):
            so_phien_e2e.ghi(s, bo_do="x", url="u")
        self.assertEqual(so_phien_e2e.bo_khoi_so({"a", "c"}), 2)
        self.assertEqual([d["session_id"] for d in so_phien_e2e.doc()], ["b"])


class DanhSachDuyetTests(unittest.TestCase):
    def test_bo_ghi_chu_va_dong_trong(self):
        f = Path(tempfile.mkdtemp()) / "ds.txt"
        f.write_text("# phiên thử lịch dựng tay 05/10\nabc  # Thử Nghiệm Lịch\n\n  def\n", encoding="utf-8")
        self.assertEqual(don.doc_danh_sach(str(f)), ["abc", "def"])


class BoDoGhiDanhTruocKhiTaoDuLieuTests(unittest.TestCase):
    """Ghi danh phải nằm NGAY sau lúc mở phiên — trước mọi lời gọi tạo dữ liệu.

    Ghi muộn thì một lượt chạy nổ giữa chừng để lại dữ liệu mà sổ không biết.
    """

    def test_hai_bo_do(self):
        goc = Path(__file__).resolve().parents[1] / "scripts"
        for ten, lenh_tao_dau in (("e2e_xuyen_suot.py", "/public/profiles"), ("e2e_hanh_trinh.py", "/public/documents/")):
            with self.subTest(bo_do=ten):
                src = (goc / ten).read_text(encoding="utf-8")
                mo = src.index('sid = phien["session_id"]')
                ghi = src.index("so_phien_e2e.ghi(sid", mo)
                tao = src.index(lenh_tao_dau, mo)
                self.assertLess(ghi, tao, f"{ten}: ghi danh sau lời gọi tạo dữ liệu đầu tiên")


if __name__ == "__main__":
    unittest.main()
