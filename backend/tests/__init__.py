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
import atexit
import os
import shutil
import tempfile


# Ghi đè, không `setdefault`. Xem docstring ở trên.
KHOA_GIA_CHO_KIEM_THU = "test-gemini-api-key-not-a-real-key"
os.environ["GEMINI_API_KEY"] = KHOA_GIA_CHO_KIEM_THU
os.environ["ADVISOR_API_KEY"] = KHOA_GIA_CHO_KIEM_THU

# Mọi ghi file trong test phải nằm ngoài `backend/storage`. Đặc biệt, khi chạy
# bộ test bên trong container đang gắn volume `/app/storage`, một ca cố ý giả
# lập MongoDB hỏng sẽ ghi điểm giả vào volume thật. Lần khởi động sau app sẽ
# replay chúng như dữ liệu nghiệp vụ. Dùng một thư mục tạm riêng cho toàn lượt
# test và dọn khi Python thoát để test không bao giờ chạm kho runtime.
_THU_MUC_LUU_TRU_KIEM_THU = tempfile.mkdtemp(prefix="xkld-tests-storage-")
os.environ["STORAGE_PATH"] = _THU_MUC_LUU_TRU_KIEM_THU
atexit.register(
    shutil.rmtree,
    _THU_MUC_LUU_TRU_KIEM_THU,
    ignore_errors=True,
)

os.environ.setdefault(
    "JWT_SECRET", "test-secret-that-is-long-enough-for-all-backend-tests"
)


# Mỗi ca bắt đầu với bộ giới hạn tần suất SẠCH.
#
# `rate_limiter` là một đối tượng dùng chung trong tiến trình, và `unittest
# discover` chạy MỌI module trong cùng một tiến trình — nên các ca dùng chung hạn
# mức của nhau, kể cả giữa các file. Ngày 06/10 một ca mới được thêm vào làm một
# ca KHÁC nhận 429: đỏ hay xanh tùy số ca đứng trước nó. Trước đó ba file đã tự
# chống chế mỗi kiểu một cách (xóa đúng khóa mình dùng, hoặc vô hiệu hóa hẳn bộ
# giới hạn). Xóa ở một chỗ, trước mỗi ca, thay cho các mẹo rời rạc ấy.
#
# Chỉ xóa GIỮA các ca. Trong một ca, bộ giới hạn chạy y như thật — nên ca kiểm
# ngưỡng 429 vẫn chạm được ngưỡng.
import unittest as _unittest

_chay_ca_goc = _unittest.TestCase.run


def _chay_ca_voi_bo_gioi_han_sach(self, result=None):
    from app.core.rate_limit import rate_limiter

    rate_limiter.clear()
    return _chay_ca_goc(self, result)


_unittest.TestCase.run = _chay_ca_voi_bo_gioi_han_sach
