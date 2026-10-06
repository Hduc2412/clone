"""Mã thoát của bộ đo phải nói đúng kết quả — bộ nghiệm thu chốt chỉ đọc mã thoát.

Lỗi chủ đồ án tái hiện ngày 06/10: `nghiem_thu_agent` in "HỎNG" nhưng luôn
`return 0`. Ép một ca thành 0/1 đạt, script vẫn thoát thành công, và
`nghiem_thu_chot` — vốn chỉ đọc mã thoát — có thể kết luận ĐẠT trong khi chất
lượng Agent không đạt.
"""
import asyncio
import unittest
from unittest.mock import patch

from scripts import nghiem_thu_agent as agent
from scripts import nghiem_thu_chot as chot

VAN_TAY = "abc123"


def bang_du(model="m-chinh"):
    """Một bảng đo đủ mọi ca trong BO_CA, đúng hình dạng file thật."""
    return {
        f"{model}::{VAN_TAY}::{ca.ma}": {
            "ma": ca.ma, "model": model, "cau_hoi": ca.cau_hoi, "cau_tra_loi": "…",
            "nguon": "mo_hinh", "intent": "", "de_xuat": [], "chot_chan_da_loai": [],
        }
        for ca in agent.BO_CA
    }


def chay_main(bang, *, hong=(), argv=("x", "--gioi-han=0")):
    """Chạy `main()` thật với bảng đo cho trước; ca nào trong `hong` chấm ra hỏng."""
    def cham(ca, ra):
        return (ra["ma"] not in hong), ([f"ép hỏng {ra['ma']}"] if ra["ma"] in hong else [])

    with patch.object(agent, "doc_bang", lambda: dict(bang)), patch.object(
        agent, "dau_van_tay", lambda: VAN_TAY
    ), patch.object(agent, "cham_tu_ban_ghi", cham), patch.object(
        agent, "ghi_bang", lambda b: None
    ), patch.object(agent.settings, "advisor_model", "m-chinh"), patch(
        "sys.argv", list(argv)
    ), patch("builtins.print"):
        return asyncio.run(agent.main())


class MaThoatAgentTests(unittest.TestCase):
    def test_mot_ca_hong_thi_ma_thoat_1(self):
        """Đúng thao tác tái hiện: đủ sáu ca, ép MỘT ca hỏng."""
        mot_ca = agent.BO_CA[0].ma
        self.assertEqual(chay_main(bang_du(), hong={mot_ca}), 1)

    def test_du_ca_va_deu_dat_thi_ma_thoat_0(self):
        self.assertEqual(chay_main(bang_du()), 0)

    def test_thieu_mot_ca_thi_chua_do_du_khong_phai_dat(self):
        """`--gioi-han=0` không gọi mô hình — ca thiếu trong bảng là CHƯA ĐO."""
        b = bang_du()
        b.pop(next(iter(b)))
        self.assertEqual(chay_main(b), agent.KHONG_DO_DUOC)

    def test_bang_rong_thi_chua_do_du(self):
        self.assertEqual(chay_main({}), agent.KHONG_DO_DUOC)

    def test_hong_thang_chua_do(self):
        """Một ca hỏng là kết luận chắc chắn, kể cả khi ca khác chưa đo."""
        b = bang_du()
        bo = next(iter(b))
        b.pop(bo)
        con = next(r["ma"] for k, r in b.items())
        self.assertEqual(chay_main(b, hong={con}), 1)


class KetLuanTests(unittest.TestCase):
    def test_bang_su_that(self):
        k = agent.ket_luan
        self.assertEqual(k(so_cham=6, so_hong=0, chua_do=[]), 0)
        self.assertEqual(k(so_cham=6, so_hong=1, chua_do=[]), 1)
        self.assertEqual(k(so_cham=5, so_hong=1, chua_do=["X"]), 1)
        self.assertEqual(k(so_cham=5, so_hong=0, chua_do=["X"]), agent.KHONG_DO_DUOC)
        self.assertEqual(k(so_cham=0, so_hong=0, chua_do=[]), agent.KHONG_DO_DUOC)


class TongKetNghiemThuChotTests(unittest.TestCase):
    """Bộ chốt gộp mã thoát của từng bộ đo thành một kết luận."""

    def test_mot_bo_hong_la_hong(self):
        self.assertEqual(chot.tong_ket([0, 0, 1, 0], hop_le=True), 1)

    def test_bo_agent_chua_do_du_khong_bi_tinh_la_hong_cung_khong_la_dat(self):
        """Trước đây chỉ bộ hành trình được hiểu mã 3; bộ khác trả 3 là thành HỎNG."""
        self.assertEqual(chot.tong_ket([0, 3, 0], hop_le=True), chot.KHONG_DO_DUOC)

    def test_hong_thang_chua_do(self):
        self.assertEqual(chot.tong_ket([3, 1], hop_le=True), 1)

    def test_dau_van_tay_lech_thi_khong_hop_le_du_moi_bo_dat(self):
        self.assertEqual(chot.tong_ket([0, 0], hop_le=False), 1)

    def test_tat_ca_dat(self):
        self.assertEqual(chot.tong_ket([0, 0, 0], hop_le=True), 0)

    def test_hai_quy_uoc_ma_3_trung_nhau(self):
        """Hai script cùng định nghĩa mã "chưa đo được" — lệch nhau là gộp sai."""
        from scripts import e2e_hanh_trinh

        self.assertEqual(agent.KHONG_DO_DUOC, chot.KHONG_DO_DUOC)
        self.assertEqual(e2e_hanh_trinh.KHONG_DO_DUOC, chot.KHONG_DO_DUOC)


if __name__ == "__main__":
    unittest.main()


class KetLuanHanhTrinhTests(unittest.TestCase):
    """Bộ hành trình: mục "chưa đo được" không được thành mã 0.

    Lượt chốt 06/10 14:31 báo ĐẠT trong khi lời tư vấn là câu ghép sẵn "trợ lý đang
    bận" — model chính hết giờ chờ, model dự phòng 503. Bộ đo in dấu `?` rồi vẫn
    thoát 0.
    """

    def test_mo_hinh_khong_tra_loi_thi_chua_do_duoc(self):
        from scripts import e2e_hanh_trinh as ht

        self.assertEqual(
            ht.ket_luan(hong=[], khong_do=["hỏi trợ lý: mô hình không trả lời"]),
            ht.KHONG_DO_DUOC,
        )

    def test_hong_thang_chua_do(self):
        from scripts import e2e_hanh_trinh as ht

        self.assertEqual(ht.ket_luan(hong=["x"], khong_do=["y"]), 1)

    def test_khong_gi_thi_dat(self):
        from scripts import e2e_hanh_trinh as ht

        self.assertEqual(ht.ket_luan(hong=[], khong_do=[]), 0)

    def test_buoc_hoi_tro_ly_ghi_nhan_khong_goi_duoc(self):
        """Đọc mã nguồn: nhánh `khong_goi_duoc` của bước hỏi phải đưa vào `khong_do`."""
        import ast
        from pathlib import Path

        src = (Path(__file__).resolve().parents[1] / "scripts" / "e2e_hanh_trinh.py").read_text(encoding="utf-8")
        i = src.index('if ra.get("source") == "khong_goi_duoc":')
        doan = src[i:i + 900]
        self.assertIn('so.setdefault("khong_do", []).append(', doan)
        ast.parse(src)
