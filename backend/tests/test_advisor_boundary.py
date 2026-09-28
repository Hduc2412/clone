"""Ranh giới giữa engine tư vấn và khung chat — cưỡng chế bằng mã nguồn.

Hệ tư vấn là **hệ chính** của đề tài; khung chat hỏi đáp là **phần phụ trợ**.
Hai việc khác nhau, và chúng phải hỏng độc lập với nhau.

Tuyên bố như vậy trong tài liệu thì dễ. Bộ này làm cho nó thành thật: quét mã
nguồn của gói `app/advisor` và bắt mọi đường dây nối sang phía chat. Một ngày
nào đó sẽ có người thấy `app/llm/gemini.py` đã có sẵn hàm gọi mô hình rồi import
cho nhanh — lúc đó ca kiểm thử này đỏ, và người ấy phải dừng lại nghĩ xem mình
đang phá cái gì.
"""
import ast
import pathlib
import unittest


GOI = pathlib.Path(__file__).resolve().parent.parent / "app" / "advisor"

# Những gói thuộc về khung chat. Engine tư vấn không được chạm tới cái nào.
#
# `app.llm.gemini` dùng `requests` đồng bộ với `time.sleep` để thử lại — gọi nó
# từ một endpoint bất đồng bộ sẽ đóng băng cả event loop trong lúc chờ. Nhưng lý
# do chính không phải kỹ thuật: dùng chung thì hai bên không còn hỏng độc lập.
CAM_IMPORT = (
    "app.llm",
    "app.rag",
    "app.conversation",
    "app.services.chat_service",
    "app.api.chat",
    "ingestion",
)


def _cac_import(duong_dan: pathlib.Path) -> set[str]:
    cay = ast.parse(duong_dan.read_text(encoding="utf-8"))
    ten: set[str] = set()
    for node in ast.walk(cay):
        if isinstance(node, ast.Import):
            ten.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            ten.add(node.module)
    return ten


class RanhGioiVoiKhungChatTests(unittest.TestCase):
    def test_goi_advisor_khong_import_gi_tu_phia_chat(self):
        for tep in sorted(GOI.glob("*.py")):
            for ten in _cac_import(tep):
                for cam in CAM_IMPORT:
                    self.assertFalse(
                        ten == cam or ten.startswith(f"{cam}."),
                        f"{tep.name} import {ten!r} — engine tư vấn phải chạy độc lập "
                        f"với khung chat. Cần gọi mô hình thì dùng "
                        f"`app/advisor/client.py`.",
                    )

    def test_co_it_nhat_mot_file_trong_goi(self):
        """Chặn trường hợp bộ kiểm thử xanh chỉ vì thư mục rỗng."""
        self.assertGreater(len(list(GOI.glob("*.py"))), 1)


class KhoaVaHanMucRiengTests(unittest.TestCase):
    """Dùng chung khóa là dùng chung hạn mức.

    Hậu quả chỉ lộ ra vào đúng lúc tệ nhất — giữa buổi demo, khi chat vừa ngốn
    hết quota và phần tư vấn im lặng quay về bản ghép sẵn.
    """

    def test_client_doc_khoa_rieng_truoc(self):
        from unittest.mock import patch

        from app.advisor import client
        from app.core.config import settings

        with patch.object(settings, "advisor_api_key", "khoa-rieng"), \
             patch.object(settings, "gemini_api_key", "khoa-chung"):
            self.assertEqual(client.api_key(), "khoa-rieng")

    def test_chua_khai_khoa_rieng_thi_quay_ve_khoa_chung_va_canh_bao(self):
        from unittest.mock import patch

        from app.advisor import client
        from app.core.config import settings

        # Cảnh báo chỉ ghi một lần cho cả vòng đời tiến trình, nên phải đặt lại
        # cờ thì ca này mới kiểm được.
        client._da_canh_bao_dung_chung = False
        with patch.object(settings, "advisor_api_key", ""), \
             patch.object(settings, "gemini_api_key", "khoa-chung"):
            with self.assertLogs("app.advisor.client", level="WARNING") as ghi:
                self.assertEqual(client.api_key(), "khoa-chung")
        self.assertIn("dùng chung", "\n".join(ghi.output))

    def test_tat_engine_thi_khong_goi_mo_hinh(self):
        from unittest.mock import patch

        from app.advisor import client
        from app.core.config import settings

        with patch.object(settings, "advisor_enabled", False), \
             patch.object(settings, "advisor_api_key", "khoa-rieng"):
            self.assertFalse(client.san_sang())


class DiaChiApiRiengTests(unittest.TestCase):
    def test_duong_cua_engine_nam_duoi_tu_van_v1(self):
        """Nhìn danh sách đường là biết đâu là hệ chính, đâu là phụ trợ."""
        from main import app

        duong = [
            route.path
            for route in app.routes
            if getattr(route, "path", "").startswith("/tu-van")
        ]
        self.assertTrue(duong, "không thấy đường nào của engine tư vấn")
        for p in duong:
            self.assertTrue(
                p.startswith("/tu-van/v1/"),
                f"{p} thiếu số phiên bản — đổi hình dạng dữ liệu sẽ làm gãy bản đang chạy",
            )



class CanhBaoDungChungKhoaTests(unittest.TestCase):
    """Dùng chung khóa là dùng chung hạn mức — và hậu quả chỉ lộ ra lúc tệ nhất.

    Đo thật ngày 28/09: một lần chạy nghiệm thu bộ đọc CV ngốn hết hạn mức, và
    bot tư vấn im lặng rơi về câu ghép sẵn. Không có dòng cảnh báo nào ở chỗ dễ
    thấy thì người vận hành sẽ đi tìm lỗi trong prompt.
    """

    def test_chua_khai_khoa_rieng_thi_bao_la_dung_chung(self):
        from unittest.mock import patch

        from app.advisor import client
        from app.core.config import settings

        with patch.object(settings, "advisor_api_key", ""):
            self.assertTrue(client.dung_chung_khoa())

    def test_khai_khoa_rieng_thi_khong_con_dung_chung(self):
        from unittest.mock import patch

        from app.advisor import client
        from app.core.config import settings

        with patch.object(settings, "advisor_api_key", "khoa-rieng"):
            self.assertFalse(client.dung_chung_khoa())

    def test_ghi_canh_bao_ngay_luc_khoi_dong(self):
        """Cảnh báo ở lần gọi mô hình đầu tiên là quá muộn: có thể chạy cả buổi
        mà không ai thấy dòng ấy."""
        from unittest.mock import patch

        from app.advisor import client
        from app.core.config import settings

        with patch.object(settings, "advisor_api_key", ""), \
             patch.object(settings, "advisor_enabled", True):
            with self.assertLogs("app.advisor.client", level="WARNING") as ghi:
                client.bao_cau_hinh()
        noi_dung = "\n".join(ghi.output)
        self.assertIn("CHUNG", noi_dung)
        # Phải nói luôn cách sửa, không chỉ báo là có vấn đề.
        self.assertIn("ADVISOR_API_KEY", noi_dung)

    def test_tat_engine_thi_bao_la_tat_chu_khong_canh_bao_khoa(self):
        from unittest.mock import patch

        from app.advisor import client
        from app.core.config import settings

        with patch.object(settings, "advisor_enabled", False):
            with self.assertLogs("app.advisor.client", level="INFO") as ghi:
                client.bao_cau_hinh()
        self.assertIn("TẮT", "\n".join(ghi.output))


if __name__ == "__main__":
    unittest.main()
