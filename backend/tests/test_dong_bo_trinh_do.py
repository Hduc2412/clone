"""Trình độ ở hồ sơ tuyển dụng đi theo hồ sơ năng lực (12/10).

`recruitment_applications.japanese_level` là bản chụp lúc đăng ký. Trước 12/10 buổi
sơ tuyển chốt trình độ mới vào hồ sơ năng lực mà hàng đợi vẫn hiện trình độ ngày
đăng ký. Nay mọi lần ghi hồ sơ đổi trình độ đều cập nhật hồ sơ tuyển dụng ĐANG MỞ.
"""
import unittest
from unittest.mock import AsyncMock, patch

from app.db import candidate_profiles as store


def ho_so(muc, code="UV-1"):
    return {"code": code, "fields": {"japanese_level": store.cell(muc, "staff")} if muc else {}}


class DongBoTrinhDoTests(unittest.IsolatedAsyncioTestCase):
    async def _ghi(self, truoc, sau, *, loi=None):
        profiles = AsyncMock()
        profiles.find_one_and_update.return_value = sau
        apps = AsyncMock()
        if loi:
            apps.update_many.side_effect = loi
        db = {store.COLLECTION: profiles, store.HO_SO_TUYEN_DUNG: apps}
        with patch.object(store, "get_db", return_value=db):
            ra = await store.apply_changes(
                "s" * 32, expected_version=1, fields=sau.get("fields") if sau else {},
                preferences={}, history=truoc,
            )
        return ra, apps

    async def test_doi_trinh_do_thi_cap_nhat_ho_so_tuyen_dung_dang_mo(self):
        ra, apps = await self._ghi(ho_so("N4"), ho_so("N3"))
        self.assertEqual(ra["code"], "UV-1")
        apps.update_many.assert_awaited_once()
        loc, lenh = apps.update_many.await_args.args
        self.assertEqual(loc, {"profile_code": "UV-1", "is_active": True})
        self.assertEqual(lenh["$set"]["japanese_level"], "N3")

    async def test_ghi_nhan_tieng_viet_nhu_luc_dang_ky(self):
        _, apps = await self._ghi(ho_so("N5"), ho_so("chua_hoc"))
        self.assertEqual(apps.update_many.await_args.args[1]["$set"]["japanese_level"], "Chưa học")

    async def test_trinh_do_khong_doi_thi_khong_cham_ho_so_tuyen_dung(self):
        _, apps = await self._ghi(ho_so("N4"), ho_so("N4"))
        apps.update_many.assert_not_awaited()

    async def test_ghi_that_bai_vi_lech_phien_ban_thi_khong_dong_bo(self):
        profiles = AsyncMock()
        profiles.find_one_and_update.return_value = None
        apps = AsyncMock()
        with patch.object(store, "get_db", return_value={store.COLLECTION: profiles, store.HO_SO_TUYEN_DUNG: apps}):
            ra = await store.apply_changes("s" * 32, expected_version=1, fields=ho_so("N3")["fields"],
                                           preferences={}, history=ho_so("N4"))
        self.assertIsNone(ra)
        apps.update_many.assert_not_awaited()

    async def test_chi_ghi_phan_khac_fields_thi_khong_dong_bo(self):
        """Ghi tiến độ học, nguyện vọng… truyền `fields=None` — trình độ không đổi."""
        profiles = AsyncMock()
        profiles.find_one_and_update.return_value = ho_so("N3")
        apps = AsyncMock()
        with patch.object(store, "get_db", return_value={store.COLLECTION: profiles, store.HO_SO_TUYEN_DUNG: apps}):
            await store.apply_changes("s" * 32, expected_version=1, fields=None,
                                      preferences={}, history=ho_so("N4"))
        apps.update_many.assert_not_awaited()

    async def test_dong_bo_loi_khong_lam_hong_lan_luu_ho_so(self):
        with self.assertLogs(store.logger, level="ERROR"):
            ra, _ = await self._ghi(ho_so("N4"), ho_so("N3"), loi=RuntimeError("mất kết nối"))
        self.assertEqual(ra["code"], "UV-1")


if __name__ == "__main__":
    unittest.main()
