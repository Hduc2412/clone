"""API đối chiếu hồ sơ và nhật ký giới thiệu."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.auth.security import get_current_user, require_roles
from app.core.rate_limit import client_ip, rate_limiter
from app.db import candidate_profiles as profile_store
from app.db import recommendation_logs as log_store
from app.services import matching_service
from app.services.assignment import can_access, is_privileged
from app.services.audit_service import audit_action


public_router = APIRouter(prefix="/public/matches", tags=["Đối chiếu đơn hàng (công khai)"])
router = APIRouter(
    prefix="/recommendation-logs",
    tags=["Nhật ký giới thiệu"],
    dependencies=[Depends(get_current_user)],
)


class RerunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_code: str = Field(min_length=4, max_length=30)


@public_router.get("/{session_id}")
async def matches_for_session(
    session_id: str,
    http_request: Request,
    limit: int = Query(default=matching_service.DEFAULT_TOP_N, ge=1, le=10),
    refresh: bool = False,
):
    """Đơn hàng phù hợp với hồ sơ của phiên này.

    Trả về 409 khi hồ sơ chưa được xác nhận. Đối chiếu trên dữ liệu máy đọc mà
    ứng viên chưa xem lại là cách chắc chắn để giới thiệu sai đơn: máy có thể đọc
    nhầm "N4" thành "N3", và ứng viên sẽ nhận một danh sách không liên quan tới
    mình mà không hiểu vì sao.
    """
    rate_limiter.check(f"matches:{client_ip(http_request)}", limit=20, window_seconds=60)

    profile = await profile_store.get_by_session(session_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Chưa có hồ sơ cho phiên này.")
    if profile.get("status") != profile_store.STATUS_CONFIRMED:
        raise HTTPException(
            status_code=409,
            detail="Hồ sơ chưa được xác nhận. Vui lòng xem lại và xác nhận trước khi đối chiếu.",
        )

    log, from_cache = await matching_service.run_matching(
        profile, trigger="public", force=refresh
    )
    return matching_service.to_public_payload(log, limit=limit) | {"from_cache": from_cache}


@public_router.get("/{session_id}/orders/{code}")
async def match_detail(session_id: str, code: str):
    """Lý do chi tiết cho một đơn, dùng cho ô "vì sao đơn này"."""
    profile = await profile_store.get_by_session(session_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Chưa có hồ sơ cho phiên này.")

    log = await log_store.latest_for_profile(profile["code"])
    if log is None:
        raise HTTPException(status_code=404, detail="Chưa có kết quả đối chiếu.")

    item = next((row for row in log.get("items", []) if row.get("code") == code), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Đơn này không có trong lần đối chiếu gần nhất.")
    return matching_service.public_item(item)


# --- Nhật ký giới thiệu, dành cho nhân viên ---


@router.get("")
async def recommendation_logs_list(
    profile_code: str | None = Query(default=None, max_length=30),
    session_id: str | None = Query(default=None, max_length=64),
    trigger: str | None = Query(default=None, max_length=20),
    date_from: str | None = Query(default=None, max_length=10),
    date_to: str | None = Query(default=None, max_length=10),
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(get_current_user),
):
    assigned_to = None if is_privileged(current_user) else current_user["email"]
    query = log_store.build_query(
        profile_code=profile_code,
        session_id=session_id,
        assigned_to=assigned_to,
        trigger=trigger,
        date_from=date_from,
        date_to=date_to,
    )
    return await log_store.list_logs(query, limit=limit)


@router.get("/{code}")
async def recommendation_log_detail(code: str, current_user=Depends(get_current_user)):
    log = await log_store.get_log(code)
    if log is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi đối chiếu.")
    if not can_access(log, current_user):
        raise HTTPException(status_code=403, detail="Bạn không được xem bản ghi này.")
    return log


@router.post("/rerun")
async def rerun_matching(
    payload: RerunRequest,
    http_request: Request,
    current_user=Depends(get_current_user),
):
    profile = await profile_store.get_by_code(payload.profile_code)
    if profile is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ ứng viên.")
    if not can_access(profile, current_user):
        raise HTTPException(status_code=403, detail="Bạn không được thao tác trên hồ sơ này.")

    log, _ = await matching_service.run_matching(
        profile, trigger="staff_rerun", actor_email=current_user["email"], force=True
    )
    await audit_action(
        http_request,
        "recommendation.rerun",
        actor=current_user,
        target_type="candidate_profile",
        target_id=payload.profile_code,
        details={"log_code": log["code"]},
    )
    return log


@router.get("/profile/{profile_code}/latest")
async def latest_for_profile(profile_code: str, current_user=Depends(get_current_user)):
    profile = await profile_store.get_by_code(profile_code)
    if profile is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ ứng viên.")
    if not can_access(profile, current_user):
        raise HTTPException(status_code=403, detail="Bạn không được xem hồ sơ này.")

    log = await log_store.latest_for_profile(profile_code)
    if log is None:
        raise HTTPException(status_code=404, detail="Hồ sơ này chưa được đối chiếu lần nào.")
    return log
