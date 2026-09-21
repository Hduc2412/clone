"""Quy tắc tính điểm hiệu suất nhân viên.

**Không có mô hình học máy ở đây, và cũng không nên có.** `docs/design/13 §1.3`
loại bỏ hướng đó với lý do: mô hình học được sẽ không giải trình được, mà điểm số
ảnh hưởng tới thu nhập và đánh giá của người thật. Mỗi điểm ở đây phải trỏ về
đúng một sự kiện có thật, đọc lên là hiểu.

## Ba nguyên tắc nằm ngay trong bảng quy tắc

**Chấm việc đã làm xong, không chấm việc đang giữ.** Nhận nhiều hồ sơ rồi bỏ đó
không sinh ra điểm; gọi được cho khách và ghi kết quả mới sinh. Chấm theo số hồ
sơ đang cầm là dạy nhân viên ôm việc.

**Không trừ điểm khi trả việc về hàng đợi.** Nghe có vẻ nên trừ — nhận rồi không
làm thì phải chịu. Nhưng trừ điểm ở đó là dạy nhân viên **giữ chặt hồ sơ họ không
xử lý nổi**, vì buông ra thì mất điểm. Người chịu thiệt cuối cùng là ứng viên
ngồi chờ. Trả việc vẫn được ghi vào sổ với 0 điểm, để quản lý nhìn thấy, nhưng
không phạt.

**Điểm sửa tay cũng là một dòng trong sổ.** Quản lý cộng trừ điểm thì phải ghi lý
do, và bản ghi đó nằm cùng chỗ với điểm tự động. Không có chỗ nào chứa "một con
số tổng" sửa trực tiếp được — tổng luôn là tổng của các dòng.
"""
from dataclasses import dataclass


# Nhận hồ sơ trong vòng hai giờ kể từ lúc ứng viên đăng ký thì được thưởng thêm.
# Hai giờ là khoảng người đăng ký buổi sáng còn nhận được cuộc gọi trong buổi
# sáng đó — mốc có ý nghĩa với khách, không phải con số cho đẹp.
FAST_PICKUP_HOURS = 2


@dataclass(frozen=True)
class Rule:
    action: str
    points: int
    label: str


# Mỗi sự kiện nghiệp vụ tương ứng tối đa một quy tắc. Sự kiện không có trong bảng
# thì không sinh điểm — im lặng bỏ qua, không phải lỗi.
RULES: dict[str, Rule] = {
    rule.action: rule
    for rule in (
        Rule("application.accepted", 2, "Nhận xử lý hồ sơ đăng ký"),
        Rule("application.accepted_fast", 3, f"Nhận trong {FAST_PICKUP_HOURS} giờ đầu"),
        Rule("appointment.completed", 5, "Gọi được cho khách và ghi kết quả"),
        # Gọi không gặp vẫn được ghi nhận: nhân viên đã bỏ công gọi, và việc ghi
        # lại "không liên lạc được" là thông tin có ích cho người gọi lần sau.
        # Điểm thấp hơn hẳn để không ai đi gọi cho có.
        Rule("appointment.unreachable", 1, "Đã gọi nhưng không liên lạc được"),
        Rule("application.departed", 20, "Ứng viên xuất cảnh"),
        Rule("application.released", 0, "Trả hồ sơ về hàng đợi"),
        Rule("manual.adjustment", 0, "Quản lý điều chỉnh tay"),
    )
}

# Trần và sàn cho một lần sửa tay. Không phải vì sợ quản lý dùng sai, mà vì một
# con số lạc tay (gõ thừa số 0) sẽ làm hỏng bảng xếp hạng của cả tháng.
MANUAL_MIN = -50
MANUAL_MAX = 50


def points_for(action: str) -> int | None:
    """Số điểm của một sự kiện, hoặc `None` nếu sự kiện này không tính điểm."""
    rule = RULES.get(action)
    return rule.points if rule else None


def label_for(action: str) -> str:
    rule = RULES.get(action)
    return rule.label if rule else action


def is_fast_pickup(registered_at, accepted_at) -> bool:
    """Nhận việc có kịp trong khung giờ được thưởng không.

    Thiếu mốc thời gian nào thì trả `False`. Đoán ra một khoảng thời gian không
    có thật rồi cộng điểm cho nó là kiểu sai tệ nhất ở đây.
    """
    if registered_at is None or accepted_at is None:
        return False
    try:
        elapsed = (accepted_at - registered_at).total_seconds()
    except TypeError:
        return False
    return 0 <= elapsed <= FAST_PICKUP_HOURS * 3600
