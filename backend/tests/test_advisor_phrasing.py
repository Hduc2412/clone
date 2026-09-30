"""Chốt chặn của engine tư vấn (`app/advisor`) — phần quyết định câu "làm sao biết nó không bịa".

Bộ này không kiểm mô hình viết hay hay dở. Nó kiểm **chốt chặn bằng mã nguồn**
đứng sau mô hình: câu nào có số lạ hoặc có lời hứa thì bị loại, và hệ thống quay
về bản ghép sẵn. Dặn mô hình "đừng bịa số" trong câu lệnh là một lời dặn; ca kiểm
thử ở đây mới là bảo đảm.
"""
import unittest
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.advisor import client as advisor_client
from app.advisor import phrasing as explain_llm


BLOCK = """ĐƠN ĐANG XÉT: DH-0001 — Điều dưỡng viện dưỡng lão Tokyo
KẾT LUẬN: chưa đạt điều kiện bắt buộc

CHƯA ĐẠT:
- Tiếng Nhật: yêu cầu N4 — ứng viên Chưa học

LỘ TRÌNH HỌC ĐỂ ĐỦ ĐIỀU KIỆN:
- Từ Chưa học lên N4: 6–7 tháng
- Học phí: 35.000.000đ
- Đây là một chặng trong tổng chi phí chương trình 90.000.000đ"""


class ChotSoTests(unittest.TestCase):
    def test_cau_dung_so_trong_khoi_thi_qua(self):
        cau = (
            "Đơn DH-0001 yêu cầu tiếng Nhật N4, hiện bạn chưa học nên chưa đạt "
            "điều kiện này. Bạn cần khoảng 6–7 tháng học tại trung tâm, học phí "
            "35.000.000đ, là một chặng trong tổng 90.000.000đ."
        )
        self.assertIsNone(explain_llm.kiem_tra(cau, BLOCK))

    def test_so_la_thi_bi_loai(self):
        """Mô hình tự thêm '12 tháng' cho câu nghe chắc chắn hơn."""
        cau = "Bạn cần học khoảng 12 tháng để đủ N4."
        ly_do = explain_llm.kiem_tra(cau, BLOCK)
        self.assertIsNotNone(ly_do)
        self.assertIn("12", ly_do)

    def test_hoc_phi_bi_thoi_phong_thi_bi_loai(self):
        cau = "Học phí khoảng 45.000.000đ cho khóa 6 tháng."
        self.assertIsNotNone(explain_llm.kiem_tra(cau, BLOCK))

    def test_so_viet_khac_cach_van_duoc_chap_nhan(self):
        """`35000000` và `35.000.000` là cùng một số.

        Không chuẩn hóa thì chốt chặn loại oan câu đúng chỉ vì mô hình viết số
        theo cách khác — và bản ghép sẵn sẽ xuất hiện gần như mọi lần.
        """
        cau = "Học phí 35000000 đồng, thời gian 6 tháng."
        self.assertIsNone(explain_llm.kiem_tra(cau, BLOCK))

    def test_khong_co_so_nao_thi_qua(self):
        cau = "Bạn chưa đạt yêu cầu tiếng Nhật của đơn này, cần học thêm."
        self.assertIsNone(explain_llm.kiem_tra(cau, BLOCK))


class ChotKetLuanTests(unittest.TestCase):
    def test_cum_hua_hen_thi_bi_loai(self):
        for cum in ("chắc chắn đi được", "đảm bảo trúng tuyển", "hoàn toàn phù hợp"):
            with self.subTest(cum=cum):
                ly_do = explain_llm.kiem_tra(f"Hồ sơ của bạn {cum}.", BLOCK)
                self.assertIsNotNone(ly_do)
                self.assertIn("hứa hẹn", ly_do)

    def test_khong_phan_biet_chu_hoa(self):
        self.assertIsNotNone(explain_llm.kiem_tra("Bạn CHẮC CHẮN ĐI ĐƯỢC.", BLOCK))

    def test_cau_rong_thi_bi_loai(self):
        self.assertIsNotNone(explain_llm.kiem_tra("   ", BLOCK))

    def test_cau_qua_dai_thi_bi_loai(self):
        self.assertIsNotNone(explain_llm.kiem_tra("Đạt. " * 400, BLOCK))


class TatDuocTests(unittest.IsolatedAsyncioTestCase):
    async def test_tat_co_thi_tra_none_va_khong_goi_mang(self):
        """Tắt cờ thì hệ thống chạy đủ bằng bản ghép sẵn, điểm số không đổi."""
        with patch.object(settings, "advisor_enabled", False):
            with patch.object(advisor_client.httpx, "AsyncClient") as client:
                self.assertIsNone(await explain_llm.rephrase(BLOCK))
                client.assert_not_called()

    async def test_thieu_khoa_api_thi_tra_none(self):
        """Không khai khóa nào thì không gọi mạng, và **phải chứng minh là không gọi**.

        Bản trước chỉ xóa `advisor_api_key`. Nhưng `client.api_key()` có đường rơi
        về `gemini_api_key`, và trên máy có `.env` thật thì khóa ấy tồn tại — nên ca
        này **gửi một request thật** rồi đi tới `None` vì Google từ chối. Nó xanh,
        nhưng xanh vì một lý do khác hẳn thứ nó nói mình đang kiểm, và bộ kiểm thử
        không còn chạy được khi mất mạng. Bản rà soát 30/09 bắt đúng chỗ này qua
        nhật ký lần chạy.

        Xóa **cả hai** khóa, và chốt bằng `assert_not_called` — thiếu nó thì lần sau
        ai thêm một đường rơi thứ ba là ca lại xanh vì lý do sai.
        """
        with patch.object(settings, "advisor_enabled", True), \
             patch.object(settings, "advisor_api_key", ""), \
             patch.object(settings, "gemini_api_key", ""):
            with patch.object(advisor_client.httpx, "AsyncClient") as client:
                self.assertIsNone(await explain_llm.rephrase(BLOCK))
                client.assert_not_called()

    async def test_chi_xoa_khoa_rieng_thi_van_dung_khoa_chung(self):
        """Đường rơi về khóa chung là có chủ ý, nên phải có ca nói rõ nó tồn tại.

        Không có ca này thì người đọc ca trên dễ tưởng chỉ cần bỏ `ADVISOR_API_KEY`
        là engine tư vấn ngừng gọi mạng — trong khi thật ra nó chuyển sang dùng
        chung hạn mức với khung chat, đúng thứ cả thiết kế cố tránh.
        """
        advisor_client._da_canh_bao_dung_chung = False
        with patch.object(settings, "advisor_enabled", True), \
             patch.object(settings, "advisor_api_key", ""), \
             patch.object(settings, "gemini_api_key", "khoa-chung"):
            self.assertTrue(advisor_client.san_sang())
            self.assertEqual(advisor_client.api_key(), "khoa-chung")

    async def test_khoi_rong_thi_khong_goi_mang(self):
        with patch.object(settings, "advisor_enabled", True), \
             patch.object(settings, "advisor_api_key", "khoa-thu"):
            with patch.object(advisor_client.httpx, "AsyncClient") as client:
                self.assertIsNone(await explain_llm.rephrase("   "))
                client.assert_not_called()


class SuCoKhongLamGayManHinhTests(unittest.IsolatedAsyncioTestCase):
    """Phần này là trang trí. Một sự cố mạng không được làm gãy cả màn hình."""

    def _gia_lap(self, *, tra_ve=None, loi=None):
        client = AsyncMock()
        if loi is not None:
            client.post = AsyncMock(side_effect=loi)
        else:
            phan_hoi = AsyncMock()
            phan_hoi.json = lambda: tra_ve
            client.post = AsyncMock(return_value=phan_hoi)
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=False)
        return ctx

    async def _chay(self, ctx):
        with patch.object(settings, "advisor_enabled", True), \
             patch.object(settings, "advisor_api_key", "khoa-thu"), \
             patch.object(advisor_client.httpx, "AsyncClient", return_value=ctx):
            return await explain_llm.rephrase(BLOCK)

    async def test_mat_mang_thi_tra_none(self):
        self.assertIsNone(await self._chay(self._gia_lap(loi=advisor_client.httpx.ConnectError("hỏng"))))

    async def test_dich_vu_bao_loi_thi_tra_none(self):
        ra = await self._chay(self._gia_lap(tra_ve={"error": {"message": "quota"}}))
        self.assertIsNone(ra)

    async def test_tra_ve_dang_la_thi_tra_none(self):
        ra = await self._chay(self._gia_lap(tra_ve={"candidates": []}))
        self.assertIsNone(ra)

    async def test_cau_hop_le_thi_duoc_dung(self):
        cau = "Đơn này yêu cầu N4, bạn chưa học nên chưa đạt. Cần 6–7 tháng học."
        ra = await self._chay(self._gia_lap(
            tra_ve={"candidates": [{"content": {"parts": [{"text": cau}]}}]}
        ))
        self.assertEqual(ra, cau)

    async def test_cau_co_so_la_thi_quay_ve_ban_ghep_san(self):
        ra = await self._chay(self._gia_lap(
            tra_ve={"candidates": [{"content": {"parts": [
                {"text": "Bạn cần học 24 tháng, học phí 200.000.000đ."}
            ]}}]}
        ))
        self.assertIsNone(ra)


if __name__ == "__main__":
    unittest.main()


class ChotNghiaTests(unittest.TestCase):
    """Lỗi nghĩa mà chốt số không bắt được.

    Đo trên máy thật: mô hình đọc "ứng viên Chưa học" rồi viết "chưa đạt điều
    kiện do **chưa có thông tin** về trình độ tiếng Nhật". Mọi con số đều đúng,
    nên chốt số cho qua — nhưng câu đó nói sai đúng cái phân biệt cả hệ thống
    dựa vào.

    Với ứng viên, hai câu dẫn tới hai hành động khác nhau: "chưa học" thì đi học,
    "chưa có thông tin" thì quay lại khai thêm rồi ngồi đợi.
    """

    def test_noi_thieu_thong_tin_khi_khoi_khong_co_chua_ro(self):
        cau = "Bạn chưa đạt vì chưa có thông tin về trình độ tiếng Nhật."
        ly_do = explain_llm.kiem_tra(cau, BLOCK)
        self.assertIsNotNone(ly_do)
        self.assertIn("thiếu thông tin", ly_do)

    def test_noi_dung_chua_hoc_thi_qua(self):
        cau = "Đơn yêu cầu N4 nhưng bạn chưa học, nên chưa đạt điều kiện này."
        self.assertIsNone(explain_llm.kiem_tra(cau, BLOCK))

    def test_khoi_co_chua_ro_thi_duoc_noi_thieu_thong_tin(self):
        khoi = BLOCK + "\n\nCHƯA RÕ (hồ sơ chưa khai):\n- Bằng cấp: chưa rõ"
        cau = "Hồ sơ còn chưa rõ mục bằng cấp nên chưa kết luận được."
        self.assertIsNone(explain_llm.kiem_tra(cau, khoi))


class KhongDungCauBiCatTests(unittest.IsolatedAsyncioTestCase):
    """Câu cắt giữa chữ vẫn là chuỗi hợp lệ, nên phải bắt riêng.

    Nguyên nhân thật gặp trên máy: `gemini-2.5-flash` suy luận nội bộ, và token
    suy luận tính vào `maxOutputTokens`. Với hạn mức nhỏ, mô hình tiêu gần hết
    vào suy luận rồi câu trả lời đứt ở giữa mã đơn — chốt số bắt được nhưng báo
    một lý do vô nghĩa ("số lạ: ['0']").
    """

    async def test_finish_reason_khac_stop_thi_bi_loai(self):
        client = AsyncMock()
        phan_hoi = AsyncMock()
        phan_hoi.json = lambda: {
            "candidates": [{
                "finishReason": "MAX_TOKENS",
                "content": {"parts": [{"text": "Chào bạn, về đơn DH-0"}]},
            }]
        }
        client.post = AsyncMock(return_value=phan_hoi)
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=False)

        with patch.object(settings, "advisor_enabled", True), \
             patch.object(settings, "advisor_api_key", "khoa-thu"), \
             patch.object(advisor_client.httpx, "AsyncClient", return_value=ctx):
            self.assertIsNone(await explain_llm.rephrase(BLOCK))

    async def test_tat_suy_luan_noi_bo_trong_payload(self):
        """Không tắt thì câu trả lời bị cắt — đã gặp thật, không phải giả thiết."""
        client = AsyncMock()
        phan_hoi = AsyncMock()
        phan_hoi.json = lambda: {"candidates": [{"finishReason": "STOP",
                                                 "content": {"parts": [{"text": "Bạn chưa học N4."}]}}]}
        client.post = AsyncMock(return_value=phan_hoi)
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=False)

        with patch.object(settings, "advisor_enabled", True), \
             patch.object(settings, "advisor_api_key", "khoa-thu"), \
             patch.object(advisor_client.httpx, "AsyncClient", return_value=ctx):
            await explain_llm.rephrase(BLOCK)

        cau_hinh = client.post.await_args.kwargs["json"]["generationConfig"]
        self.assertEqual(cau_hinh["thinkingConfig"]["thinkingBudget"], 0)


class KhongHua_ThayCongTyTests(unittest.TestCase):
    """Một loại vượt rào khác hẳn: không hứa **kết quả** mà hứa **hành động**.

    Đo trên máy thật, ca ứng viên đã có N4: mô hình tự thêm câu cuối "Chúng tôi
    sẽ nộp hồ sơ của bạn vào đơn hàng sau khi có kết quả khám sức khỏe." Câu đó
    không có con số nào nên chốt số cho qua.

    Tại sao nó tệ: ứng viên còn chưa bấm đăng ký. Đọc câu ấy họ tưởng việc đã
    xong rồi ngồi đợi, trong khi hệ thống chưa tạo hồ sơ nào và không ai gọi họ.
    """

    def test_cam_ket_nop_ho_so_thi_bi_loai(self):
        cau = ("Bạn đã đạt các điều kiện bắt buộc. Chúng tôi sẽ nộp hồ sơ của bạn "
               "vào đơn hàng sau khi có kết quả khám sức khỏe.")
        ly_do = explain_llm.kiem_tra(cau, BLOCK)
        self.assertIsNotNone(ly_do)
        self.assertIn("cam kết thay công ty", ly_do)

    def test_cac_cach_noi_khac_cung_bi_bat(self):
        for cau in (
            "Công ty sẽ nộp đơn giúp bạn.",
            "Bạn sẽ được nhận vào đơn này.",
            "Chúng tôi sẽ sắp xếp lịch phỏng vấn cho bạn.",
        ):
            with self.subTest(cau=cau):
                self.assertIsNotNone(explain_llm.kiem_tra(cau, BLOCK))

    def test_noi_nhan_vien_se_lien_he_thi_van_duoc(self):
        """Câu này đúng và hữu ích — nhân viên gọi lại là bước thật có trong luồng."""
        cau = "Bạn đã đạt điều kiện. Nhân viên tư vấn sẽ liên hệ để trao đổi thêm."
        self.assertIsNone(explain_llm.kiem_tra(cau, BLOCK))


class KhongNoiKetLuanRaCaChuongTrinhTests(unittest.TestCase):
    """Lỗi tìm ra bằng E2E trên trình duyệt thật, ngày 30/09.

    Đi đúng luồng khách: gửi CV của một người 38 tuổi vào đơn DH-0001 (20–35 tuổi).
    Khối máy ghép nói đúng:

        "Đơn này chưa phù hợp vì độ tuổi: đơn tuổi 20–35, 38 tuổi."

    Mô hình viết lại thành:

        "bạn hiện chưa đạt điều kiện bắt buộc CỦA CHƯƠNG TRÌNH"

    Chữ "chương trình" **không có trong khối nguồn**. Mô hình tự nới phạm vi của kết
    luận từ một đơn ra cả chương trình — hướng nới nguy hiểm nhất: chương trình nhận
    18–40 tuổi, ngay trên website còn hai đơn nhận tới 38 và 40 (DH-0004, DH-0008),
    nên người 38 tuổi đọc câu ấy sẽ bỏ đi trong khi họ vẫn đi được.

    Sáu chốt cũ không bắt: không số nào bịa (20, 35, 38 đều có trong khối), không
    hứa hẹn, không cam kết, câu kết thúc đủ. Chúng kiểm **con số và lời hứa**, không
    kiểm **phạm vi của lời khẳng định**.

    Và không bộ kiểm thử nào bắt được, vì tất cả đều mock mô hình. Chỉ chạy thật
    trên trình duyệt mới lộ ra.
    """

    KHOI = "Đơn DH-0001 chưa phù hợp vì độ tuổi: đơn tuổi 20–35, 38 tuổi."

    def test_cau_that_do_mo_hinh_viet_bi_loai(self):
        cau = (
            "Theo kết quả đối chiếu hồ sơ của bạn với đơn tuyển DH-0001, bạn hiện "
            "chưa đạt điều kiện bắt buộc của chương trình. Cụ thể, yêu cầu về độ "
            "tuổi của đơn hàng là từ 20 đến 35 tuổi, trong khi bạn 38 tuổi."
        )
        ly_do = explain_llm.kiem_tra(cau, self.KHOI)
        self.assertIsNotNone(ly_do, "câu nới phạm vi vẫn lọt qua chốt")
        self.assertIn("chương trình", ly_do)

    def test_noi_dung_pham_vi_mot_don_thi_qua(self):
        cau = (
            "Đơn DH-0001 yêu cầu ứng viên từ 20 đến 35 tuổi, trong khi bạn 38 tuổi "
            "nên hồ sơ chưa đạt điều kiện của đơn này."
        )
        self.assertIsNone(explain_llm.kiem_tra(cau, self.KHOI))

    def test_noi_ve_muc_nen_cua_chuong_trinh_van_qua(self):
        """Nêu mức nền của chương trình là việc ĐÚNG và cần làm.

        Chốt này chỉ chặn việc **phán ứng viên trượt cả chương trình**, không chặn
        việc nói chương trình nhận những ai — đó chính là thông tin cứu người 38
        tuổi khỏi bỏ cuộc.
        """
        # Khối phải có sẵn mức nền, không thì chốt SỐ loại 18/40 — và loại vì một
        # lý do khác hẳn thứ ca này đang kiểm.
        khoi = self.KHOI + "\nĐIỀU KIỆN MỨC NỀN: Độ tuổi 18 đến 40 tuổi."
        cau = (
            "Chương trình nhận ứng viên từ 18 đến 40 tuổi. Riêng đơn DH-0001 yêu "
            "cầu từ 20 đến 35 tuổi nên hồ sơ của bạn chưa hợp đơn này."
        )
        self.assertIsNone(explain_llm.kiem_tra(cau, khoi))

    def test_neu_luat_chung_khong_gan_voi_nguoi_hoi_thi_qua(self):
        """"Trường hợp nhiễm viêm gan B thì không đủ điều kiện" là nêu luật công ty.

        Khác hẳn "BẠN không đủ điều kiện của chương trình" — cái sau mới là phán
        vượt quá thứ khối dữ liệu nói.
        """
        cau = (
            "Trường hợp nhiễm bệnh truyền nhiễm sẽ không đủ điều kiện tham gia "
            "chương trình. Kết luận là của buổi khám tại bệnh viện được chỉ định."
        )
        self.assertIsNone(explain_llm.kiem_tra(cau, self.KHOI))

    def test_bot_hoi_dap_dung_chung_dung_mot_chot(self):
        """Hai chỗ lệch nhau nghĩa là một trong hai đang để lọt."""
        from app.advisor import qa

        cau = "Hồ sơ của bạn chưa đủ điều kiện của chương trình."
        self.assertIsNotNone(qa.kiem_tra(cau, self.KHOI))
