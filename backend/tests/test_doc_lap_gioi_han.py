"""Mỗi ca kiểm thử bắt đầu với bộ giới hạn tần suất sạch — xem `tests/__init__.py`.

Hai ca chạy theo thứ tự tên (`unittest` sắp theo tên phương thức): ca `a` dùng hết
hạn mức của một khóa, ca `b` phải dùng lại được đúng khóa ấy. Không có bước xóa
giữa hai ca thì ca `b` nhận 429.
"""
import unittest

from fastapi import HTTPException

from app.core.rate_limit import rate_limiter

KHOA = "kiem-doc-lap:10.0.0.1"


class DocLapGiuaCacCaTests(unittest.TestCase):
    def test_a_ca_truoc_dung_het_han_muc(self):
        for _ in range(3):
            rate_limiter.check(KHOA, limit=3, window_seconds=600)
        with self.assertRaises(HTTPException) as ra:
            rate_limiter.check(KHOA, limit=3, window_seconds=600)
        self.assertEqual(ra.exception.status_code, 429, "trong MỘT ca, bộ giới hạn phải chạy như thật")

    def test_b_ca_sau_khong_mang_han_muc_cua_ca_truoc(self):
        rate_limiter.check(KHOA, limit=3, window_seconds=600)


class DocLapCaBatDongBoTests(unittest.IsolatedAsyncioTestCase):
    """`IsolatedAsyncioTestCase` có `run` riêng — vẫn phải đi qua bước xóa."""

    async def test_a_dung_het(self):
        for _ in range(2):
            rate_limiter.check(KHOA + ":async", limit=2, window_seconds=600)

    async def test_b_van_dung_lai_duoc(self):
        rate_limiter.check(KHOA + ":async", limit=2, window_seconds=600)
