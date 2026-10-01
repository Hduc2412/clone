"""Ghi điểm từ sự kiện nghiệp vụ.

Tách khỏi `scoring.py` (bảng quy tắc, thuần) và khỏi `employee_scores.py` (lưu
trữ). Ở giữa là chỗ duy nhất biết cả hai, nên cũng là chỗ duy nhất cần đọc khi
muốn biết "sự kiện này có sinh điểm không, và bao nhiêu".

## Ghi điểm không được làm hỏng việc chính

Mọi hàm ở đây nuốt lỗi và chỉ in log. Nhân viên bấm "nhận xử lý" mà sổ điểm trục
trặc thì việc nhận vẫn phải thành công — điểm số là thứ phụ, hồ sơ ứng viên mới
là việc chính. Cùng lý do với `audit_service`.
"""
from datetime import datetime
from typing import Any

from app.core.codes import PREFIX_SCORE_EVENT, new_code
from app.db import employee_scores as store
from app.services import score_outbox
from app.services import scoring


async def award(
    *,
    staff_email: str | None,
    action: str,
    reference_type: str,
    reference_code: str,
    occurred_at: datetime | None = None,
    note: str | None = None,
) -> dict[str, Any] | None:
    """Ghi điểm cho một sự kiện, nếu sự kiện đó có trong bảng quy tắc."""
    if not staff_email:
        return None
    points = scoring.points_for(action)
    if points is None:
        return None

    ban_ghi = {
        "code": new_code(PREFIX_SCORE_EVENT),
        "staff_email": staff_email.strip().lower(),
        "action": action,
        "points": points,
        "reference_type": reference_type,
        "reference_code": reference_code,
        "occurred_at": occurred_at or store.now(),
        "note": note,
        "source": store.SOURCE_AUTO,
    }
    try:
        return await store.record(ban_ghi)
    except Exception as exc:  # noqa: BLE001 — xem docstring đầu file
        # Database hỏng thì **xếp vào sổ chờ**, không bỏ đi.
        #
        # Bản trước `print` một dòng rồi trả `None`. Trên máy chạy thật dòng ấy
        # trôi mất trong vài phút, và điểm mất hẳn — tổng vẫn ra một con số, chỉ là
        # con số đó không còn khớp với việc đã làm, và không ai có cách nào biết.
        # Người bị thiếu điểm cũng không biết để hỏi; họ đâu có đếm.
        #
        # Việc nghiệp vụ vẫn đi tiếp: một sự cố ghi điểm không được làm hỏng thao
        # tác mà nhân viên vừa làm xong. Xem `app/services/score_outbox.py`.
        score_outbox.ghi_cho(ban_ghi, ly_do=f"{type(exc).__name__}: {exc}")
        return None


async def award_pickup(
    *,
    staff_email: str,
    application_code: str,
    registered_at: datetime | None,
    accepted_at: datetime | None = None,
) -> None:
    """Điểm nhận việc, cộng thêm nếu nhận sớm.

    Hai dòng riêng chứ không gộp thành một dòng điểm cao hơn. Nhân viên mở sổ ra
    phải thấy được **vì sao** hôm nay hơn hôm qua hai điểm, chứ không chỉ thấy
    một con số khác đi.
    """
    moment = accepted_at or store.now()
    await award(
        staff_email=staff_email,
        action="application.accepted",
        reference_type="recruitment_application",
        reference_code=application_code,
        occurred_at=moment,
    )
    if scoring.is_fast_pickup(registered_at, moment):
        await award(
            staff_email=staff_email,
            action="application.accepted_fast",
            reference_type="recruitment_application",
            reference_code=application_code,
            occurred_at=moment,
        )


async def award_appointment_result(
    *,
    staff_email: str | None,
    appointment_code: str,
    status: str,
    note: str | None = None,
) -> None:
    """Điểm cho kết quả gọi. Chỉ hai trạng thái có trong bảng quy tắc."""
    await award(
        staff_email=staff_email,
        action=f"appointment.{status}",
        reference_type="consultation_appointment",
        reference_code=appointment_code,
        note=note,
    )


async def adjust(
    *,
    staff_email: str,
    points: int,
    note: str,
    created_by: str,
) -> dict[str, Any]:
    """Quản lý cộng trừ điểm tay. Luôn là một dòng mới, không sửa dòng cũ."""
    try:
        record = await store.record(
            {
                "code": new_code(PREFIX_SCORE_EVENT),
                "staff_email": staff_email.strip().lower(),
                "action": "manual.adjustment",
                "points": points,
                "reference_type": "manual",
                "reference_code": None,
                "note": note,
                "source": store.SOURCE_MANUAL,
                "created_by": created_by,
            }
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Không ghi được điều chỉnh: {exc}") from exc
    if record is None:
        raise RuntimeError("Không ghi được điều chỉnh.")
    return record
