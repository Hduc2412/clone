"""Mã phiên ẩn danh chính là mật khẩu của hồ sơ công khai.

Luồng `/public/*` không có đăng nhập: ai cầm mã phiên là đọc được hồ sơ, danh
sách đơn đã giới thiệu và các tệp CV đã gửi. Cho nên độ dài tối thiểu của mã
phiên không phải chuyện hình thức mà là chiều dài của chính cái khóa ấy.

Ràng buộc cũ cho phép từ tám ký tự. Giao diện không bao giờ gửi chuỗi ngắn như
vậy — nó luôn dùng `crypto.randomUUID()` — nhưng giao diện không phải là hàng
rào: đường công khai ai gọi thẳng cũng được.
"""
import re
import unittest

from app.core.session_id import SESSION_PATTERN


class SessionPatternTests(unittest.TestCase):
    def _hop_le(self, value: str) -> bool:
        return re.match(SESSION_PATTERN, value) is not None

    def test_uuid_co_dau_gach_ngang_duoc_nhan(self):
        self.assertTrue(self._hop_le("3f2a9c41-7d18-4b6e-9a05-2c8e1d47b930"))

    def test_uuid_viet_lien_duoc_nhan(self):
        self.assertTrue(self._hop_le("3f2a9c417d184b6e9a052c8e1d47b930"))

    def test_chuoi_tam_ky_tu_bi_tu_choi(self):
        """Đúng chuỗi mà ràng buộc cũ vẫn nhận — và dò hết chỉ là chuyện thời gian."""
        self.assertFalse(self._hop_le("12345678"))

    def test_chuoi_de_doan_dai_vua_phai_bi_tu_choi(self):
        for value in ("phien-ung-vien-0001", "user-1", "abcdefghijklmnop"):
            with self.subTest(value=value):
                self.assertFalse(self._hop_le(value))

    def test_chuoi_dai_qua_bi_tu_choi(self):
        self.assertFalse(self._hop_le("a" * 65))

    def test_ky_tu_la_bi_tu_choi(self):
        for value in ("../../etc/passwd" + "a" * 20, "a" * 31 + "/", "a" * 31 + " "):
            with self.subTest(value=value):
                self.assertFalse(self._hop_le(value))


if __name__ == "__main__":
    unittest.main()
