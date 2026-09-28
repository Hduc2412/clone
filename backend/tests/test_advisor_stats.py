"""Số liệu độ tin được của bot — thứ trả lời câu "làm sao biết nó không bịa".

Mỗi lượt `khong_biet` là một lần bot chịu dừng lại thay vì nói bừa. Đếm được
chúng nghĩa là có con số thật để đưa ra, không phải một lời hứa trong tài liệu.
"""
import unittest
from unittest.mock import AsyncMock, patch

from app.api import consultation_room
from app.db import advisor_turns, session_memory


STAFF = {"email": "tu.van@example.com", "full_name": "Tư vấn", "role": "consultant"}


class ThongKeTests(unittest.IsolatedAsyncioTestCase):
    async def _goi(self, so_lieu):
        trong = AsyncMock(return_value={"theo_chu_de": [], "so_phien_co_bo_nho": 0})
        with patch.object(advisor_turns, "thong_ke", AsyncMock(return_value=so_lieu)),              patch.object(session_memory, "thong_ke", trong):
            return await consultation_room.thong_ke_bot(so_ngay=30, current_user=STAFF)

    async def test_tra_ve_du_cac_con_so(self):
        ra = await self._goi({
            "tong_luot": 40, "mo_hinh_tra_loi": 31, "bot_khong_doan": 9,
            "ty_le_khong_doan": 22.5, "so_phien": 7, "so_don_da_hoi": 4,
        })
        self.assertEqual(ra["so_ngay"], 30)
        self.assertEqual(ra["bot_khong_doan"], 9)
        self.assertEqual(ra["ty_le_khong_doan"], 22.5)

    async def test_chua_co_luot_nao_thi_ty_le_la_none_chu_khong_phai_khong(self):
        """Chưa ai dùng khác hẳn với dùng rồi mà bot chưa từ chối lần nào.

        Ghi 0% cho cả hai là xoá mất phân biệt ấy, và người đọc số liệu sẽ tưởng
        chốt chặn chưa bao giờ phải làm việc.
        """
        ra = await self._goi({
            "tong_luot": 0, "mo_hinh_tra_loi": 0, "bot_khong_doan": 0,
            "ty_le_khong_doan": None, "so_phien": 0, "so_don_da_hoi": 0,
        })
        self.assertIsNone(ra["ty_le_khong_doan"])


class TinhTyLeTests(unittest.TestCase):
    def test_lam_tron_mot_chu_so_thap_phan(self):
        """Ghi thêm chữ số nữa là gợi ý một độ chính xác mà cỡ mẫu này chưa có."""
        self.assertEqual(round(9 * 100 / 40, 1), 22.5)
        self.assertEqual(round(1 * 100 / 3, 1), 33.3)


if __name__ == "__main__":
    unittest.main()
