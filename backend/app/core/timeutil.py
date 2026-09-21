"""Thời gian theo múi giờ Việt Nam.

Hệ thống lưu mốc thời gian dạng UTC, nhưng mọi câu hỏi nghiệp vụ đều theo giờ
Việt Nam: hôm nay là ngày nào, đơn hàng còn hạn không, ứng viên bao nhiêu tuổi,
lịch hẹn có nằm trong giờ làm việc không.

Dùng `datetime.now(UTC).date()` cho những việc đó là sai: từ 0h đến 7h sáng giờ
Việt Nam, UTC vẫn đang ở ngày hôm trước. Một đơn hàng hết hạn hôm qua sẽ vẫn
được coi là còn hạn. Gom về đây để mọi module dùng chung một định nghĩa.
"""
from datetime import UTC, date, datetime, timedelta, timezone


# Giờ Việt Nam, trùng với `booking_service` đang dùng cho lịch hẹn.
LOCAL_TIMEZONE = timezone(timedelta(hours=7))


def local_now() -> datetime:
    """Thời điểm hiện tại theo giờ Việt Nam."""
    return datetime.now(LOCAL_TIMEZONE)


def local_today() -> date:
    """Ngày hôm nay theo giờ Việt Nam."""
    return local_now().date()


def local_today_iso() -> str:
    """Hôm nay dạng `YYYY-MM-DD`, để so sánh với các trường ngày lưu dạng chuỗi."""
    return local_today().isoformat()


def utc_now() -> datetime:
    """Mốc thời gian để ghi vào database."""
    return datetime.now(UTC)


def age_on(birth_year: int | None, as_of: date | None = None) -> int | None:
    """Tuổi tính theo năm sinh.

    Chỉ có năm sinh nên không biết đã qua sinh nhật hay chưa; lấy hiệu số năm là
    quy ước thông dụng khi đối chiếu khoảng tuổi của đơn hàng. Trả `None` khi
    thiếu dữ liệu, vì bộ đối chiếu phải phân biệt "không đạt" với "chưa rõ".
    """
    if not birth_year:
        return None
    reference = as_of or local_today()
    return reference.year - birth_year
