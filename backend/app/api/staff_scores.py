"""API sổ điểm nhân viên.

## Ai xem được của ai

Tư vấn viên xem được sổ của chính mình, không xem được của người khác. Đây không
phải bí mật kỹ thuật mà là chuyện quản lý con người: bảng xếp hạng công khai giữa
các đồng nghiệp tạo áp lực không ai yêu cầu, và dễ biến thành chuyện cá nhân.
Quản lý cần bức tranh toàn đội thì có quyền xem hết.

## Sửa tay bắt buộc ghi lý do

Một dòng điểm không có lý do, ba tháng sau đọc lại thì không ai biết vì sao. Mà
lúc đó thường là lúc cần biết nhất — khi có người thắc mắc.
"""
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.timeutil import LOCAL_TIMEZONE
from app.auth.security import get_current_user, require_roles
from app.db import employee_scores as store
from app.db.database import get_staff_user_by_email
from app.services import score_service, scoring
from app.services.assignment import is_privileged
from app.services.audit_service import audit_action


router = APIRouter(
    prefix="/staff-scores",
    tags=["Điểm hiệu suất nhân viên"],
    dependencies=[Depends(get_current_user)],
)


class AdjustRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    points: int = Field(ge=scoring.MANUAL_MIN, le=scoring.MANUAL_MAX)
    note: str = Field(min_length=5, max_length=500)

    @field_validator("note")
    @classmethod
    def _ly_do_phai_co_chu(cls, value: str) -> str:
        """Lý do phải có chữ, không phải chỉ có dấu cách.

        `min_length=5` đếm ký tự, nên năm dấu cách lọt qua. Điểm trừ tay là thứ
        duy nhất trong sổ điểm làm giảm điểm của một người, và quy tắc đặt ra là
        **trừ điểm luôn phải có lý do trong nhật ký** — một dòng toàn khoảng trắng
        thì nhật ký vẫn đủ dòng mà người bị trừ không biết vì sao.

        Trả về bản đã cắt khoảng trắng hai đầu: lưu `"  đi muộn  "` rồi hiển thị
        thụt lề là một thứ không ai cố ý tạo ra.
        """
        sach = value.strip()
        if len(sach) < 5:
            raise ValueError(
                "lý do phải có ít nhất 5 ký tự thật, không tính khoảng trắng"
            )
        return sach


def _window(
    date_from: str | None,
    date_to: str | None,
) -> tuple[datetime | None, datetime | None]:
    """Đổi ngày dạng chuỗi thành mốc UTC, hiểu ngày theo **giờ Việt Nam**.

    ## Vì sao phải quy đổi múi giờ

    Người lọc gõ "01/10" nghĩa là ngày mùng một **theo giờ của họ**. Mốc ghi trong
    database thì luôn là UTC (`db/common.now()`).

    Bản trước dựng `datetime` **không mang múi giờ** rồi đem so thẳng — pymongo coi
    chuỗi ấy là UTC, nên cửa sổ lệch đúng bảy tiếng. Hậu quả rất cụ thể: mọi việc
    nhân viên làm **sau 17h giờ Việt Nam** rơi sang ô điểm của ngày hôm sau, còn
    xem đúng ngày hôm đó thì thiếu. Người gọi điện cho ứng viên lúc 8 giờ tối thấy
    bảng điểm hôm nay trống, và hôm sau tự dưng có thêm điểm không rõ từ đâu.

    Nay dựng mốc theo `LOCAL_TIMEZONE` rồi đổi sang UTC: đầu ngày là 00:00:00 giờ
    Việt Nam, cuối ngày là 23:59:59.999999 giờ Việt Nam.

    Chấp nhận cả `2026-10-01` lẫn `2026-10-01T09:30`. Chuỗi đã mang sẵn múi giờ thì
    giữ nguyên múi giờ ấy — người gửi đã nói rõ ý mình.
    """
    def parse(value: str | None, end_of_day: bool) -> datetime | None:
        if not value:
            return None
        try:
            day = datetime.fromisoformat(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"Ngày không hợp lệ: {value}"
            ) from exc
        if end_of_day:
            # `microsecond` cũng phải lấp đầy: một sự kiện lúc 23:59:59.4 vẫn
            # thuộc ngày hôm đó, mà `<=` với 23:59:59.0 thì loại nó ra.
            day = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        if day.tzinfo is None:
            day = day.replace(tzinfo=LOCAL_TIMEZONE)
        return day.astimezone(UTC)

    return parse(date_from, False), parse(date_to, True)


def _decorate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Gắn nhãn tiếng Việt cho từng loại việc, để giao diện không giữ bảng riêng."""
    return [{**row, "label": scoring.label_for(row.get("action", ""))} for row in rows]


@router.get("")
async def scoreboard(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Tổng điểm toàn đội. Tư vấn viên chỉ thấy dòng của chính mình."""
    start, end = _window(date_from, date_to)
    query = store.build_query(date_from=start, date_to=end)
    if not is_privileged(current_user):
        query = store.build_query(
            staff_email=current_user["email"], date_from=start, date_to=end
        )
    return {"items": await store.totals(query), "rules": _rule_table()}


@router.get("/{email}")
async def staff_ledger(
    email: str,
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Từng dòng điểm của một nhân viên, kèm phần tách theo loại việc."""
    normalized = email.strip().lower()
    if not is_privileged(current_user) and normalized != current_user["email"]:
        raise HTTPException(status_code=403, detail="Bạn chỉ xem được sổ điểm của mình.")

    start, end = _window(date_from, date_to)
    query = store.build_query(staff_email=normalized, date_from=start, date_to=end)
    totals = await store.totals(query)
    return {
        "staff_email": normalized,
        "points": totals[0]["points"] if totals else 0,
        "events": _decorate(await store.list_events(query, limit=limit)),
        "breakdown": _decorate(await store.breakdown(query)),
    }


@router.post("/{email}/adjust", status_code=201)
async def adjust(
    email: str,
    payload: AdjustRequest,
    http_request: Request,
    current_user=Depends(require_roles("admin", "manager")),
) -> dict[str, Any]:
    """Cộng hoặc trừ điểm tay. Ghi thành một dòng mới, không sửa dòng cũ."""
    normalized = email.strip().lower()
    staff = await get_staff_user_by_email(normalized)
    if staff is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhân viên.")

    try:
        record = await score_service.adjust(
            staff_email=normalized,
            points=payload.points,
            note=payload.note,
            created_by=current_user["email"],
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    await audit_action(
        http_request,
        "staff_score.adjusted",
        actor=current_user,
        target_type="staff_user",
        target_id=normalized,
        details={"points": payload.points, "note": payload.note},
    )
    return record


def _rule_table() -> list[dict[str, Any]]:
    """Bảng quy tắc phát ra cho giao diện hiển thị.

    Nhân viên phải đọc được luật tính điểm áp lên mình, ngay cạnh điểm của mình.
    Giấu luật đi thì điểm số thành một con số trời cho.
    """
    return [
        {"action": rule.action, "points": rule.points, "label": rule.label}
        for rule in scoring.RULES.values()
        if rule.action != "manual.adjustment"
    ]
