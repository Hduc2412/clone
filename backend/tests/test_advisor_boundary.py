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


class ModelDuPhongTests(unittest.IsolatedAsyncioTestCase):
    """Dự phòng chỉ được dùng khi CHƯA nhận được câu trả lời trọn vẹn.

    Hạn mức gói miễn phí là 20 lượt mỗi ngày cho mỗi (dự án, model). Một buổi bảo
    vệ mà hội đồng hỏi vài chục câu là cạn, và lúc ấy toàn bộ phần tư vấn lặng lẽ
    rơi về bản ghép sẵn. Một model thứ hai trên cùng khóa là thêm 20 lượt nữa mà
    không phải mượn hạn mức của khung chat.

    Nhưng cái đáng canh không phải việc có dự phòng, mà là **giới hạn của nó**.
    """

    async def _goi(self, *ket_qua, du_phong="model-du-phong", chinh="model-chinh"):
        from unittest.mock import AsyncMock, patch

        from app.advisor import client
        from app.core.config import settings

        goi = AsyncMock(side_effect=list(ket_qua))
        with patch.object(settings, "advisor_enabled", True), \
             patch.object(settings, "advisor_api_key", "khoa"), \
             patch.object(settings, "advisor_model", chinh), \
             patch.object(settings, "advisor_model_du_phong", du_phong), \
             patch.object(client, "_goi_mot_lan", goi):
            ket = await client.sinh_van_ban("prompt")
        return ket, goi

    async def test_het_han_muc_thi_chuyyen_sang_du_phong(self):
        from app.advisor import client

        (van_ban, ly_do, model), goi = await self._goi(
            (None, client.LY_DO_KHONG_GOI_DUOC),
            ("câu của dự phòng", client.LY_DO_OK),
        )
        self.assertEqual(van_ban, "câu của dự phòng")
        self.assertEqual(model, "model-du-phong")
        self.assertEqual(goi.await_count, 2)

    async def test_cau_bi_cat_giua_chung_cung_duoc_chuyen(self):
        """Câu đứt giữa chữ nghĩa là chưa hề có câu trả lời để mà xét."""
        from app.advisor import client

        (van_ban, _, model), goi = await self._goi(
            (None, client.LY_DO_BI_CAT),
            ("câu của dự phòng", client.LY_DO_OK),
        )
        self.assertEqual(van_ban, "câu của dự phòng")
        self.assertEqual(model, "model-du-phong")

    async def test_model_chinh_tra_loi_duoc_thi_KHONG_goi_du_phong(self):
        """Dự phòng là phương án cuối, không phải lượt gọi thứ hai cho mọi câu.

        Gọi cả hai mỗi lần là tiêu hai hạn mức cho một câu hỏi — đúng thứ mà việc
        có dự phòng lẽ ra phải tránh.
        """
        from app.advisor import client

        (van_ban, _, model), goi = await self._goi(
            ("câu của model chính", client.LY_DO_OK),
        )
        self.assertEqual(van_ban, "câu của model chính")
        self.assertEqual(model, "model-chinh")
        self.assertEqual(goi.await_count, 1)

    async def test_engine_tat_thi_khong_goi_ca_hai(self):
        from unittest.mock import AsyncMock, patch

        from app.advisor import client
        from app.core.config import settings

        goi = AsyncMock()
        with patch.object(settings, "advisor_enabled", False), \
             patch.object(settings, "advisor_model_du_phong", "model-du-phong"), \
             patch.object(client, "_goi_mot_lan", goi):
            van_ban, ly_do, model = await client.sinh_van_ban("prompt")
        self.assertIsNone(van_ban)
        self.assertEqual(ly_do, client.LY_DO_TAT)
        goi.assert_not_awaited()

    async def test_chua_khai_du_phong_thi_khong_goi_lan_hai(self):
        from app.advisor import client

        (van_ban, ly_do, _), goi = await self._goi(
            (None, client.LY_DO_KHONG_GOI_DUOC), du_phong=""
        )
        self.assertIsNone(van_ban)
        self.assertEqual(goi.await_count, 1)

    async def test_du_phong_trung_model_chinh_thi_khong_goi_lai(self):
        """Khai trùng thì lượt thứ hai chỉ tiêu thêm hạn mức của cùng một model."""
        from app.advisor import client

        (_, _, _), goi = await self._goi(
            (None, client.LY_DO_KHONG_GOI_DUOC),
            du_phong="model-chinh",
        )
        self.assertEqual(goi.await_count, 1)

    def test_chot_hau_kiem_KHONG_BAO_GIO_lam_doi_model(self):
        """Ca quan trọng nhất của lớp này — cưỡng chế bằng thứ tự các tầng.

        Nếu chốt hậu kiểm loại câu của model A rồi hệ thống đi hỏi model B, nó
        không đáng tin hơn: nó đang **lọc theo mẫu cho tới khi có câu lọt qua
        chốt**. Việc ấy chọn lọc đúng những lời bịa mà chốt tình cờ không bắt
        được, và tỉ lệ "bot không đoán" sẽ đẹp lên trong khi chất lượng thật đi
        xuống. Một câu bị loại là một kết quả ĐÚNG, không phải một lần thử hỏng.

        Canh bằng cách đọc mã: `qa.tra_loi` chỉ được gọi `sinh_van_ban` **một
        lần**, và lý do loại của `kiem_tra` không được dẫn tới lượt gọi nào nữa.
        """
        import ast as _ast

        nguon = (
            pathlib.Path(__file__).resolve().parent.parent
            / "app" / "advisor" / "qa.py"
        ).read_text(encoding="utf-8")
        cay = _ast.parse(nguon)
        ham = next(
            n for n in _ast.walk(cay)
            if isinstance(n, _ast.AsyncFunctionDef) and n.name == "tra_loi"
        )
        so_lan_goi = sum(
            1 for n in _ast.walk(ham)
            if isinstance(n, _ast.Call)
            and isinstance(n.func, _ast.Attribute)
            and n.func.attr == "sinh_van_ban"
        )
        self.assertEqual(
            so_lan_goi,
            1,
            "`tra_loi` gọi mô hình nhiều hơn một lần. Nếu lượt thêm là để thử lại "
            "sau khi chốt hậu kiểm loại câu, đó là lọc theo mẫu cho tới khi lọt — "
            "phải bỏ. Dự phòng thuộc `client.sinh_van_ban`, nằm DƯỚI chốt.",
        )
        # Vòng lặp trong `tra_loi` cũng là dấu hiệu của việc thử lại.
        self.assertFalse(
            any(isinstance(n, (_ast.While, _ast.For)) for n in _ast.walk(ham)),
            "`tra_loi` có vòng lặp — kiểm xem có phải đang thử lại mô hình không.",
        )
