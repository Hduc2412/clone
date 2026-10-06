"""Hẹn gặp nhân viên từ hành trình tư vấn — và một chốt chặn chống lệch quy tắc.

## Khoảng trống này tồn tại từ đầu

Rà soát 01/10 lần ngược `create_appointment` và tìm ra đúng **một** nơi gọi:
`booking/booking_service.py`, tức khung chat. Hành trình chính trên website không
có đường nào tạo lịch hẹn, nên màn hình `/admin/appointments` luôn trống với ai
chỉ đi theo hành trình mới — và chính dòng chữ trên đó thừa nhận: *"chờ lịch mới
từ chatbot"*.

## Ca quan trọng nhất ở đây là ca chống lệch quy tắc

Quy tắc giờ nhận lịch nay có **hai bản**: một trong `booking_service._extract_time`
(của khung chat, không sửa vì nó đang chạy đúng), một trong
`consultation/lich_hen.kiem_gio`. Bản sao có người canh thì an toàn; bản sao
không ai canh mới là nợ.

`test_hai_ban_quy_tac_gio_khong_duoc_lech` so hai bản trên cùng một dải giờ. Ngày
nào ai đó nới giờ ở một bên, ca này đỏ và nói rõ giờ nào lệch.
"""
import unittest
from datetime import timedelta

from app.consultation import lich_hen
from app.core.timeutil import local_today


class KiemGioTests(unittest.TestCase):
    def test_gio_trong_khung_duoc_nhan_va_chuan_hoa(self):
        self.assertEqual(lich_hen.kiem_gio("8:0"), "08:00")
        self.assertEqual(lich_hen.kiem_gio("09:30"), "09:30")
        self.assertEqual(lich_hen.kiem_gio("11:30"), "11:30")
        self.assertEqual(lich_hen.kiem_gio("13:30"), "13:30")
        self.assertEqual(lich_hen.kiem_gio("17:00"), "17:00")

    def test_gio_nghi_trua_bi_tu_choi(self):
        """Giờ liên hệ ghi "8h đến 17h" cho gọn, nhưng đặt lịch thì phải chính xác.

        Khoảng nghỉ trưa không có ai ở văn phòng. Nhận một cái hẹn 12h là hẹn
        một người tới gặp một cái bàn trống.
        """
        for gio in ("11:31", "12:00", "13:29"):
            with self.assertRaises(lich_hen.GioKhongHopLe, msg=gio):
                lich_hen.kiem_gio(gio)

    def test_ngoai_gio_lam_viec_bi_tu_choi(self):
        for gio in ("07:59", "17:01", "20:00", "00:00"):
            with self.assertRaises(lich_hen.GioKhongHopLe, msg=gio):
                lich_hen.kiem_gio(gio)

    def test_loi_nhan_noi_ro_hai_khung_gio(self):
        """Khách cần biết chọn lại giờ nào, không cần biết mình sai cú pháp."""
        with self.assertRaises(lich_hen.GioKhongHopLe) as ctx:
            lich_hen.kiem_gio("12:00")
        cau = str(ctx.exception)
        self.assertIn("08:00", cau)
        self.assertIn("13:30", cau)

    def test_cu_phap_sai_cung_bao_duoc_dang_can_viet(self):
        with self.assertRaises(lich_hen.GioKhongHopLe) as ctx:
            lich_hen.kiem_gio("chín giờ sáng")
        self.assertIn("09:30", str(ctx.exception))


class KiemNgayTests(unittest.TestCase):
    def _ngay_lam_viec(self, cach: int) -> str:
        """Một ngày cách hôm nay `cach` ngày, nhảy qua Chủ Nhật.

        Không ghim ngày cố định: ca kiểm thử ghim ngày trong khi dữ liệu tính
        theo hôm nay là bom hẹn giờ, đúng loại vừa phải tháo ở
        `test_matching_seeded_data` ngày 05/10.
        """
        d = local_today() + timedelta(days=cach)
        while d.weekday() in lich_hen.NGAY_NGHI:
            d += timedelta(days=1)
        return d.isoformat()

    def test_ngay_sap_toi_duoc_nhan(self):
        self.assertEqual(
            lich_hen.kiem_ngay(self._ngay_lam_viec(3)), self._ngay_lam_viec(3)
        )

    def test_ngay_da_qua_bi_tu_choi(self):
        qua = (local_today() - timedelta(days=1)).isoformat()
        with self.assertRaises(lich_hen.GioKhongHopLe) as ctx:
            lich_hen.kiem_ngay(qua)
        self.assertIn("đã qua", str(ctx.exception))

    def test_chu_nhat_bi_tu_choi(self):
        d = local_today()
        while d.weekday() != 6:
            d += timedelta(days=1)
        with self.assertRaises(lich_hen.GioKhongHopLe) as ctx:
            lich_hen.kiem_ngay(d.isoformat())
        self.assertIn("Chủ Nhật", str(ctx.exception))

    def test_hen_qua_xa_bi_tu_choi(self):
        """Hẹn ba tháng sau thì tới lúc gọi cả hai bên đều quên vì sao hẹn."""
        xa = (
            local_today() + timedelta(days=lich_hen.TOI_DA_NGAY + 1)
        ).isoformat()
        with self.assertRaises(lich_hen.GioKhongHopLe):
            lich_hen.kiem_ngay(xa)


class ChongLechQuyTacTests(unittest.TestCase):
    """Hai bản quy tắc giờ không được lệch nhau.

    Khung chat có bản riêng (`booking_service._extract_time`) và nó không bị sửa
    vì đang chạy đúng. Bản sao ở `consultation/lich_hen` phải nói y như vậy —
    khách hẹn 12h qua chat bị từ chối, qua hành trình tư vấn cũng phải bị từ
    chối, nếu không thì cùng một công ty trả lời hai kiểu.
    """

    def test_hai_ban_quy_tac_gio_khong_duoc_lech(self):
        from app.booking.booking_service import _extract_time

        lech: list[str] = []
        for tong_phut in range(0, 24 * 60, 5):
            gio = f"{tong_phut // 60:02d}:{tong_phut % 60:02d}"

            try:
                _extract_time(gio)
                chat_nhan = True
            except ValueError:
                chat_nhan = False

            try:
                lich_hen.kiem_gio(gio)
                tu_van_nhan = True
            except lich_hen.GioKhongHopLe:
                tu_van_nhan = False

            if chat_nhan != tu_van_nhan:
                lech.append(
                    f"{gio}: khung chat {'nhận' if chat_nhan else 'từ chối'}, "
                    f"hành trình tư vấn {'nhận' if tu_van_nhan else 'từ chối'}"
                )

        self.assertEqual(
            lech,
            [],
            "Hai bản quy tắc giờ đã lệch nhau — cùng một công ty trả lời hai "
            "kiểu cho cùng một giờ:\n  " + "\n  ".join(lech),
        )


class BanGhiLichHenTests(unittest.TestCase):
    def test_booking_key_giu_dung_cong_thuc_de_index_chong_trung(self):
        """Index duy nhất nằm trên `booking_key`. Đổi công thức là mất chốt chặn.

        Khách bấm hai lần, hay vừa hẹn qua chat vừa hẹn qua hành trình tư vấn,
        thì chỉ một lịch được tạo — nhân viên không gọi hai lần cho cùng một
        người vào cùng một giờ.
        """
        ban = lich_hen.dung_ban_ghi(
            session_id="s",
            full_name="Nguyễn Thị Mai",
            phone="0912345678",
            ngay="2026-10-20",
            gio="09:30",
        )
        self.assertEqual(ban["booking_key"], "0912345678|2026-10-20|09:30")

    def test_ma_lich_cung_khuon_voi_ma_khung_chat_sinh_ra(self):
        """Hai nguồn thì hai mã, nhưng phải đọc như một — nhân viên không cần học
        hai cách đọc mã cho cùng một loại việc."""
        import re

        ma = lich_hen.sinh_ma("2026-10-20")
        self.assertRegex(ma, r"^TV-20261020-[0-9A-F]{4}$")

    def test_ban_ghi_ghi_ro_nguon_de_truy_nguoc(self):
        ban = lich_hen.dung_ban_ghi(
            session_id="s",
            full_name="A B",
            phone="0912345678",
            ngay="2026-10-20",
            gio="09:30",
            support_code="HT-ABC123",
            job_order_code="DH-0001",
        )
        self.assertEqual(ban["source"], "tu_van")
        self.assertEqual(ban["support_code"], "HT-ABC123")
        self.assertEqual(ban["job_order_code"], "DH-0001")
        self.assertEqual(ban["conversation_id"], "s")

    def test_mo_ta_doc_duoc_cho_nhan_vien(self):
        cau = lich_hen.mo_ta(
            {
                "appointment_date": "2026-10-20",
                "appointment_time": "09:30",
                "meeting_kind": "truc_tiep",
                "job_order_code": "DH-0001",
            }
        )
        self.assertIn("09:30", cau)
        self.assertIn("20/10/2026", cau)
        self.assertIn("trực tiếp", cau)
        self.assertIn("DH-0001", cau)


class ThanYeuCauHoTroTests(unittest.TestCase):
    """Kiểm giờ ở tầng thân yêu cầu, để khách nhận câu nói rõ phải sửa gì.

    Kiểm sâu hơn trong luồng thì lỗi giờ sai rơi vào nhánh "không tạo được lịch,
    nuốt lỗi" — yêu cầu vẫn vào hàng đợi nhưng khách không biết giờ mình chọn đã
    bị bỏ, và vẫn tưởng mình có hẹn.
    """

    def _ngay_lam_viec(self) -> str:
        d = local_today() + timedelta(days=3)
        while d.weekday() in lich_hen.NGAY_NGHI:
            d += timedelta(days=1)
        return d.isoformat()

    def _tao(self, **them):
        from app.api.support import SupportRequestBody

        goc = {
            "kind": "gap_mat",
            "full_name": "Nguyễn Thị Mai",
            "phone": "0912345678",
        }
        return SupportRequestBody(**{**goc, **them})

    def test_khong_chon_gio_van_gui_duoc(self):
        """Bắt chọn giờ mới được xin gặp là dựng một cửa ở chỗ không cần cửa."""
        than = self._tao()
        self.assertIsNone(than.appointment_date)
        self.assertIsNone(than.appointment_time)

    def test_chon_du_ngay_va_gio_thi_nhan(self):
        than = self._tao(
            appointment_date=self._ngay_lam_viec(), appointment_time="9:30"
        )
        self.assertEqual(than.appointment_time, "09:30")

    def test_chi_co_ngay_thi_tu_choi(self):
        with self.assertRaises(Exception):
            self._tao(appointment_date=self._ngay_lam_viec())

    def test_chi_co_gio_thi_tu_choi(self):
        with self.assertRaises(Exception):
            self._tao(appointment_time="09:30")

    def test_gio_nghi_trua_bi_tu_choi_ngay_o_than_yeu_cau(self):
        with self.assertRaises(Exception):
            self._tao(
                appointment_date=self._ngay_lam_viec(), appointment_time="12:00"
            )

    def test_hinh_thuc_gap_chi_nhan_hai_gia_tri(self):
        with self.assertRaises(Exception):
            self._tao(
                appointment_date=self._ngay_lam_viec(),
                appointment_time="09:30",
                meeting_kind="qua_dien_thoai",
            )


class BanGiaoMangTheoLichHenTests(unittest.TestCase):
    """Lịch hẹn là thứ duy nhất trong bản bàn giao có mốc thời gian.

    Nó quyết định thứ tự việc trong ngày của nhân viên. Một bản đầy đủ mà không
    nói "khách hẹn 9h30 sáng mai" thì đọc xong vẫn phải mở màn hình khác để biết
    có phải gọi ngay không.
    """

    def test_ban_giao_in_lich_hen(self):
        from app.agent import ban_giao, state

        ra = ban_giao.dung(
            profile=None,
            trang_thai=state.suy_ra(profile=None),
            lich_hen=[
                {
                    "appointment_date": "2026-10-20",
                    "appointment_time": "09:30",
                    "meeting_kind": "truc_tuyen",
                    "job_order_code": "DH-0001",
                    "status": "pending",
                }
            ],
        )
        self.assertIn("KHÁCH ĐÃ CHỌN KHUNG GIỜ", ra)
        self.assertIn("09:30", ra)
        self.assertIn("20/10/2026", ra)

    def test_khong_co_lich_thi_khong_hien_tieu_de_trong(self):
        from app.agent import ban_giao, state

        ra = ban_giao.dung(profile=None, trang_thai=state.suy_ra(profile=None))
        self.assertNotIn("KHUNG GIỜ", ra)

    def test_hai_duong_ban_giao_deu_nap_lich_hen(self):
        """Đường cho khách xem trước và đường đính vào yêu cầu phải khớp nhau."""
        import pathlib
        import re

        goc = pathlib.Path(__file__).resolve().parent.parent / "app" / "api"
        for ten in ("agent.py", "support.py"):
            nguon = (goc / ten).read_text(encoding="utf-8")
            self.assertTrue(
                re.search(r"lich_hen=await list_appointments_for_session\(", nguon),
                f"{ten}: bản bàn giao không nạp lịch hẹn",
            )


if __name__ == "__main__":
    unittest.main()
