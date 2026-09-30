"""Giá trị môi trường cho kiểm thử — và một chốt chặn: **bộ này không gọi mạng**.

`app.core.config` kiểm tra cấu hình ngay lúc import và sẽ báo lỗi nếu thiếu khóa
Gemini hoặc khóa ký JWT. Đặt sẵn ở đây để bộ kiểm thử chạy được trên máy chưa có
file `.env` — máy CI, máy vừa clone repo.

## Vì sao KHÓA API bị ghi đè, không phải `setdefault`

Bản trước dùng `setdefault` cho mọi biến, với lý do "khi `.env` có thật thì giá trị
trong đó được ưu tiên, nên bản mặc định không che mất cấu hình thật". Nghe hợp lý,
nhưng với một bộ kiểm thử thì đó là lỗi: nó có nghĩa là **trên máy có `.env` thật,
test chạy với khóa thật và gọi được API thật**.

Bản rà soát 30/09 bắt được hệ quả qua nhật ký lần chạy. Ca
`test_thieu_khoa_api_thi_tra_none` xóa `advisor_api_key` rồi khẳng định không gọi
mô hình — nhưng `client.api_key()` có đường rơi về `gemini_api_key`, và khóa ấy có
thật, nên ca đó **gửi một request thật** rồi đi tới `None` vì Google từ chối. Nó
xanh, nhưng xanh vì một lý do khác hẳn thứ nó nói mình đang kiểm.

Hậu quả rộng hơn một ca kiểm thử:

- bộ test không chạy được khi mất mạng, dù nó tự nhận là không cần mạng;
- mỗi lượt chạy ngốn hạn mức của gói miễn phí — 20 lượt mỗi ngày, và chúng dùng
  chung với phần đo chất lượng thật;
- và tệ nhất: một ca **đỏ vì hết hạn mức** trông y như một ca đỏ vì mã sai.

Nên hai khóa API bị ghi đè vô điều kiện. Không ca nào trong `tests/` cần khóa thật:
việc đo mô hình thật nằm ở `scripts/nghiem_thu_*.py`, chạy tay, và những script ấy
đọc `.env` như bình thường.

`JWT_SECRET` vẫn `setdefault` — nó không đi ra mạng, và giữ giá trị thật giúp phần
nào đó chạy gần hơn với bản thật.
"""
import os


# Ghi đè, không `setdefault`. Xem docstring ở trên.
KHOA_GIA_CHO_KIEM_THU = "test-gemini-api-key-not-a-real-key"
os.environ["GEMINI_API_KEY"] = KHOA_GIA_CHO_KIEM_THU
os.environ["ADVISOR_API_KEY"] = KHOA_GIA_CHO_KIEM_THU

os.environ.setdefault(
    "JWT_SECRET", "test-secret-that-is-long-enough-for-all-backend-tests"
)
