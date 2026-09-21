"""API đăng ký sơ bộ và hàng đợi nhân viên.

Router công khai cho ứng viên tự đăng ký; router nội bộ cho nhân viên nhìn hàng
đợi, nhận việc và đọc phiếu tóm tắt.

## Ứng viên không nhìn thấy phiếu

Đăng ký xong, ứng viên chỉ nhận lại một câu xác nhận và mã hồ sơ. Phiếu tóm tắt
là tài liệu nội bộ: trong đó có phần "điểm còn thiếu" và "thông tin chưa rõ" —
những câu viết để nhân viên chuẩn bị trước khi gọi, không phải để ứng viên đọc.

## Nhận việc là thao tác có tranh chấp

Hai nhân viên cùng bấm nhận một hồ sơ trong cùng một giây là chuyện sẽ xảy ra khi
hàng đợi vừa có việc mới. Điều kiện `assigned_to: None` nằm ngay trong câu truy
vấn cập nhật, nên người thứ hai nhận lại `None` và được báo là đã có người nhận —
thay vì cả hai cùng tưởng mình đang phụ trách rồi gọi cho ứng viên hai lần.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.auth.security import get_current_user
from app.core.rate_limit import client_ip, rate_limiter
from app.db import candidate_accounts
from app.db import consultation_reports as reports
from app.db.database import (
    REFERENCE_APPLICATION,
    create_application_event,
    create_notification,
    get_recruitment_application,
    list_recruitment_applications,
    list_unassigned_registrations,
    update_recruitment_application,
)
from app.services import registration_service, score_service
from app.services.assignment import (
    can_access,
    ensure_can_assign,
    validate_assignee,
)
from app.services.audit_service import audit_action


public_router = APIRouter(prefix="/public/registrations", tags=["Đăng ký sơ bộ (công khai)"])
router = APIRouter(
    prefix="/registrations",
    tags=["Đăng ký sơ bộ"],
    dependencies=[Depends(get_current_user)],
)

SESSION_PATTERN = r"^[A-Za-z0-9_-]{8,64}$"


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_order_code: str = Field(min_length=3, max_length=30)
    # Ứng viên phải bấm đồng ý, không mặc định là đồng ý. Đây là chỗ biến "ứng
    # viên tự chọn" thành một hành động có thật chứ không phải suy đoán.
    confirmed: bool = Field(description="Ứng viên xác nhận muốn đăng ký đơn này.")


class HandoverRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assigned_to: str = Field(min_length=3, max_length=150)
    # Bắt buộc ghi lý do. Chuyển việc mà không nói vì sao thì người nhận phải đi
    # hỏi lại từ đầu, và sáu tháng sau không ai dựng lại được chuyện đã xảy ra.
    note: str = Field(min_length=3, max_length=500)


class ReleaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str = Field(min_length=3, max_length=500)


def _session(session_id: str = Path(pattern=SESSION_PATTERN)) -> str:
    return session_id


@public_router.post("/{session_id}", status_code=201)
async def register(
    payload: RegisterRequest,
    http_request: Request,
    session_id: str = Depends(_session),
) -> dict[str, Any]:
    rate_limiter.check(f"registration:{client_ip(http_request)}", limit=5, window_seconds=300)

    if not payload.confirmed:
        raise HTTPException(
            status_code=400,
            detail="Bạn cần xác nhận muốn đăng ký đơn này.",
        )

    try:
        created = await registration_service.register(
            session_id=session_id, job_order_code=payload.job_order_code
        )
    except registration_service.AlreadyRegistered as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except registration_service.RegistrationRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    application = created["application"]
    return {
        "message": (
            "Mình đã ghi nhận đăng ký của bạn. Nhân viên tư vấn sẽ liên hệ "
            "trong giờ làm việc để trao đổi các bước tiếp theo nhé."
        ),
        "application_code": application["application_code"],
        "job_order_code": application["job_order_code"],
        "job_order_title": application.get("job_order_title"),
        "status": application["status"],
    }


@public_router.get("/{session_id}")
async def my_registrations(session_id: str = Depends(_session)) -> dict[str, Any]:
    """Ứng viên xem lại mình đã đăng ký đơn nào."""
    items = await list_unassigned_registrations(session_id=session_id, include_assigned=True)
    return {
        "items": [
            {
                "application_code": item["application_code"],
                "job_order_code": item.get("job_order_code"),
                "job_order_title": item.get("job_order_title"),
                "status": item["status"],
                "created_at": item["created_at"],
            }
            for item in items
        ]
    }


@router.get("/queue")
async def queue(
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Hồ sơ ứng viên tự đăng ký mà chưa ai nhận.

    Không lọc theo người phụ trách: đây đúng là phần việc **chưa của ai**, nên
    mọi nhân viên đều phải nhìn thấy thì mới có người nhận.
    """
    items = await list_unassigned_registrations(limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/{application_code}/accept")
async def accept(
    application_code: str,
    http_request: Request,
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Nhận xử lý một hồ sơ trong hàng đợi."""
    existing = await _load(application_code)
    if existing.get("assigned_to"):
        raise HTTPException(
            status_code=409,
            detail=f"Hồ sơ đã được {existing['assigned_to']} nhận xử lý.",
        )

    updated = await update_recruitment_application(
        application_code,
        {"assigned_to": current_user["email"]},
        expected_status=existing["status"],
        unassigned_only=True,
    )
    if updated is None:
        raise HTTPException(
            status_code=409,
            detail="Hồ sơ vừa được người khác nhận. Bạn tải lại hàng đợi nhé.",
        )

    await _log(application_code, "accepted", current_user, {})
    await score_service.award_pickup(
        staff_email=current_user["email"],
        application_code=application_code,
        registered_at=existing.get("created_at"),
    )
    await audit_action(
        http_request,
        "application.accepted",
        actor=current_user,
        target_type="recruitment_application",
        target_id=application_code,
    )
    return updated


@router.get("/mine")
async def my_registrations_staff(
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Hồ sơ đăng ký đang do tôi phụ trách."""
    items = await list_recruitment_applications(
        assigned_to=current_user["email"], active_only=True, limit=limit
    )
    return {
        "items": [item for item in items if item.get("source") == "self_registration"],
    }


@router.post("/{application_code}/handover")
async def handover(
    application_code: str,
    payload: HandoverRequest,
    http_request: Request,
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Chuyển hồ sơ cho người khác phụ trách.

    Chỉ quản lý được chuyển — cùng quy tắc với phân công ở các nghiệp vụ khác.
    Người đang phụ trách muốn buông thì dùng `release`: trả về hàng đợi không
    phải là giao cho một người cụ thể, nên không cần quyền quản lý.
    """
    ensure_can_assign(current_user, "Chỉ Admin/Manager được chuyển người phụ trách.")
    existing = await _load(application_code)

    new_owner = await validate_assignee(payload.assigned_to)
    previous = existing.get("assigned_to")
    if new_owner == previous:
        raise HTTPException(status_code=409, detail="Hồ sơ đã do người này phụ trách.")

    updated = await update_recruitment_application(
        application_code,
        {"assigned_to": new_owner},
        expected_status=existing["status"],
        # Khóa theo người đang giữ, để lệnh chuyển không đè lên một lần chuyển
        # khác vừa xảy ra trong tích tắc.
        owner_email=previous,
    )
    if updated is None:
        raise HTTPException(
            status_code=409,
            detail="Hồ sơ vừa đổi người phụ trách hoặc đổi trạng thái. Bạn tải lại nhé.",
        )

    details = {"from": previous, "to": new_owner, "note": payload.note}
    await _log(application_code, "handover", current_user, details)
    await create_notification(
        notification_type="application_handover",
        title="Bạn được giao một hồ sơ đăng ký",
        reference_type=REFERENCE_APPLICATION,
        reference_code=application_code,
        detail={
            "customer_name": existing.get("customer_name"),
            "assigned_to": new_owner,
            "note": payload.note,
        },
    )
    await audit_action(
        http_request,
        "application.handover",
        actor=current_user,
        target_type="recruitment_application",
        target_id=application_code,
        details=details,
    )
    return updated


@router.post("/{application_code}/release")
async def release(
    application_code: str,
    payload: ReleaseRequest,
    http_request: Request,
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Trả hồ sơ về hàng đợi.

    Cho phép chính người đang phụ trách làm việc này, không chỉ quản lý. Nhân
    viên nghỉ đột xuất hoặc nhận nhầm mà phải chờ quản lý mới buông được thì hồ
    sơ nằm chết ở đó, và ứng viên là người chịu.
    """
    existing = await _load(application_code)
    previous = existing.get("assigned_to")
    if not previous:
        raise HTTPException(status_code=409, detail="Hồ sơ này chưa ai nhận.")
    if not can_access(existing, current_user):
        raise HTTPException(status_code=403, detail="Hồ sơ này do người khác phụ trách.")

    updated = await update_recruitment_application(
        application_code,
        {"assigned_to": None},
        expected_status=existing["status"],
        owner_email=previous,
    )
    if updated is None:
        raise HTTPException(
            status_code=409,
            detail="Hồ sơ vừa thay đổi. Bạn tải lại danh sách nhé.",
        )

    details = {"from": previous, "note": payload.note}
    await _log(application_code, "released", current_user, details)
    # Không điểm, nhưng vẫn vào sổ: quản lý cần thấy ai trả việc và vì sao. Xem
    # lý do không trừ điểm ở `services/scoring.py`.
    await score_service.award(
        staff_email=previous,
        action="application.released",
        reference_type="recruitment_application",
        reference_code=application_code,
        note=payload.note,
    )
    await create_notification(
        notification_type="application_released",
        title="Một hồ sơ được trả về hàng đợi",
        reference_type=REFERENCE_APPLICATION,
        reference_code=application_code,
        detail={"customer_name": existing.get("customer_name"), "note": payload.note},
    )
    await audit_action(
        http_request,
        "application.released",
        actor=current_user,
        target_type="recruitment_application",
        target_id=application_code,
        details=details,
    )
    return updated


async def _load(application_code: str) -> dict[str, Any]:
    application = await get_recruitment_application(application_code)
    if application is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ đăng ký.")
    return application


async def _log(
    application_code: str,
    action: str,
    current_user: dict[str, Any],
    details: dict[str, Any],
) -> None:
    await create_application_event(
        {
            "application_code": application_code,
            "action": action,
            "actor_email": current_user["email"],
            "actor_name": current_user["full_name"],
            "details": details,
        }
    )


@router.get("/{application_code}/report")
async def registration_report(
    application_code: str,
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Phiếu tóm tắt tư vấn của một hồ sơ đăng ký."""
    application = await _load(application_code)

    # Hồ sơ chưa ai nhận thì ai cũng đọc được phiếu — phải đọc mới biết có nên
    # nhận hay không. Nhận rồi thì theo quy tắc phân quyền chung.
    if application.get("assigned_to") and not can_access(application, current_user):
        raise HTTPException(status_code=403, detail="Hồ sơ này do người khác phụ trách.")

    report = await reports.get_by_application(application_code)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Hồ sơ này chưa có phiếu tóm tắt (được tạo tay, không qua đăng ký sơ bộ).",
        )
    return report


# --- Cấp quyền vào hệ khách hàng ---


class GrantAccessResponse(BaseModel):
    """Mật khẩu ban đầu chỉ xuất hiện **đúng một lần**, ngay trong phản hồi này.

    Không lưu bản rõ ở đâu cả, và cũng không gửi lại được. Nhân viên đang gọi
    điện cho ứng viên thì đọc luôn; lỡ mất thì bấm cấp lại, sinh mật khẩu khác.
    """

    phone: str
    full_name: str | None
    initial_password: str
    already_existed: bool


@router.post("/{application_code}/cap-tai-khoan", response_model=GrantAccessResponse)
async def grant_portal_access(
    application_code: str,
    http_request: Request,
    current_user=Depends(get_current_user),
) -> GrantAccessResponse:
    """Cấp cho ứng viên tài khoản vào hệ khách hàng để tự theo dõi hồ sơ.

    Chỉ người đang phụ trách hồ sơ (hoặc quản lý) mới cấp được — đây là việc đi
    kèm cuộc gọi, không phải thao tác hàng loạt.
    """
    application = await _load(application_code)
    if not can_access(application, current_user):
        raise HTTPException(status_code=403, detail="Bạn không phụ trách hồ sơ này.")

    phone = (application.get("phone") or "").strip()
    if not phone:
        raise HTTPException(
            status_code=409,
            detail="Hồ sơ chưa có số điện thoại nên chưa cấp tài khoản được.",
        )

    password = candidate_accounts.generate_initial_password()
    existing = await candidate_accounts.get_account_by_phone(phone)
    if existing is None:
        account = await candidate_accounts.create_account(
            phone=phone,
            lead_code=application.get("lead_code"),
            full_name=application.get("customer_name"),
            password=password,
            created_by=current_user["email"],
        )
        already_existed = False
    else:
        # Đã có tài khoản thì đây là "cấp lại mật khẩu", không phải tạo trùng.
        # Ứng viên quên mật khẩu là chuyện thường xuyên hơn ta tưởng.
        account = await candidate_accounts.reset_password(
            phone, password, by=current_user["email"]
        )
        already_existed = True

    await _log(
        application_code,
        "portal_access_granted",
        current_user,
        {"phone": phone, "reset": already_existed},
    )
    await audit_action(
        http_request,
        "candidate_account.granted",
        actor=current_user,
        target_type="candidate_account",
        target_id=phone,
        details={"application_code": application_code, "reset": already_existed},
    )
    return GrantAccessResponse(
        phone=phone,
        full_name=(account or {}).get("full_name"),
        initial_password=password,
        already_existed=already_existed,
    )
