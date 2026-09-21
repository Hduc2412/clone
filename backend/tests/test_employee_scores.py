"""Kiểm thử sổ điểm nhân viên.

Điểm số ảnh hưởng tới đánh giá và thu nhập của người thật, nên mấy chỗ sau được
soi kỹ nhất:

1. **Không cộng trùng.** Một sự kiện gửi lại hai lần không được thành hai lần
   điểm — đó là cách nhanh nhất để mất lòng tin vào cả bảng điểm.
2. **Không phạt việc trả hồ sơ về hàng đợi.** Phạt ở đó là dạy nhân viên giữ chặt
   hồ sơ họ không xử lý nổi, và người chịu là ứng viên ngồi chờ.
3. **Điểm thuộc về người làm việc, không thuộc người bấm nút.** Quản lý ghi hộ
   kết quả gọi thì điểm vẫn của tư vấn viên đã gọi.
4. **Không ai xem được sổ của người khác**, trừ quản lý.
"""
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, Request

from app.api import staff_scores as api
from app.services import score_service, scoring


ADMIN = {"email": "admin@example.com", "full_name": "Quản trị", "role": "admin"}
MANAGER = {"email": "manager@example.com", "full_name": "Quản lý", "role": "manager"}
TUVAN = {"email": "tu.van@example.com", "full_name": "Tư vấn", "role": "consultant"}
KHAC = {"email": "nguoi.khac@example.com", "full_name": "Người khác", "role": "consultant"}


def http_request() -> Request:
    return Request({"type": "http", "headers": [], "client": ("127.0.0.1", 12345)})


class BangQuyTacTests(unittest.TestCase):
    def test_su_kien_ngoai_bang_khong_sinh_diem(self):
        self.assertIsNone(scoring.points_for("application.updated"))
        self.assertIsNone(scoring.points_for("linh tinh"))

    def test_tra_ho_so_ve_hang_doi_khong_bi_tru_diem(self):
        """Phạt ở đây là dạy nhân viên ôm hồ sơ họ không xử lý nổi."""
        self.assertEqual(scoring.points_for("application.released"), 0)

    def test_goi_duoc_khach_an_diem_cao_hon_han_goi_khong_gap(self):
        self.assertGreater(
            scoring.points_for("appointment.completed"),
            scoring.points_for("appointment.unreachable"),
        )

    def test_goi_khong_gap_van_duoc_ghi_nhan(self):
        """Nhân viên đã bỏ công gọi, và kết quả đó có ích cho người gọi lần sau."""
        self.assertGreater(scoring.points_for("appointment.unreachable"), 0)

    def test_xuat_canh_la_moc_dang_gia_nhat(self):
        self.assertEqual(
            max(rule.points for rule in scoring.RULES.values()),
            scoring.points_for("application.departed"),
        )


class NhanViecSomTests(unittest.TestCase):
    def setUp(self):
        self.moc = datetime(2026, 9, 16, 9, 0, tzinfo=UTC)

    def test_nhan_trong_khung_gio_thi_duoc_thuong(self):
        self.assertTrue(
            scoring.is_fast_pickup(self.moc, self.moc + timedelta(minutes=30))
        )

    def test_nhan_muon_thi_khong(self):
        self.assertFalse(
            scoring.is_fast_pickup(self.moc, self.moc + timedelta(hours=5))
        )

    def test_thieu_moc_thoi_gian_thi_khong_doan_bua(self):
        self.assertFalse(scoring.is_fast_pickup(None, self.moc))
        self.assertFalse(scoring.is_fast_pickup(self.moc, None))

    def test_moc_thoi_gian_lech_mui_gio_khong_lam_no_chuong_trinh(self):
        """Một bên có múi giờ, một bên không — trả False chứ không ném lỗi."""
        self.assertFalse(
            scoring.is_fast_pickup(self.moc, datetime(2026, 9, 16, 9, 30))
        )


class GhiDiemTests(unittest.IsolatedAsyncioTestCase):
    async def test_ghi_du_hai_dong_khi_nhan_viec_som(self):
        """Hai dòng riêng để nhân viên thấy vì sao hôm nay hơn hôm qua."""
        moc = datetime(2026, 9, 16, 9, 0, tzinfo=UTC)
        with patch.object(score_service.store, "record", AsyncMock(side_effect=lambda d: d)) as rec:
            await score_service.award_pickup(
                staff_email=TUVAN["email"],
                application_code="HS-AAA111",
                registered_at=moc,
                accepted_at=moc + timedelta(minutes=10),
            )
        actions = [call.args[0]["action"] for call in rec.await_args_list]
        self.assertEqual(actions, ["application.accepted", "application.accepted_fast"])

    async def test_nhan_muon_chi_ghi_mot_dong(self):
        moc = datetime(2026, 9, 16, 9, 0, tzinfo=UTC)
        with patch.object(score_service.store, "record", AsyncMock(side_effect=lambda d: d)) as rec:
            await score_service.award_pickup(
                staff_email=TUVAN["email"],
                application_code="HS-AAA111",
                registered_at=moc,
                accepted_at=moc + timedelta(hours=6),
            )
        self.assertEqual(len(rec.await_args_list), 1)

    async def test_khong_co_nguoi_phu_trach_thi_khong_ghi_gi(self):
        with patch.object(score_service.store, "record", AsyncMock()) as rec:
            result = await score_service.award(
                staff_email=None,
                action="application.accepted",
                reference_type="recruitment_application",
                reference_code="HS-AAA111",
            )
        self.assertIsNone(result)
        rec.assert_not_awaited()

    async def test_su_kien_ngoai_bang_khong_cham_vao_so(self):
        with patch.object(score_service.store, "record", AsyncMock()) as rec:
            await score_service.award(
                staff_email=TUVAN["email"],
                action="application.updated",
                reference_type="recruitment_application",
                reference_code="HS-AAA111",
            )
        rec.assert_not_awaited()

    async def test_so_diem_hong_khong_lam_hong_viec_chinh(self):
        """Nhận hồ sơ mà sổ điểm trục trặc thì việc nhận vẫn phải xong."""
        with patch.object(score_service.store, "record", AsyncMock(side_effect=RuntimeError("mat ket noi"))):
            result = await score_service.award(
                staff_email=TUVAN["email"],
                action="application.accepted",
                reference_type="recruitment_application",
                reference_code="HS-AAA111",
            )
        self.assertIsNone(result, "phải nuốt lỗi, không được ném lên")

    async def test_ghi_trung_thi_bo_qua(self):
        """Tầng lưu trữ trả None khi index duy nhất chặn — coi như không có gì."""
        with patch.object(score_service.store, "record", AsyncMock(return_value=None)):
            result = await score_service.award(
                staff_email=TUVAN["email"],
                action="application.accepted",
                reference_type="recruitment_application",
                reference_code="HS-AAA111",
            )
        self.assertIsNone(result)

    async def test_ket_qua_goi_ghi_dung_ten_hanh_dong(self):
        with patch.object(score_service.store, "record", AsyncMock(side_effect=lambda d: d)) as rec:
            await score_service.award_appointment_result(
                staff_email=TUVAN["email"],
                appointment_code="LH-001",
                status="completed",
            )
        self.assertEqual(rec.await_args.args[0]["action"], "appointment.completed")

    async def test_trang_thai_khong_tinh_diem_thi_bo_qua(self):
        with patch.object(score_service.store, "record", AsyncMock()) as rec:
            await score_service.award_appointment_result(
                staff_email=TUVAN["email"],
                appointment_code="LH-001",
                status="cancelled",
            )
        rec.assert_not_awaited()


class SuaTayTests(unittest.IsolatedAsyncioTestCase):
    async def test_ghi_them_dong_moi_chu_khong_sua_dong_cu(self):
        with patch.object(score_service.store, "record", AsyncMock(side_effect=lambda d: d)) as rec:
            await score_service.adjust(
                staff_email=TUVAN["email"],
                points=5,
                note="Hỗ trợ đồng nghiệp trực cuối tuần",
                created_by=MANAGER["email"],
            )
        document = rec.await_args.args[0]
        self.assertEqual(document["source"], score_service.store.SOURCE_MANUAL)
        self.assertEqual(document["created_by"], MANAGER["email"])
        self.assertEqual(document["note"], "Hỗ trợ đồng nghiệp trực cuối tuần")

    def test_bat_buoc_ghi_ly_do(self):
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            api.AdjustRequest(points=5, note="")

    def test_chan_con_so_lac_tay(self):
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            api.AdjustRequest(points=5000, note="gõ thừa số 0")


class PhanQuyenTests(unittest.IsolatedAsyncioTestCase):
    async def test_tu_van_vien_chi_thay_dong_cua_minh(self):
        with patch.object(api.store, "totals", AsyncMock(return_value=[])) as totals:
            await api.scoreboard(None, None, TUVAN)
        self.assertEqual(totals.await_args.args[0]["staff_email"], TUVAN["email"])

    async def test_quan_ly_thay_toan_doi(self):
        with patch.object(api.store, "totals", AsyncMock(return_value=[])) as totals:
            await api.scoreboard(None, None, MANAGER)
        self.assertNotIn("staff_email", totals.await_args.args[0])

    async def test_khong_xem_duoc_so_cua_nguoi_khac(self):
        with self.assertRaises(HTTPException) as ctx:
            await api.staff_ledger(KHAC["email"], None, None, 50, TUVAN)
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_tu_xem_so_cua_minh_thi_duoc(self):
        with (
            patch.object(api.store, "totals", AsyncMock(return_value=[{"points": 12}])),
            patch.object(api.store, "list_events", AsyncMock(return_value=[])),
            patch.object(api.store, "breakdown", AsyncMock(return_value=[])),
        ):
            result = await api.staff_ledger(TUVAN["email"], None, None, 50, TUVAN)
        self.assertEqual(result["points"], 12)

    async def test_quan_ly_xem_duoc_so_cua_nhan_vien(self):
        with (
            patch.object(api.store, "totals", AsyncMock(return_value=[])),
            patch.object(api.store, "list_events", AsyncMock(return_value=[])),
            patch.object(api.store, "breakdown", AsyncMock(return_value=[])),
        ):
            result = await api.staff_ledger(TUVAN["email"], None, None, 50, ADMIN)
        self.assertEqual(result["points"], 0)

    async def test_sua_tay_cho_nhan_vien_khong_co_that_thi_bao_loi(self):
        with patch.object(api, "get_staff_user_by_email", AsyncMock(return_value=None)):
            with self.assertRaises(HTTPException) as ctx:
                await api.adjust(
                    "ma@example.com",
                    api.AdjustRequest(points=5, note="thưởng cuối tuần"),
                    http_request(),
                    MANAGER,
                )
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_ngay_viet_sai_bao_loi_ro(self):
        with self.assertRaises(HTTPException) as ctx:
            await api.scoreboard("16-09-2026", None, ADMIN)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Ngày không hợp lệ", ctx.exception.detail)


class BangQuyTacPhatRaTests(unittest.IsolatedAsyncioTestCase):
    async def test_nhan_vien_doc_duoc_luat_ap_len_minh(self):
        with patch.object(api.store, "totals", AsyncMock(return_value=[])):
            result = await api.scoreboard(None, None, TUVAN)
        actions = {rule["action"] for rule in result["rules"]}
        self.assertIn("appointment.completed", actions)
        self.assertNotIn(
            "manual.adjustment", actions, "điều chỉnh tay không phải một luật"
        )


if __name__ == "__main__":
    unittest.main()
