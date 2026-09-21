"""Kiểm thử việc gắn cờ cho câu mô hình tự từ chối.

Bốn câu dự phòng ghép sẵn thì luôn mang cờ `is_fallback`. Nhưng mô hình còn có
cách từ chối riêng của nó — *"website chưa cung cấp thông tin này"* — và những
câu đó trước đây được ghi nhận **như trả lời thành công**. Đo trên dữ liệu thật
tháng 9: 3 câu có cờ, trong khi có thêm 7 câu mô hình tự từ chối mà không ai đếm.

Hệ quả không nằm ở chatbot mà nằm ở **báo cáo**: tỷ lệ "trả lời được" cao hơn
thực tế, và người đọc báo cáo tin vào một con số đã bị thổi lên.

Bộ nhận diện cố ý hẹp. Lớp `KhongGanNhamTests` giữ cho nó hẹp: gắn nhầm cờ cho
một câu trả lời thật còn tệ hơn bỏ sót, vì nó bóp méo con số theo chiều ngược lại
mà không ai kiểm được.
"""
import unittest
from unittest.mock import AsyncMock, patch

from app.conversation.fallback_messages import (
    ALL_FALLBACKS,
    INVALID_ANSWER,
    NO_KNOWLEDGE,
    RATE_LIMITED,
    looks_like_refusal,
)


class NhanDienTuChoiTests(unittest.TestCase):
    def test_bon_cau_du_phong_deu_duoc_nhan_ra(self):
        for câu in ALL_FALLBACKS:
            with self.subTest(câu=câu[:40]):
                self.assertTrue(looks_like_refusal(câu))

    def test_mo_hinh_tu_tu_choi_theo_nhieu_cach(self):
        cases = [
            "Hiện tại, website chưa cung cấp thông tin chi tiết về quy trình đóng phí.",
            "Chào bạn, tôi chưa có thông tin về thủ tục bảo lãnh vợ con sang Nhật.",
            "Về việc hoàn tiền, tôi chưa tìm thấy thông tin cụ thể trên website.",
            "Thông tin từ website chưa đề cập đến nội dung này.",
            "Câu hỏi này không thuộc chuyên môn của tôi về xuất khẩu lao động.",
            "Chào bạn, tôi không thể đoán được bạn có đỗ phỏng vấn hay không.",
            "Tôi không thể cam kết bạn sẽ trúng tuyển.",
        ]
        for câu in cases:
            with self.subTest(câu=câu[:45]):
                self.assertTrue(looks_like_refusal(câu), câu)

    def test_chuoi_rong_khong_phai_tu_choi(self):
        self.assertFalse(looks_like_refusal(""))


class KhongGanNhamTests(unittest.TestCase):
    """Câu trả lời thật không được nhận nhầm thành từ chối."""

    def test_cau_tra_loi_co_so_lieu(self):
        cases = [
            "Chào bạn, khi bắt đầu đăng ký bạn đóng tiền đặt cọc 10 triệu đồng.",
            "Tổng chi phí trọn gói cho cả chương trình là 90 triệu đồng.",
            "Nếu phỏng vấn trượt, công ty sẽ hoàn lại 10 triệu tiền đặt cọc.",
            "Chương trình nhận cả các bạn thấp, bé, gầy, béo, mắt cận đeo kính.",
            "Ký túc xá miễn phí cho học viên, có ba cơ sở ở Hà Nội, Thủ Đức và Bến Tre.",
        ]
        for câu in cases:
            with self.subTest(câu=câu[:45]):
                self.assertFalse(looks_like_refusal(câu), câu)

    def test_cau_neu_dieu_kien_khong_phai_tu_choi(self):
        """Nêu lại một điều kiện có trong tài liệu là trả lời, không phải từ chối."""
        self.assertFalse(
            looks_like_refusal(
                "Điều kiện gồm: không nhiễm các bệnh truyền nhiễm như viêm gan B, "
                "HIV, bệnh lao."
            )
        )


class LuongChatGanCoTests(unittest.IsolatedAsyncioTestCase):
    """Cờ phải đi tới tận bản ghi lưu xuống database."""

    def _hit(self):
        class Hit:
            score = 0.8
            payload = {"title": "Bài nào đó", "url": "https://vi.du/bai", "text": "nội dung"}

        return Hit()

    async def _chay(self, answer: str) -> dict:
        from app.services import chat_service

        with (
            patch.object(chat_service, "search", return_value=[self._hit()]),
            patch.object(chat_service, "generate_response", return_value=answer),
            patch.object(chat_service, "get_messages", AsyncMock(return_value=[])),
            patch.object(chat_service, "get_booking_draft", AsyncMock(return_value=None)),
            patch.object(chat_service, "save_message", AsyncMock()) as save,
        ):
            result = await chat_service.process_message(
                "Cho em hỏi về chi phí", session_id="phien-kiem-thu-0001"
            )
            return {"result": result, "save": save}

    async def test_mo_hinh_tu_choi_thi_co_co_va_khong_kem_nguon(self):
        ran = await self._chay(
            "Hiện tại, website chưa cung cấp thông tin chi tiết về nội dung này. "
            "Bạn vui lòng liên hệ hotline nhé."
        )
        self.assertTrue(ran["result"]["is_fallback"])
        self.assertEqual(
            ran["result"]["sources"],
            [],
            "nói chưa có thông tin mà vẫn hiện link nguồn là tự mâu thuẫn",
        )
        # Bản ghi của trợ lý lưu xuống database cũng phải mang cờ.
        assistant = [c for c in ran["save"].await_args_list if c.args[1] == "assistant"]
        self.assertTrue(assistant[0].kwargs["is_fallback"])

    async def test_cau_tra_loi_that_van_khong_co_co_va_co_nguon(self):
        ran = await self._chay(
            "Chào bạn, tổng chi phí trọn gói cho cả chương trình là 90 triệu đồng."
        )
        self.assertFalse(ran["result"]["is_fallback"])
        self.assertEqual(len(ran["result"]["sources"]), 1)

    async def test_cau_bi_bo_kiem_chan_van_giu_co_nhu_cu(self):
        """Câu quá ngắn bị validator chặn — nhánh cũ, không được hỏng theo."""
        ran = await self._chay("Vâng.")
        self.assertTrue(ran["result"]["is_fallback"])
        self.assertEqual(ran["result"]["answer"], INVALID_ANSWER)

    async def test_khong_tim_thay_doan_nao_van_giu_co_nhu_cu(self):
        from app.services import chat_service

        with (
            patch.object(chat_service, "search", return_value=[]),
            patch.object(chat_service, "get_messages", AsyncMock(return_value=[])),
            patch.object(chat_service, "get_booking_draft", AsyncMock(return_value=None)),
            patch.object(chat_service, "save_message", AsyncMock()),
        ):
            result = await chat_service.process_message(
                "Cho em hỏi về chi phí", session_id="phien-kiem-thu-0002"
            )
        self.assertTrue(result["is_fallback"])
        self.assertEqual(result["answer"], NO_KNOWLEDGE)


class DungChungMotBoNhanDienTests(unittest.TestCase):
    """Bộ nghiệm thu phải dùng đúng bộ nhận diện của hệ thống, không giữ bản sao."""

    def test_bo_nghiem_thu_khong_tu_dinh_nghia_lai(self):
        import inspect
        import pathlib

        source = (
            pathlib.Path(__file__).resolve().parents[1]
            / "scripts"
            / "nghiem_thu_chatbot.py"
        ).read_text(encoding="utf-8")
        self.assertIn("looks_like_refusal", source)
        self.assertNotIn(
            "TU_CHOI = re.compile",
            source,
            "hai bản sao sẽ lệch nhau, và bộ nghiệm thu sẽ báo đạt cho đúng thứ "
            "mà hệ thống đang đếm sai",
        )
        del inspect

    def test_cau_qua_tai_khong_bi_coi_la_tu_choi_trong_bo_nghiem_thu(self):
        """`RATE_LIMITED` vẫn nằm trong ALL_FALLBACKS, nên bộ nghiệm thu phải
        chặn nó trước bằng nhánh riêng — kiểm ở đây để nhánh đó không bị bỏ."""
        import pathlib

        source = (
            pathlib.Path(__file__).resolve().parents[1]
            / "scripts"
            / "nghiem_thu_chatbot.py"
        ).read_text(encoding="utf-8")
        self.assertIn("if answer == RATE_LIMITED:", source)
        self.assertTrue(looks_like_refusal(RATE_LIMITED))


if __name__ == "__main__":
    unittest.main()
