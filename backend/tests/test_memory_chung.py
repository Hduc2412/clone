"""Bộ nhớ dùng chung giữa khung chat và engine tư vấn.

Ca quan trọng nhất trong file này không phải ca chức năng mà là
`CauTraLoiKhongDiQuaBoNhoTests`: nó cưỡng chế luật cứng của gói — **bộ nhớ chở
câu hỏi, không chở câu trả lời**.

Nếu câu trả lời của khung chat lọt sang làm dữ liệu đầu vào cho engine tư vấn thì
một câu bịa ở bên phụ trợ sẽ được bên chính đọc như sự thật, nhắc lại với giọng
chắc chắn hơn, và tới lượt thứ ba thì không ai truy được nó bắt nguồn từ đâu.
Một lần bịa tự bồi thành hồ sơ. Luật ấy dễ nói trong tài liệu và rất dễ bị phá
bằng một dòng code "cho tiện", nên phải có ca kiểm thử canh.
"""
import ast
import pathlib
import unittest

from app.db import session_memory
from app.memory import render, topics


GOI = pathlib.Path(__file__).resolve().parent.parent / "app" / "memory"


class PhanLoaiChuDeTests(unittest.TestCase):
    def test_nhan_ra_chu_de_thuong_gap(self):
        self.assertEqual(topics.phan_loai("Học phí bao nhiêu ạ?"), topics.CHI_PHI)
        self.assertEqual(topics.phan_loai("Lương một tháng bao nhiêu yên"), topics.LUONG)
        self.assertEqual(topics.phan_loai("Em chưa học tiếng Nhật"), topics.TIENG_NHAT)

    def test_chay_duoc_khi_khach_go_khong_dau(self):
        """Phần lớn ứng viên gõ trên điện thoại và bỏ dấu."""
        self.assertEqual(topics.phan_loai("hoc phi bao nhieu"), topics.CHI_PHI)
        self.assertEqual(topics.phan_loai("bao nhieu tuoi thi di duoc"), topics.TUOI)

    def test_khong_khop_thi_tra_none_chu_khong_doan(self):
        """Thà bỏ sót còn hơn gán sai.

        Gán sai một nhãn làm bên kia tưởng chủ đề đã bàn rồi và bỏ qua đúng thứ
        khách đang lo. Bỏ sót thì chỉ làm bộ nhớ nghèo đi.
        """
        self.assertIsNone(topics.phan_loai("Tokyo dạo này thời tiết thế nào"))
        self.assertIsNone(topics.phan_loai(""))
        self.assertIsNone(topics.phan_loai("   "))

    def test_hoi_ve_tien_thi_ra_chi_phi_chu_khong_ra_tieng_nhat(self):
        """'học phí' có chữ 'học' nhưng thứ khách hỏi là tiền."""
        self.assertEqual(topics.phan_loai("học phí khóa tiếng Nhật"), topics.CHI_PHI)

    def test_moi_nhan_deu_co_chu_tieng_viet(self):
        """Nhãn đi thẳng vào prompt, nên không được để lọt mã máy."""
        for chu_de in topics.NHAN:
            self.assertNotIn("_", topics.nhan_cua(chu_de))


class KhoiChuChoTungBenTests(unittest.TestCase):
    def test_chua_co_gi_thi_khoi_rong(self):
        """Tiêu đề không có nội dung chỉ tốn chỗ và mời mô hình tự điền vào."""
        self.assertEqual(render.render(None, cho=session_memory.BEN_CHAT), "")
        self.assertEqual(render.render({}, cho=session_memory.BEN_TU_VAN), "")

    def test_khung_chat_biet_don_khach_dang_xem(self):
        khoi = render.render(
            {"job_order_code": "DH-0001"}, cho=session_memory.BEN_CHAT
        )
        self.assertIn("DH-0001", khoi)
        # Phải kèm lời dặn không lấy số của đơn khác — đây chính là lỗi mà việc
        # dò tỉnh trong `rag/job_lookup.py` hay mắc.
        self.assertIn("đơn khác", khoi)

    def test_engine_tu_van_thay_moi_lo_hoi_di_hoi_lai(self):
        khoi = render.render(
            {
                "moi_quan_tam": [
                    {"chu_de": topics.CHI_PHI, "so_lan": 3,
                     "cau_gan_nhat": "có trả góp được không ạ"},
                    {"chu_de": topics.LUONG, "so_lan": 1},
                ]
            },
            cho=session_memory.BEN_TU_VAN,
        )
        self.assertIn("chi phí", khoi)
        self.assertIn("3 lần", khoi)
        self.assertIn("có trả góp được không ạ", khoi)
        # Hỏi một lần thì không phải mối lo, xuống dòng phụ.
        self.assertIn("cũng đã hỏi qua", khoi)

    def test_hoi_lai_thi_nhac_dung_lap_lai_cau_cu(self):
        khoi = render.render(
            {"moi_quan_tam": [{"chu_de": topics.CHI_PHI, "so_lan": 4}]},
            cho=session_memory.BEN_TU_VAN,
        )
        self.assertIn("đừng lặp lại", khoi.casefold())

    def test_thu_tu_tat_dinh(self):
        """Hai lượt dựng phải ra cùng một chuỗi, kể cả khi đầu vào xáo trộn."""
        quan_tam = [
            {"chu_de": topics.LUONG, "so_lan": 2, "lan_cuoi": "2026-09-28"},
            {"chu_de": topics.CHI_PHI, "so_lan": 2, "lan_cuoi": "2026-09-28"},
            {"chu_de": topics.TUOI, "so_lan": 2, "lan_cuoi": "2026-09-28"},
        ]
        mot = render.render({"moi_quan_tam": quan_tam}, cho=session_memory.BEN_TU_VAN)
        hai = render.render(
            {"moi_quan_tam": list(reversed(quan_tam))}, cho=session_memory.BEN_TU_VAN
        )
        self.assertEqual(mot, hai)

    def test_moi_khoi_deu_kem_loi_dan_dung_suy_ra_cau_tra_loi(self):
        """Mô hình đọc 'đã giải thích về chi phí' rất dễ tự nghĩ ra một con số."""
        for cho in (session_memory.BEN_CHAT, session_memory.BEN_TU_VAN):
            khoi = render.render(
                {
                    "job_order_code": "DH-0001",
                    "moi_quan_tam": [{"chu_de": topics.CHI_PHI, "so_lan": 2}],
                    "da_giai_thich": [
                        {"chu_de": topics.CHI_PHI, "ben": session_memory.BEN_TU_VAN},
                        {"chu_de": topics.LUONG, "ben": session_memory.BEN_CHAT},
                    ],
                },
                cho=cho,
            )
            self.assertIn("không chứa nội dung đã trả lời", khoi)
            self.assertIn("Đừng suy ra câu trả lời từ đây", khoi)

    def test_moi_ben_chi_thay_phan_ben_kia_da_giai_thich(self):
        du_lieu = {
            "da_giai_thich": [
                {"chu_de": topics.CHI_PHI, "ben": session_memory.BEN_TU_VAN},
                {"chu_de": topics.SUC_KHOE, "ben": session_memory.BEN_CHAT},
            ]
        }
        cho_chat = render.render(du_lieu, cho=session_memory.BEN_CHAT)
        cho_tu_van = render.render(du_lieu, cho=session_memory.BEN_TU_VAN)
        self.assertIn("chi phí", cho_chat)
        self.assertNotIn("sức khỏe", cho_chat)
        self.assertIn("sức khỏe", cho_tu_van)
        self.assertNotIn("chi phí", cho_tu_van)


class CauTraLoiKhongDiQuaBoNhoTests(unittest.TestCase):
    """Luật cứng của gói, cưỡng chế bằng mã nguồn chứ không bằng lời dặn."""

    def test_ham_ghi_khong_co_tham_so_nao_nhan_cau_tra_loi(self):
        """Không có cửa để truyền câu trả lời vào thì không ai lỡ tay truyền được.

        Đây là cách rẻ nhất để giữ luật: đóng cửa, thay vì dặn nhau đừng đi qua.
        """
        import inspect

        for ten in ("ghi_moi_quan_tam", "ghi_da_giai_thich"):
            tham_so = set(inspect.signature(getattr(session_memory, ten)).parameters)
            self.assertNotIn("cau_tra_loi", tham_so)
            self.assertNotIn("answer", tham_so)
            self.assertNotIn("noi_dung", tham_so)

    def test_ghi_da_giai_thich_chi_nhan_nhan_chu_de(self):
        import inspect

        tham_so = set(inspect.signature(session_memory.ghi_da_giai_thich).parameters)
        self.assertEqual(tham_so, {"session_id", "chu_de", "ben"})

    def test_khoi_bo_nho_khong_nam_trong_khoi_cho_phep_cua_chot_hau_kiem(self):
        """Một con số lọt vào bộ nhớ cũng không được phép đi ra ngoài.

        `qa.kiem_tra` loại mọi con số không có trong khối dữ liệu cho phép. Nếu
        ai đó nối `bo_nho` vào khối ấy "cho tiện" thì chốt chặn thủng: câu hỏi cũ
        của khách trở thành nguồn hợp lệ để mô hình trích số ra dùng.
        """
        nguon = (
            pathlib.Path(__file__).resolve().parent.parent
            / "app" / "advisor" / "qa.py"
        ).read_text(encoding="utf-8")
        dong = next(
            d for d in nguon.splitlines() if d.strip().startswith("khoi_cho_phep")
        )
        self.assertNotIn("bo_nho", dong)


class GoiBoNhoKhongPhuThuocBenNaoTests(unittest.TestCase):
    """`app/memory` phải nằm dưới cả hai bên, không phải là cây cầu giữa chúng.

    Cho nó import một bên là mở đúng con đường vòng qua ranh giới mà
    `test_advisor_boundary.py` đang canh: engine tư vấn không import khung chat,
    nhưng cả hai cùng import bộ nhớ, và bộ nhớ thì import khung chat.
    """

    CAM = (
        "app.advisor",
        "app.llm",
        "app.rag",
        "app.conversation",
        "app.services.chat_service",
        "app.api",
        "ingestion",
    )

    def test_khong_import_gi_tu_hai_ben(self):
        tep_da_quet = 0
        for tep in sorted(GOI.glob("*.py")):
            tep_da_quet += 1
            cay = ast.parse(tep.read_text(encoding="utf-8"))
            ten: set[str] = set()
            for node in ast.walk(cay):
                if isinstance(node, ast.Import):
                    ten.update(a.name for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    ten.add(node.module)
            for t in ten:
                for cam in self.CAM:
                    self.assertFalse(
                        t == cam or t.startswith(f"{cam}."),
                        f"{tep.name} import {t!r} — bộ nhớ chung phải nằm dưới cả "
                        f"hai bên, không được phụ thuộc bên nào.",
                    )
        # Chặn trường hợp bộ kiểm thử xanh chỉ vì thư mục rỗng.
        self.assertGreaterEqual(tep_da_quet, 3)

    def test_khong_cham_database(self):
        """`app/memory` là phần thuần; chỗ chạm database là `app/db/session_memory.py`."""
        for tep in sorted(GOI.glob("*.py")):
            noi_dung = tep.read_text(encoding="utf-8")
            self.assertNotIn("motor", noi_dung, f"{tep.name} chạm tới database")
            self.assertNotIn("get_db", noi_dung, f"{tep.name} chạm tới database")


if __name__ == "__main__":
    unittest.main()
