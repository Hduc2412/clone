"""Yêu cầu hỗ trợ: lưu được rồi thì không được mất, và không được nhân đôi.

Hai lỗi từ bản rà soát 30/09, cả hai thuộc loại **hỏng ở chỗ không ai nhìn**.

## P1 — lưu thành công nhưng khách nhận 500

Bản rà soát dựng cảnh `create_notification` ném ngoại lệ. Kết quả đo được: HTTP
500, mà số yêu cầu trong bảng **vẫn tăng 1**. Khách tưởng mình chưa gửi được nên
bấm lại; lần này nhận 201, nhưng nhánh chống trùng trả yêu cầu đã có và **bỏ qua
việc ghi thông báo** — nên số thông báo vẫn bằng không, và không nhân viên nào biết
có người đang chờ.

Đây là dạng xấu nhất trong các dạng hỏng: dữ liệu vào rồi, khách nghĩ là thất bại,
nhân viên không thấy gì, và không ai có lý do để đi tìm.

## P2 — chống trùng chưa nguyên tử

`tim_yeu_cau_dang_cho` rồi `create_request` là đọc-rồi-ghi. Hai lần bấm sát nhau thì
cả hai truy vấn đều thấy "chưa có", cả hai đều ghi. Bản rà soát tái hiện có kiểm
soát: hai response 201, hai bản ghi cùng phiên cùng loại.

Chốt chặn thật phải nằm ở **index duy nhất**, không ở lần tra trước đó.
"""
import unittest
from unittest.mock import AsyncMock, patch

from pymongo.errors import DuplicateKeyError

from app.api import support
from app.db import support_requests as store


SESSION = "11111111-1111-4111-8111-111111111111"


def http_request():
    from fastapi import Request

    return Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1234)})


def body(**ghi_de):
    gia_tri = {
        "kind": "gap_mat",
        "full_name": "Nguyễn Thị Lan",
        "phone": "0912345678",
        "job_order_code": "DH-0001",
    }
    gia_tri.update(ghi_de)
    return support.SupportRequestBody(**gia_tri)


class ThongBaoHongKhongLamMatYeuCauTests(unittest.IsolatedAsyncioTestCase):
    async def _gui(self, *, tao, bao=None, danh_dau=None):
        bao = bao or AsyncMock()
        danh_dau = danh_dau or AsyncMock()
        with patch.object(store, "create_request", tao), patch.object(
            store, "danh_dau_da_thong_bao", danh_dau
        ), patch.object(
            support.khoi_doi_chieu, "dung_tu_nhat_ky", AsyncMock(return_value=None)
        ), patch.object(
            support, "create_notification", bao
        ), patch.object(support.rate_limiter, "check", lambda *a, **k: None):
            ra = await support.gui_yeu_cau(SESSION, body(), http_request())
        return ra, bao, danh_dau

    async def test_thong_bao_hong_van_tra_ve_thanh_cong_cho_khach(self):
        """Ném lỗi lúc này là trả 500 cho một thao tác đã thành công."""
        tao = AsyncMock(
            return_value=({"code": "HT-A1", "kind": "gap_mat", "full_name": "L", "notified_at": None}, True)
        )
        bao = AsyncMock(side_effect=RuntimeError("mongodb mất kết nối"))
        ra, _, danh_dau = await self._gui(tao=tao, bao=bao)
        self.assertEqual(ra["code"], "HT-A1")
        self.assertIn("Đã gửi", ra["message"])
        # Không đánh dấu đã báo: mốc còn `None` để lần gửi lại thử lại.
        danh_dau.assert_not_awaited()

    async def test_bao_thanh_cong_thi_ghi_moc_da_bao(self):
        tao = AsyncMock(
            return_value=({"code": "HT-A1", "kind": "gap_mat", "full_name": "L", "notified_at": None}, True)
        )
        _, bao, danh_dau = await self._gui(tao=tao)
        bao.assert_awaited_once()
        danh_dau.assert_awaited_once_with("HT-A1")

    async def test_gui_lai_khi_lan_truoc_bao_hong_thi_BAO_BU(self):
        """Ca trung tâm của file.

        Lần đầu: yêu cầu lưu được, thông báo hỏng. Lần hai: nhánh chống trùng trả
        lại yêu cầu cũ — và **phải thử báo lại**, không được im lặng bỏ qua. Bản
        trước bỏ qua, nên nhân viên không bao giờ biết có người đang chờ.
        """
        cu = {"code": "HT-A1", "kind": "gap_mat", "full_name": "L", "notified_at": None}
        tao = AsyncMock(return_value=(cu, False))
        _, bao, danh_dau = await self._gui(tao=tao)
        bao.assert_awaited_once()
        danh_dau.assert_awaited_once_with("HT-A1")

    async def test_gui_lai_khi_lan_truoc_da_bao_thi_KHONG_bao_lai(self):
        """Đã báo rồi thì thôi — nhân viên không cần hai thông báo cho một việc."""
        cu = {
            "code": "HT-A1",
            "kind": "gap_mat",
            "full_name": "L",
            "notified_at": "2026-09-30T10:00:00",
        }
        tao = AsyncMock(return_value=(cu, False))
        _, bao, danh_dau = await self._gui(tao=tao)
        bao.assert_not_awaited()
        danh_dau.assert_not_awaited()


class ChongTrungBangIndexTests(unittest.IsolatedAsyncioTestCase):
    """Chốt chặn phải nằm ở tầng dữ liệu, không ở lần tra trước đó."""

    async def test_trung_index_thi_tra_lai_yeu_cau_dang_mo(self):
        """Đây là đường chạy khi hai lần bấm sát nhau: lần sau ăn `DuplicateKeyError`."""
        cu = {"code": "HT-CU", "kind": "gap_mat", "notified_at": None}

        class _Col:
            async def insert_one(self, doc):
                raise DuplicateKeyError("trùng")

        with patch.object(store, "get_db", lambda: {store.COLLECTION: _Col()}), \
             patch.object(store, "tim_yeu_cau_dang_cho", AsyncMock(return_value=cu)):
            ban_ghi, la_moi = await store.create_request(
                {"code": "HT-MOI", "kind": "gap_mat", "session_id": SESSION,
                 "job_order_code": "DH-0001"}
            )
        self.assertEqual(ban_ghi["code"], "HT-CU")
        self.assertFalse(la_moi)

    async def test_trung_nhung_ban_cu_vua_dong_thi_nem_len_chu_khong_tra_None(self):
        """Trả `None` ra ngoài sẽ thành `AttributeError` ở nơi gọi — khó lần hơn nhiều."""
        class _Col:
            async def insert_one(self, doc):
                raise DuplicateKeyError("trùng")

        with patch.object(store, "get_db", lambda: {store.COLLECTION: _Col()}), \
             patch.object(store, "tim_yeu_cau_dang_cho", AsyncMock(return_value=None)):
            with self.assertRaises(DuplicateKeyError):
                await store.create_request(
                    {"code": "HT-MOI", "kind": "gap_mat", "session_id": SESSION,
                     "job_order_code": None}
                )

    async def test_co_index_duy_nhat_cho_yeu_cau_dang_mo(self):
        """Soi tham số THẬT gửi xuống `create_index`, không grep mã nguồn.

        Bản nháp đầu chỉ kiểm `"unique=True" in nguon` — vô dụng, vì chuỗi ấy còn ở
        index của trường `code`. Đổi `unique=True` thành `False` ở đúng index chống
        trùng mà ca vẫn xanh. Phá thử mới lộ ra, và đây là lần thứ hai trong hai
        ngày tôi mắc đúng kiểu ca kiểm thử này.
        """
        goi = []

        class _Col:
            async def create_index(self, keys, **tuy_chon):
                goi.append((keys, tuy_chon))

        await store.ensure_indexes({store.COLLECTION: _Col()})
        chong_trung = [
            (k, o)
            for k, o in goi
            if o.get("name") == "mot_yeu_cau_dang_mo_moi_loai_moi_don"
        ]
        self.assertEqual(len(chong_trung), 1, "không thấy index chống trùng")
        keys, tuy_chon = chong_trung[0]
        self.assertTrue(tuy_chon.get("unique"), "index chống trùng phải là `unique`")
        self.assertEqual(
            tuy_chon.get("partialFilterExpression"), {"dang_mo": {"$eq": True}}
        )
        self.assertEqual(
            [ten for ten, _ in keys],
            ["session_id", "kind", "job_order_code"],
        )

    def test_partial_index_khong_dung_in_vi_mongo_khong_nhan(self):
        """`partialFilterExpression` chỉ nhận `$eq`, `$exists` và vài toán tử so sánh.

        Dùng `$in` thì MongoDB từ chối tạo index — và nếu ai bắt lỗi rồi bỏ qua,
        chống trùng biến mất trong im lặng.
        """
        import inspect

        # Tìm ĐÚNG tham số, không tìm chữ trong chú thích: chú thích ngay trên đó
        # có nhắc `$in` để giải thích vì sao không dùng, và bản nháp đầu của ca này
        # đỏ vì chính câu giải thích ấy.
        nguon = inspect.getsource(store.ensure_indexes)
        i = nguon.index("partialFilterExpression=")
        self.assertNotIn("$in", nguon[i : i + 160])

    def test_dong_yeu_cau_thi_XOA_co_dang_mo(self):
        """Đặt `False` thì giá trị vẫn nằm trong index, và khách quay lại bị chặn oan."""
        import inspect

        nguon = inspect.getsource(store.close_request)
        self.assertIn("$unset", nguon)
        self.assertIn("dang_mo", nguon)


class LoiNhanKhongBatBuocOCaHaiTangTests(unittest.TestCase):
    """API cho để trống mà biểu mẫu vẫn `required` thì khách vẫn bị bắt viết.

    Bản rà soát 30/09 bắt đúng chỗ lệch này: tôi sửa máy chủ hôm 30/09 nhưng để sót
    thuộc tính `required` trên `textarea`, nên trên thực tế không gì đổi.
    """

    def test_bieu_mau_khong_bat_buoc_o_noi_dung(self):
        import pathlib
        import re

        nguon = (
            pathlib.Path(__file__).resolve().parents[2]
            / "frontend" / "components" / "candidate" / "SupportRequestForm.tsx"
        ).read_text(encoding="utf-8")
        khoi = re.search(r"<textarea[^>]*name=\"message\"[^>]*>", nguon, re.S)
        if khoi is None:
            khoi = re.search(r"<textarea(?:(?!</).)*?name=\"message\".*?/>", nguon, re.S)
        self.assertIsNotNone(khoi, "không tìm thấy ô nhập nội dung")
        self.assertNotIn(
            "required",
            khoi.group(),
            "ô nội dung còn `required` — máy chủ cho để trống mà khách vẫn bị bắt viết",
        )


if __name__ == "__main__":
    unittest.main()
