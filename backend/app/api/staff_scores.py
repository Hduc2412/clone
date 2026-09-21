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
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

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


def _window(
    date_from: str | None,
    date_to: str | None,
) -> tuple[datetime | None, datetime | None]:
    """Đổi ngày dạng chuỗi thành mốc thời gian, báo lỗi rõ nếu viết sai."""
    def parse(value: str | None, end_of_day: bool) -> datetime | None:
        if not value:
            return None
        try:
            day = datetime.fromisoformat(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"Ngày không hợp lệ: {value}"
            ) from exc
        return day.replace(hour=23, minute=59, second=59) if end_of_day else day

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
