"""Sinh mã nghiệp vụ hiển thị cho người dùng.

Mã dạng `HS-A1B2C3` được dùng thay cho ObjectId ở mọi đường dẫn API và trên giao
diện, vì nhân viên phải đọc và trao đổi mã này qua điện thoại. Dùng `secrets`
thay vì `random` để mã không đoán được — một số endpoint công khai định danh bản
ghi chỉ bằng mã.
"""
import secrets


# Tiền tố đang dùng trong hệ thống, gom về một chỗ để tra cứu nhanh khi đọc log.
PREFIX_APPLICATION = "HS"      # hồ sơ đăng ký
PREFIX_DOCUMENT = "CV"         # file hồ sơ ứng viên tải lên
PREFIX_PROFILE = "UV"          # hồ sơ năng lực đã bóc tách
PREFIX_REPORT = "PT"           # phiếu tóm tắt tư vấn
PREFIX_RECOMMENDATION = "RL"   # nhật ký giới thiệu
PREFIX_SCORE_EVENT = "SE"      # sự kiện điểm nhân viên
PREFIX_ASSIGNMENT = "AS"       # lượt phân công
PREFIX_LEAD = "LD"             # khách hàng
PREFIX_RESET = "YC"            # yêu cầu đặt lại mật khẩu


def new_code(prefix: str, nbytes: int = 3) -> str:
    """Sinh mã ngẫu nhiên dạng `<prefix>-<HEX>`.

    `nbytes=3` cho 6 ký tự hex, tức khoảng 16,7 triệu tổ hợp. Đủ thưa cho quy mô
    một doanh nghiệp phái cử, và mọi collection đều có unique index nên trùng mã
    sẽ bị chặn ở tầng database chứ không ghi đè dữ liệu.
    """
    return f"{prefix}-{secrets.token_hex(nbytes).upper()}"
