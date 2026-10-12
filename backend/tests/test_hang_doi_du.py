"""Hàng đợi không được cắt im lặng.

Đo ngày 06/10: 72 hồ sơ đăng ký đang chờ, màn hình hiện 50 — giới hạn mặc định của
`/registrations/queue` — và không có gì cho biết còn 22 người. Hàng đợi xếp người
chờ lâu nhất lên đầu, nên 22 người bị giấu là những người **vừa** đăng ký.
"""
import inspect
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api import registrations as api_dk
from app.api import support as api_ht
from app.db import database
from app.db import support_requests as store_ht

NHAN_VIEN = {"email": "a@local.test", "full_name": "A", "role": "consultant"}


def _mac_dinh(ham, ten="limit") -> int:
    return inspect.signature(ham).parameters[ten].default.default


class HangDoiDangKyTests(unittest.IsolatedAsyncioTestCase):
    def test_gioi_han_mac_dinh_du_cho_ca_hang_luc_do(self):
        self.assertGreaterEqual(_mac_dinh(api_dk.queue), 72)

    async def test_bi_cat_thi_tra_tong_that(self):
        with patch.object(
            api_dk, "list_unassigned_registrations", AsyncMock(return_value=[{}] * 50)
        ), patch.object(api_dk, "count_unassigned_registrations", AsyncMock(return_value=72)):
            ra = await api_dk.queue(limit=50, current_user=NHAN_VIEN)
        self.assertEqual((ra["count"], ra["total"]), (50, 72))

    async def test_dem_cung_dieu_kien_voi_danh_sach(self):
        """Đếm một đằng, liệt kê một nẻo thì con số "còn N người" lại sai theo kiểu khác."""
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.to_list = AsyncMock(return_value=[])
        db = MagicMock()
        db.recruitment_applications.find.return_value = cursor
        db.recruitment_applications.count_documents = AsyncMock(return_value=0)
        with patch.object(database, "get_db", return_value=db):
            await database.list_unassigned_registrations(limit=10)
            await database.count_unassigned_registrations()
        self.assertEqual(
            db.recruitment_applications.find.call_args.args[0],
            db.recruitment_applications.count_documents.await_args.args[0],
        )


class HangDoiHoTroTests(unittest.IsolatedAsyncioTestCase):
    def test_gioi_han_mac_dinh_du_cho_ca_hang_luc_do(self):
        self.assertGreaterEqual(_mac_dinh(api_ht.hang_doi), 72)

    async def test_bi_cat_thi_tra_tong_that(self):
        with patch.object(
            api_ht.store, "list_requests", AsyncMock(return_value=[{}] * 100)
        ), patch.object(api_ht.store, "count_requests", AsyncMock(return_value=130)) as dem:
            ra = await api_ht.hang_doi(status="cho_xu_ly", kind="gap_mat", limit=100, current_user=NHAN_VIEN)
        self.assertEqual((ra["count"], ra["total"]), (100, 130))
        self.assertEqual(dem.await_args.kwargs, {"status": "cho_xu_ly", "kind": "gap_mat"})

    async def test_dem_cung_bo_loc_voi_danh_sach(self):
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.limit.return_value = cursor

        async def _rong():
            return
            yield  # noqa: unreachable — biến hàm thành async generator rỗng

        cursor.__aiter__ = lambda self: _rong()
        bang = MagicMock()
        bang.find.return_value = cursor
        bang.count_documents = AsyncMock(return_value=0)
        db = MagicMock()
        db.__getitem__.return_value = bang
        with patch.object(store_ht, "get_db", return_value=db):
            await store_ht.list_requests(status="cho_xu_ly", kind="hoc_tap", limit=5)
            await store_ht.count_requests(status="cho_xu_ly", kind="hoc_tap")
        self.assertEqual(bang.find.call_args.args[0], bang.count_documents.await_args.args[0])


if __name__ == "__main__":
    unittest.main()
