"""Hàng đợi hỗ trợ — việc cần người, tách khỏi hàng đợi tuyển dụng.

Hai ca đáng giá nhất bộ này:

- `test_khong_luu_bat_ky_du_lieu_suc_khoe_nao` — khách gửi yêu cầu vì lo chuyện
  sức khỏe, nhưng bản ghi không được có chỗ nào ghi bệnh gì.
- `test_hai_nguoi_cung_bam_nhan_thi_mot_nguoi_truot` — nếu không, hai nhân viên
  cùng gọi cho một khách và cùng nói những điều khác nhau.
"""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, Request

from app.api import support
from app.db import support_requests as store


STAFF = {"email": "tu.van@example.com", "full_name": "Tư vấn", "role": "consultant"}
KHAC = {"email": "nguoi.khac@example.com", "full_name": "Người khác", "role": "consultant"}
QUAN_LY = {"email": "quan.ly@example.com", "full_name": "Quản lý", "role": "manager"}

SESSION = "3f2a9c41-7d18-4b6e-9a05-2c8e1d47b930"


def http_request() -> Request:
    return Request({"type": "http", "headers": [], "client": ("127.0.0.1", 12345)})


def body(**ghi_de) -> support.SupportRequestBody:
    gia_tri = {
        "kind": "nhan_tin",
        "message": "Em muốn hỏi thêm về chi phí ạ.",
        "full_name": "Nguyễn Thị Lan",
        "phone": "0912345678",
        "job_order_code": "DH-0001",
        # KHÔNG có `advice_block`: thân yêu cầu không còn nhận nó nữa. Máy chủ tự
        # dựng lại từ nhật ký giới thiệu — xem `KhoiDoiChieuDoMayChuDungTests`.
    }
    gia_tri.update(ghi_de)
    return support.SupportRequestBody(**gia_tri)


def ban_ghi(**ghi_de) -> dict:
    document = {
        "code": "HT-A1B2C3",
        "kind": "nhan_tin",
        "session_id": SESSION,
        "full_name": "Nguyễn Thị Lan",
        "phone": "0912345678",
        "message": "Em muốn hỏi thêm về chi phí ạ.",
        "job_order_code": "DH-0001",
        "advice_block": "ĐƠN ĐANG XÉT: DH-0001",
        "status": store.STATUS_CHO,
        "assigned_to": None,
        "reply": None,
        "handled_at": None,
    }
    document.update(ghi_de)
    return document


class GuiYeuCauTests(unittest.IsolatedAsyncioTestCase):
    async def _gui(self, payload, *, khoi="ĐƠN ĐANG XÉT: DH-0001", dang_cho=None):
        viet = AsyncMock(side_effect=lambda doc: ({**doc, "status": store.STATUS_CHO, "notified_at": None}, True))
        with patch.object(store, "create_request", viet), patch.object(store, "danh_dau_da_thong_bao", AsyncMock()), \
             patch.object(
                 store, "tim_yeu_cau_dang_cho", AsyncMock(return_value=dang_cho)
             ), \
             patch.object(
                 support.khoi_doi_chieu, "dung_tu_nhat_ky",
                 AsyncMock(return_value=khoi),
             ), \
             patch.object(support, "create_notification", AsyncMock()), \
             patch.object(support.rate_limiter, "check", lambda *a, **k: None):
            ra = await support.gui_yeu_cau(SESSION, payload, http_request())
        return ra, (viet.await_args.args[0] if viet.await_args else None), viet

    async def test_tao_duoc_yeu_cau_va_tra_ma(self):
        ra, _, _ = await self._gui(body())
        self.assertTrue(ra["code"].startswith("HT-"))

    async def test_noi_ro_khung_gio_lien_he_ngay_trong_cau_tra_ve(self):
        """Câu này là thứ khách đọc đầu tiên sau khi bấm gửi.

        Không nói khung giờ ở đây thì người gửi lúc mười một giờ đêm sẽ ngồi đợi
        một câu trả lời không tới — và đó là cách nhanh nhất để mất một người
        thật sự đang quan tâm.
        """
        ra, _, _ = await self._gui(body())
        self.assertIn(support.GIO_LIEN_HE, ra["message"])
        self.assertIn("liên hệ", ra["message"].lower())

    async def test_mang_theo_anh_chup_ket_qua_doi_chieu(self):
        """Nhân viên gọi lại đọc được chính thứ khách đã đọc."""
        _, doc, _ = await self._gui(body())
        self.assertIn("DH-0001", doc["advice_block"])

    async def test_chuan_hoa_so_dien_thoai(self):
        _, doc, _ = await self._gui(body(phone="+84912345678"))
        self.assertEqual(doc["phone"], "0912345678")

    async def test_khong_luu_bat_ky_du_lieu_suc_khoe_nao(self):
        """Khách lo chuyện sức khỏe vẫn gửi được, nhưng bản ghi không ghi bệnh gì.

        Chẩn đoán bệnh theo người ta đi rất xa nếu lộ, mà giá trị nghiệp vụ bằng
        không — buổi khám mới là chỗ kết luận. Ca này chặn việc ai đó thêm một
        trường kiểu `health_status` về sau.
        """
        _, doc, _ = await self._gui(body(kind="hoc_tap", message="Em lo về sức khỏe"))
        cam = ("health", "disease", "benh", "hepatitis", "hiv", "diagnosis", "medical")
        for khoa in doc:
            for tu in cam:
                self.assertNotIn(tu, khoa.lower(), f"không được có trường {khoa!r}")

    async def test_ba_loai_deu_gui_duoc(self):
        for loai in store.KINDS:
            with self.subTest(loai=loai):
                _, doc, _ = await self._gui(body(kind=loai))
                self.assertEqual(doc["kind"], loai)

    async def test_loai_la_bi_tu_choi_ngay_o_mo_hinh_du_lieu(self):
        with self.assertRaises(Exception):
            body(kind="linh_tinh")


class TranhChapTests(unittest.IsolatedAsyncioTestCase):
    async def test_hai_nguoi_cung_bam_nhan_thi_mot_nguoi_truot(self):
        """Không chặn thì hai nhân viên cùng gọi một khách, nói hai điều khác nhau."""
        with patch.object(store, "claim", AsyncMock(return_value=None)), \
             patch.object(store, "get_request",
                          AsyncMock(return_value=ban_ghi(assigned_to=KHAC["email"]))), \
             patch.object(support, "audit_action", AsyncMock()):
            with self.assertRaises(HTTPException) as bat:
                await support.nhan_xu_ly("HT-A1B2C3", http_request(), current_user=STAFF)
        self.assertEqual(bat.exception.status_code, 409)
        self.assertIn(KHAC["email"], bat.exception.detail)

    async def test_khong_co_yeu_cau_thi_bao_404_chu_khong_phai_409(self):
        """Hai chuyện dẫn tới hai hành động khác nhau cho người đang bấm."""
        with patch.object(store, "claim", AsyncMock(return_value=None)), \
             patch.object(store, "get_request", AsyncMock(return_value=None)):
            with self.assertRaises(HTTPException) as bat:
                await support.nhan_xu_ly("HT-A1B2C3", http_request(), current_user=STAFF)
        self.assertEqual(bat.exception.status_code, 404)

    async def test_nhan_duoc_thi_doi_trang_thai(self):
        nhan = AsyncMock(return_value=ban_ghi(assigned_to=STAFF["email"],
                                              status=store.STATUS_DANG_XU_LY))
        with patch.object(store, "claim", nhan), \
             patch.object(support, "audit_action", AsyncMock()):
            ra = await support.nhan_xu_ly("HT-A1B2C3", http_request(), current_user=STAFF)
        self.assertEqual(ra["status"], store.STATUS_DANG_XU_LY)


class QuyenTraLoiTests(unittest.IsolatedAsyncioTestCase):
    async def _tra_loi(self, *, giu: str | None, nguoi: dict):
        with patch.object(store, "get_request",
                          AsyncMock(return_value=ban_ghi(assigned_to=giu))), \
             patch.object(store, "close_request",
                          AsyncMock(return_value=ban_ghi(status=store.STATUS_XONG))), \
             patch.object(support, "audit_action", AsyncMock()):
            return await support.tra_loi(
                "HT-A1B2C3", support.ReplyBody(reply="Chào bạn, ..."),
                http_request(), current_user=nguoi,
            )

    async def test_nguoi_dang_giu_tra_loi_duoc(self):
        ra = await self._tra_loi(giu=STAFF["email"], nguoi=STAFF)
        self.assertEqual(ra["status"], store.STATUS_XONG)

    async def test_nguoi_khac_khong_tra_loi_duoc(self):
        with self.assertRaises(HTTPException) as bat:
            await self._tra_loi(giu=STAFF["email"], nguoi=KHAC)
        self.assertEqual(bat.exception.status_code, 403)

    async def test_quan_ly_tra_loi_duoc_de_viec_khong_ket(self):
        """Người nhận nghỉ thì việc phải có đường đi tiếp."""
        ra = await self._tra_loi(giu=STAFF["email"], nguoi=QUAN_LY)
        self.assertEqual(ra["status"], store.STATUS_XONG)

    async def test_chua_ai_nhan_thi_ai_tra_loi_cung_duoc(self):
        ra = await self._tra_loi(giu=None, nguoi=KHAC)
        self.assertEqual(ra["status"], store.STATUS_XONG)


class KhachChiXemDuocPhanCuaMinhTests(unittest.IsolatedAsyncioTestCase):
    async def test_khong_lo_truong_noi_bo_cho_khach(self):
        """Danh sách cho phép, không phải danh sách loại trừ.

        Thêm một trường nội bộ vào bản ghi sau này sẽ không vô tình lọt ra.
        """
        doc = ban_ghi(assigned_to="nhan.vien@example.com", handled_by="ai.do@example.com")
        with patch.object(store, "list_for_session", AsyncMock(return_value=[doc])):
            ra = await support.yeu_cau_cua_toi(SESSION)
        khach_thay = ra["items"][0]
        for cam in ("assigned_to", "handled_by", "phone", "session_id", "advice_block"):
            self.assertNotIn(cam, khach_thay, f"khách không được thấy {cam!r}")
        self.assertIn("reply", khach_thay)


if __name__ == "__main__":
    unittest.main()
