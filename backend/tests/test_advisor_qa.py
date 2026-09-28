"""Bot tư vấn — hỏi đáp về hồ sơ của khách và đơn họ đang xem.

Bộ này không kiểm bot trả lời hay hay dở. Nó kiểm **chỗ bot phải chịu nói không
biết**, và chỗ nó không được nói quá những gì được đọc.

Bot này khác khung chat ở một điểm quyết định: nó **không có kho tài liệu nào**.
Mọi thứ nó biết nằm trong bốn khối chữ do quy tắc dựng. Câu hỏi ngoài bốn khối ấy
mà nó vẫn trả lời thì câu đó là bịa — và sẽ được đọc như lời của công ty.
"""
import unittest
from unittest.mock import AsyncMock, patch

from app.advisor import qa


HO_SO = """[Đang biết về khách này]
Đã xác nhận:
- Họ tên: Trần Thị Thu Hà
- Trình độ tiếng Nhật: Chưa học
- Bằng cấp: Cao đẳng"""

DON = """[Đơn khách đang xét]
Mã đơn: DH-0001
Điều kiện bắt buộc — thiếu một mục là không nộp được đơn này:
- Tiếng Nhật: N4
- Độ tuổi: 20 đến 35 tuổi"""

DOI_CHIEU = """ĐƠN ĐANG XÉT: DH-0001 — Điều dưỡng viện dưỡng lão Tokyo
KẾT LUẬN: chưa đạt điều kiện bắt buộc

CHƯA ĐẠT:
- Tiếng Nhật: yêu cầu N4 — ứng viên Chưa học

LỘ TRÌNH HỌC ĐỂ ĐỦ ĐIỀU KIỆN:
- Từ Chưa học lên N4: 6–7 tháng
- Học phí: 35.000.000đ
- Đây là một chặng trong tổng chi phí chương trình 90.000.000đ"""

DIEU_KIEN = """ĐIỀU KIỆN MỨC NỀN CỦA CHƯƠNG TRÌNH:
- Độ tuổi: 18 đến 40 tuổi, cả nam và nữ
- Bằng cấp: Không yêu cầu bằng cấp"""

KHOI = "\n".join((HO_SO, DON, DOI_CHIEU, DIEU_KIEN))


class HauKiemTests(unittest.TestCase):
    def test_cau_dung_du_lieu_duoc_doc_thi_qua(self):
        cau = (
            "Đơn DH-0001 yêu cầu tiếng Nhật N4, hiện bạn chưa học nên chưa đạt. "
            "Bạn cần khoảng 6–7 tháng, học phí 35.000.000đ trong tổng 90.000.000đ."
        )
        self.assertIsNone(qa.kiem_tra(cau, KHOI))

    def test_so_khong_co_trong_du_lieu_thi_bi_loai(self):
        ly_do = qa.kiem_tra("Bạn cần học khoảng 12 tháng.", KHOI)
        self.assertIsNotNone(ly_do)
        self.assertIn("12", ly_do)

    def test_hua_hen_thi_bi_loai(self):
        self.assertIsNotNone(qa.kiem_tra("Học xong bạn chắc chắn đi được.", KHOI))

    def test_cam_ket_thay_cong_ty_thi_bi_loai(self):
        self.assertIsNotNone(
            qa.kiem_tra("Chúng tôi sẽ nộp hồ sơ của bạn ngay.", KHOI)
        )

    def test_duoc_phep_noi_chua_co_thong_tin(self):
        """Khác phần diễn đạt: ở đây nói "chưa có thông tin" là hành vi mong muốn.

        Phần diễn đạt cấm câu đó vì nó đang viết lại một kết quả đã có đủ. Bot
        thì phải được quyền từ chối, nếu không nó sẽ bịa cho có câu trả lời.
        """
        self.assertIsNone(
            qa.kiem_tra("Câu này mình chưa có thông tin trong hồ sơ và đơn.", KHOI)
        )


class KhongBietThiNoiKhongBietTests(unittest.IsolatedAsyncioTestCase):
    async def _hoi(self, *, mo_hinh_tra, ly_do=None):
        if ly_do is None:
            ly_do = qa.client.LY_DO_OK if mo_hinh_tra else qa.client.LY_DO_KHONG_GOI_DUOC
        goi = AsyncMock(return_value=(mo_hinh_tra, ly_do))
        with patch.object(qa.client, "sinh_van_ban", goi):
            return await qa.tra_loi(
                cau_hoi="Ký túc xá có điều hòa không ạ?",
                ho_so=HO_SO, don=DON, doi_chieu=DOI_CHIEU, dieu_kien_nen=DIEU_KIEN,
            )

    async def test_mo_hinh_khong_goi_duoc_thi_van_co_cau_tra_loi(self):
        """Im lặng ở giữa một cuộc trò chuyện là để ứng viên đứng lại không biết làm gì."""
        cau, nguon = await self._hoi(mo_hinh_tra=None)
        self.assertEqual(nguon, qa.NGUON_KHONG_GOI_DUOC)
        self.assertIn("nhân viên tư vấn", cau)

    async def test_khong_goi_duoc_khong_bi_ghi_thanh_bot_khong_doan(self):
        """Đây là ca giữ cho số liệu bảo vệ khỏi tự đẹp lên khi hệ thống hỏng.

        Hết hạn mức thì bot chưa hề được hỏi. Ghi lượt ấy là `khong_biet` nghĩa
        là đếm nó vào tỉ lệ "bot chịu không đoán" — tỉ lệ càng đẹp khi dịch vụ
        càng chết. Đo thật ngày 28/09, mười câu dính đúng lỗi này.
        """
        _, nguon = await self._hoi(mo_hinh_tra=None)
        self.assertNotEqual(nguon, qa.NGUON_KHONG_BIET)

    async def test_khong_goi_duoc_noi_that_la_dang_ban_chu_khong_noi_thieu_du_lieu(self):
        """Nói "chưa có thông tin" lúc dịch vụ chết là nói sai với ứng viên.

        Họ sẽ tưởng công ty không có dữ liệu và thôi không hỏi nữa, trong khi
        thứ họ cần chỉ là hỏi lại sau ít phút.
        """
        cau, _ = await self._hoi(mo_hinh_tra=None)
        self.assertEqual(cau, qa.CAU_KHONG_GOI_DUOC)
        self.assertNotEqual(cau, qa.CAU_KHONG_BIET)

    async def test_cau_co_so_bia_thi_thay_bang_cau_khong_biet(self):
        cau, nguon = await self._hoi(mo_hinh_tra="Ký túc xá có 4 phòng điều hòa.")
        self.assertEqual(nguon, qa.NGUON_KHONG_BIET)
        self.assertEqual(cau, qa.CAU_KHONG_BIET)

    async def test_mo_hinh_tu_nhan_khong_biet_thi_thay_bang_cau_chuan(self):
        """Lời từ chối phải kèm đúng đường đi tiếp, không để ứng viên cụt ở đó."""
        cau, nguon = await self._hoi(mo_hinh_tra="Mình không biết.")
        self.assertEqual(nguon, qa.NGUON_KHONG_BIET)
        self.assertIn("khung chat", cau)

    async def test_cau_hop_le_thi_duoc_dung(self):
        tra = "Đơn này yêu cầu N4, bạn chưa học nên cần khoảng 6–7 tháng học thêm."
        cau, nguon = await self._hoi(mo_hinh_tra=tra)
        self.assertEqual(nguon, qa.NGUON_MO_HINH)
        self.assertEqual(cau, tra)


class NguCanhDuaVaoTests(unittest.IsolatedAsyncioTestCase):
    async def test_cau_lenh_chua_du_bon_khoi(self):
        goi = AsyncMock(return_value=("Đơn yêu cầu N4.", qa.client.LY_DO_OK))
        with patch.object(qa.client, "sinh_van_ban", goi):
            await qa.tra_loi(
                cau_hoi="Tôi thiếu gì?", ho_so=HO_SO, don=DON,
                doi_chieu=DOI_CHIEU, dieu_kien_nen=DIEU_KIEN,
            )
        prompt = goi.await_args.args[0]
        for manh in ("Trần Thị Thu Hà", "DH-0001", "6–7 tháng", "18 đến 40 tuổi"):
            self.assertIn(manh, prompt)

    async def test_chi_mang_theo_vai_luot_gan_nhat(self):
        """Một câu sai ở lượt hai mà theo tới lượt mười thì nó thành sự thật.

        Chốt hậu kiểm bám vào bốn khối dữ liệu; lịch sử dài làm nó mất chỗ bám.
        """
        lich_su = [
            {"question": f"câu {i}", "answer": f"đáp {i}"} for i in range(10)
        ]
        goi = AsyncMock(return_value=("Đơn yêu cầu N4.", qa.client.LY_DO_OK))
        with patch.object(qa.client, "sinh_van_ban", goi):
            await qa.tra_loi(
                cau_hoi="Tôi thiếu gì?", ho_so=HO_SO, don=DON,
                doi_chieu=DOI_CHIEU, dieu_kien_nen=DIEU_KIEN, lich_su=lich_su,
            )
        prompt = goi.await_args.args[0]
        self.assertIn("câu 9", prompt)
        self.assertNotIn("câu 0", prompt)

    async def test_chua_co_don_thi_van_tra_loi_duoc(self):
        goi = AsyncMock(return_value=("Bạn cần khai thêm thông tin.", qa.client.LY_DO_OK))
        with patch.object(qa.client, "sinh_van_ban", goi):
            cau, _ = await qa.tra_loi(
                cau_hoi="Tôi hợp đơn nào?", ho_so=HO_SO, don="",
                doi_chieu="", dieu_kien_nen=DIEU_KIEN,
            )
        self.assertIn("Chưa chọn đơn nào", goi.await_args.args[0])


class KhongDungKhoTaiLieuTests(unittest.TestCase):
    def test_module_khong_import_gi_lien_quan_kho_tai_lieu(self):
        """Bot này cố ý **không** có kho tài liệu.

        Cho nó đọc kho là mở đường cho một câu trả lời về chi phí nói sai con số
        — kho hiện còn rác nhận dạng ảnh ở 24 trên 32 đoạn. Khung chat hỏi đáp
        làm việc đó, và nó là phần phụ trợ, hỏng thì không kéo theo phần tư vấn.
        """
        import inspect

        nguon = inspect.getsource(qa).lower()
        for tu in ("qdrant", "retriever", "app.rag", "embedding", "app.llm"):
            self.assertNotIn(tu, nguon, f"qa.py không được dính tới {tu!r}")


if __name__ == "__main__":
    unittest.main()


class KhongGopHaiKhoanTienTests(unittest.TestCase):
    """Chốt số không bắt được lỗi này: cả hai con số đều có thật trong dữ liệu.

    Đo trên máy thật ngày 25/09. Ứng viên hỏi "em cần chuẩn bị tổng cộng bao
    nhiêu tiền", bot trả lời "tổng chi phí chương trình là 110.000.000đ, trong đó
    học phí tiếng Nhật là 35.000.000đ".

    110 triệu là chi phí ước tính của riêng một đơn; 35 triệu thuộc gói 90 triệu
    của bảng khóa học. Hai nguồn khác nhau, và không ai biết con số này có bao
    gồm con số kia. Với người đang tính chuyện vay tiền đi nước ngoài, chữ "trong
    đó" ấy là khác biệt giữa chuẩn bị 110 triệu và chuẩn bị 145 triệu.
    """

    # Nguồn nói thẳng quan hệ giữa hai con số, trên cùng một dòng.
    NGUON_CO_QUAN_HE = (
        "LỘ TRÌNH HỌC:\n"
        "- Học phí 35.000.000đ, là một chặng trong tổng chi phí chương trình 90.000.000đ"
    )
    # Hai con số từ hai chỗ khác nhau, không dòng nào nói chúng liên quan.
    NGUON_HAI_CHO = (
        "Chi phí ước tính của riêng đơn này: 110.000.000đ\n"
        "- Học phí 35.000.000đ"
    )

    def test_noi_khoan_nay_nam_trong_khoan_kia_thi_bi_loai(self):
        cau = "Tổng chi phí là 110.000.000 đồng. Trong đó, học phí là 35.000.000 đồng."
        ly_do = qa.kiem_tra(cau, KHOI + "\n" + self.NGUON_HAI_CHO)
        self.assertIsNotNone(ly_do)
        self.assertIn("nằm trong khoản tiền khác", ly_do)

    def test_nguon_noi_ra_quan_he_thi_duoc_nhac_lai(self):
        """Chốt đầu tiên chặn luôn câu đúng — bot im lặng dù có đủ thông tin.

        Dữ liệu nói thẳng "35 triệu là một chặng trong tổng 90 triệu". Chặn câu
        nhắc lại đúng điều đó là biến một chốt chống bịa thành một chốt chống
        trả lời.
        """
        cau = "Học phí 35.000.000đ, nằm trong tổng chi phí chương trình 90.000.000đ."
        self.assertIsNone(qa.kiem_tra(cau, KHOI + "\n" + self.NGUON_CO_QUAN_HE))

    def test_cung_so_tien_viet_hai_cach_van_nhan_ra(self):
        """`35 triệu` và `35.000.000` là cùng một số tiền viết hai cách."""
        cau = "Học phí 35 triệu, nằm trong tổng 90 triệu."
        self.assertIsNone(qa.kiem_tra(cau, KHOI + "\n" + self.NGUON_CO_QUAN_HE))

    def test_neu_tung_khoan_rieng_thi_qua(self):
        cau = ("Chi phí ước tính của đơn là 35.000.000đ. Học phí khóa học là "
               "90.000.000đ. Nhân viên tư vấn sẽ báo con số cuối cùng.")
        self.assertIsNone(qa.kiem_tra(cau, KHOI))

    def test_mot_khoan_tien_kem_cum_bao_ham_thi_van_qua(self):
        """"Đã bao gồm phụ cấp" là câu bình thường, không phải gộp hai khoản."""
        cau = "Học phí 35.000.000đ đã bao gồm tài liệu học."
        self.assertIsNone(qa.kiem_tra(cau, KHOI))
