"""Ghi bản gốc CV xuống đĩa.

Spec yêu cầu **lưu bản gốc** chứ không chỉ lưu phần đã bóc tách. Lý do nghiệp vụ:
khi nhân viên nghi máy đọc sai một trường, thứ duy nhất phân xử được là chính tờ
CV ứng viên gửi. Bản gốc mất thì đoạn dẫn trong hồ sơ trở thành lời nói suông.

Ba quy tắc:

- **Không bao giờ ghi đè.** Tên file lấy theo mã `CV-xxxxxx` sinh ngẫu nhiên, và
  vẫn mở bằng cờ `x` để nếu mã có trùng thì lỗi nổ ra chứ không âm thầm đè mất
  file của người khác.
- **Không dùng tên file người dùng đặt làm đường dẫn.** Tên gốc chỉ được lưu như
  một trường dữ liệu để hiển thị. Lấy nó làm tên file thật là mở đường cho
  `../../` đi ra ngoài thư mục lưu trữ.
- **Chia thư mục theo ngày.** Một thư mục phẳng chứa hàng chục nghìn file làm mọi
  thao tác quản trị trên máy chủ chậm đi thấy rõ.
"""
import hashlib
from pathlib import Path

from app.core.config import settings
from app.core.timeutil import local_today


def digest(data: bytes) -> str:
    """Vân tay nội dung, dùng để nhận ra ứng viên gửi lại đúng file cũ."""
    return hashlib.sha256(data).hexdigest()


def relative_path(code: str, extension: str) -> str:
    """Đường dẫn tương đối tính từ thư mục lưu trữ CV.

    Lưu tương đối để khi đổi chỗ thư mục lưu trữ (đổi máy, gắn ổ khác) thì đường
    dẫn trong database không thành vô nghĩa.
    """
    return f"{local_today():%Y/%m}/{code}{extension}"


def save(data: bytes, code: str, extension: str) -> str:
    path = settings.cv_storage_path / relative_path(code, extension)
    path.parent.mkdir(parents=True, exist_ok=True)
    # "xb" = tạo mới, lỗi nếu đã tồn tại.
    with open(path, "xb") as handle:
        handle.write(data)
    return relative_path(code, extension)


def absolute_path(stored_path: str) -> Path:
    return settings.cv_storage_path / stored_path


def load(stored_path: str) -> bytes:
    return absolute_path(stored_path).read_bytes()
