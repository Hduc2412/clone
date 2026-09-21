"""Giá trị môi trường mặc định cho kiểm thử.

`app.core.config` kiểm tra cấu hình ngay lúc import và sẽ báo lỗi nếu thiếu khóa
Gemini hoặc khóa ký JWT. Đặt sẵn ở đây để bộ kiểm thử chạy được trên máy chưa có
file `.env` (máy CI, máy vừa clone repo). Khi `.env` có thật thì các giá trị
trong đó được ưu tiên, nên bản mặc định này không che mất cấu hình thật.
"""
import os


os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key-not-a-real-key")
os.environ.setdefault(
    "JWT_SECRET", "test-secret-that-is-long-enough-for-all-backend-tests"
)
