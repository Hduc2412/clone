import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from app.auth.security import get_current_user, require_roles
from app.db.database import (
    create_application_event,
    create_recruitment_application,
    get_managed_lead,
    get_recruitment_application,
    list_application_events,
    list_recruitment_applications,
    update_recruitment_application,
)
from app.services import score_service
from app.services.assignment import (
    can_access,
    ensure_can_assign,
    is_privileged,
    validate_assignee,
)
from app.services.audit_service import audit_action


router = APIRouter(prefix="/applications", tags=["Recruitment applications"])

APPLICATION_STATUSES = {
    "draft",
    "collecting_documents",
    "screening",
    "eligible",
    "training",
    "waiting_interview",
    "passed",
    "visa_processing",
    "ready_departure",
    "departed",
    "rejected",
    "withdrawn",
    "cancelled",
}
CLOSED_STATUSES = {"departed", "rejected", "withdrawn", "cancelled"}
STATUS_TRANSITIONS = {
    "draft": {"collecting_documents", "withdrawn", "cancelled"},
    "collecting_documents": {"screening", "withdrawn", "cancelled"},
    "screening": {"collecting_documents", "eligible", "rejected", "withdrawn", "cancelled"},
    "eligible": {"training", "waiting_interview", "withdrawn", "cancelled"},
    "training": {"waiting_interview", "withdrawn", "cancelled"},
    "waiting_interview": {"training", "passed", "rejected", "withdrawn", "cancelled"},
    "passed": {"visa_processing", "withdrawn", "cancelled"},
    "visa_processing": {"ready_departure", "withdrawn", "cancelled"},
    "ready_departure": {"departed", "withdrawn", "cancelled"},
    "departed": set(),
    "rejected": set(),
    "withdrawn": set(),
    "cancelled": set(),
}


class ApplicationCreateRequest(BaseModel):
    lead_code: str = Field(min_length=4, max_length=30)
    assigned_to: str | None = Field(default=None, max_length=150)
    destination: str | None = Field(default=None, max_length=100)
    japanese_level: str | None = Field(default=None, max_length=30)
    qualification: str | None = Field(default=None, max_length=150)
    note: str | None = Field(default=None, max_length=1000)


class ApplicationUpdateRequest(BaseModel):
    status: str | None = None
    assigned_to: str | None = Field(default=None, max_length=150)
    destination: str | None = Field(default=None, max_length=100)
    japanese_level: str | None = Field(default=None, max_length=30)
    qualification: str | None = Field(default=None, max_length=150)
    note: str | None = Field(default=None, max_length=1000)


def _validate_status_transition(current_status: str, next_status: str) -> None:
    if next_status == current_status:
        return
    if next_status not in STATUS_TRANSITIONS.get(current_status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Không thể chuyển hồ sơ từ {current_status} sang {next_status}.",
        )


async def _record_event(
    application_code: str,
    action: str,
    current_user: dict,
    details: dict | None = None,
) -> None:
    await create_application_event(
        {
            "application_code": application_code,
            "action": action,
            "actor_email": current_user["email"],
            "actor_name": current_user["full_name"],
            "details": details or {},
        }
    )


@router.get("")
async def applications(
    status: str | None = None,
    lead_code: str | None = Query(default=None, max_length=30),
    assigned_to: str | None = Query(default=None, max_length=150),
    active_only: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    current_user=Depends(get_current_user),
):
    if status and status not in APPLICATION_STATUSES:
        raise HTTPException(status_code=400, detail="Trạng thái hồ sơ không hợp lệ.")
    if not is_privileged(current_user):
        assigned_to = current_user["email"]
    return await list_recruitment_applications(
        status=status,
        lead_code=lead_code,
        assigned_to=assigned_to,
        active_only=active_only,
        limit=limit,
    )


@router.get("/{application_code}")
async def application_detail(
    application_code: str,
    current_user=Depends(get_current_user),
):
    application = await get_recruitment_application(application_code)
    if application is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ tuyển dụng.")
    if not can_access(application, current_user):
        raise HTTPException(status_code=403, detail="Bạn không được truy cập hồ sơ này.")
    return application


@router.get("/{application_code}/events")
async def application_history(
    application_code: str,
    current_user=Depends(get_current_user),
):
    application = await get_recruitment_application(application_code)
    if application is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ tuyển dụng.")
    if not can_access(application, current_user):
        raise HTTPException(status_code=403, detail="Bạn không được truy cập hồ sơ này.")
    return await list_application_events(application_code)


@router.post("", status_code=201)
async def create_application(
    payload: ApplicationCreateRequest,
    http_request: Request,
    current_user=Depends(require_roles("admin", "manager")),
):
    lead = await get_managed_lead(payload.lead_code)
    if lead is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy khách hàng/lead.")
    assigned_to = await validate_assignee(payload.assigned_to or lead.get("assigned_to"))
    application_code = f"HS-{secrets.token_hex(3).upper()}"
    document = {
        **payload.model_dump(),
        "application_code": application_code,
        "lead_code": lead["lead_code"],
        "customer_name": lead["customer_name"],
        "phone": lead["phone"],
        "assigned_to": assigned_to,
        "status": "draft",
        "is_active": True,
    }
    try:
        application = await create_recruitment_application(document)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=409,
            detail="Khách hàng đang có một hồ sơ tuyển dụng hoạt động.",
        ) from exc
    await _record_event(application_code, "created", current_user, {"status": "draft"})
    await audit_action(
        http_request, "application.created", actor=current_user,
        target_type="recruitment_application", target_id=application_code,
    )
    return application


@router.patch("/{application_code}")
async def update_application(
    application_code: str,
    payload: ApplicationUpdateRequest,
    http_request: Request,
    current_user=Depends(get_current_user),
):
    existing = await get_recruitment_application(application_code)
    if existing is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ tuyển dụng.")
    if not can_access(existing, current_user):
        raise HTTPException(status_code=403, detail="Bạn không được cập nhật hồ sơ này.")
    fields = payload.model_dump(exclude_unset=True)
    if fields.get("status") and fields["status"] not in APPLICATION_STATUSES:
        raise HTTPException(status_code=400, detail="Trạng thái hồ sơ không hợp lệ.")
    if fields.get("status"):
        _validate_status_transition(existing["status"], fields["status"])
    if "assigned_to" in fields:
        ensure_can_assign(current_user, "Chỉ Admin/Manager được phân công hồ sơ.")
        fields["assigned_to"] = await validate_assignee(fields["assigned_to"])
    if fields.get("status"):
        fields["is_active"] = fields["status"] not in CLOSED_STATUSES
    try:
        updated = await update_recruitment_application(
            application_code,
            fields,
            expected_status=existing["status"],
            owner_email=None if is_privileged(current_user) else current_user["email"],
        )
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=409,
            detail="Khách hàng đã có một hồ sơ tuyển dụng hoạt động khác.",
        ) from exc
    if updated is None:
        raise HTTPException(
            status_code=409,
            detail="Hồ sơ đã thay đổi hoặc không còn được giao cho bạn. Vui lòng tải lại.",
        )
    # Xuất cảnh là đích của cả chuỗi tư vấn, nên là mốc duy nhất trong vòng đời
    # hồ sơ có điểm. Các bước giữa chỉ là đi qua, chấm điểm từng bước sẽ thành
    # thưởng cho việc bấm nút.
    if fields.get("status") == "departed":
        await score_service.award(
            staff_email=existing.get("assigned_to"),
            action="application.departed",
            reference_type="recruitment_application",
            reference_code=application_code,
        )

    changed_fields = sorted(key for key in fields if key != "is_active")
    event_details = {"changed_fields": changed_fields}
    if "status" in fields:
        event_details.update({"old_status": existing["status"], "new_status": fields["status"]})
    await _record_event(application_code, "updated", current_user, event_details)
    await audit_action(
        http_request, "application.updated", actor=current_user,
        target_type="recruitment_application", target_id=application_code,
        details=event_details,
    )
    return updated


# --- Ghi kết quả buổi sơ tuyển ---
#
# Mắt xích giữa phần mềm và con người. Trình độ tiếng Nhật là tiêu chí loại người
# nhiều nhất trong bảy điều kiện bắt buộc, và nó **không xác thực được bằng máy**:
# nhìn ảnh chụp bằng không phân biệt được thật với giả, còn ngồi đối diện thì hỏi
# vài câu là biết ngay. Nên việc ấy là của buổi gặp, và hệ thống chỉ ghi lại kết
# quả cùng cách đối chứng.
#
# ## Vì sao gắn vào hồ sơ tuyển dụng, không gắn vào lịch hẹn
#
# Bản thiết kế ban đầu định đặt ở `POST /appointments/{code}/ket-qua`. Nhưng bản
# ghi lịch hẹn chỉ có tên và số điện thoại — **không nối tới hồ sơ năng lực, cũng
# không nối tới hồ sơ tuyển dụng**. Đặt ở đó thì phải dò ngược ứng viên theo số
# điện thoại, mà số điện thoại không phải khóa bền: một người đổi số, hai người
# dùng chung số, hoặc số cũ được cấp lại cho người khác.
#
# Hồ sơ tuyển dụng thì mang sẵn `profile_code` và chính nó là thứ có máy trạng
# thái. Nên đặt ở đây, và không phải đoán ai là ai.


class KetQuaSoTuyenBody(BaseModel):
    """Một buổi gặp, một lời gọi, đổi cả hai thứ."""

    japanese_level: str = Field(max_length=20)
    chung_cu: str = Field(max_length=30)
    hinh_thuc: str = Field(default="truc_tiep", max_length=20)
    next_status: str = Field(max_length=30)
    note: str | None = Field(default=None, max_length=1000)


HINH_THUC_GAP = ("truc_tiep", "truc_tuyen")


@router.post("/{application_code}/so-tuyen")
async def ghi_ket_qua_so_tuyen(
    application_code: str,
    payload: KetQuaSoTuyenBody,
    http_request: Request,
    current_user=Depends(get_current_user),
):
    """Ghi kết quả buổi sơ tuyển: chốt trình độ tiếng Nhật **và** trạng thái hồ sơ.

    ## Vì sao phải là một lời gọi

    Hai việc này luôn đi cùng nhau trong đời thật — nhân viên vừa gặp xong, biết
    trình độ thật của ứng viên, và quyết định cho đi tiếp hay không. Tách thành
    hai nút thì sớm muộn sẽ có hồ sơ bấm được cái này mà quên cái kia, và khi ấy
    **hai chỗ trong hệ thống nói hai điều khác nhau về cùng một người**: hồ sơ
    năng lực ghi "chưa học" trong khi hồ sơ tuyển dụng ghi "đạt sơ tuyển".

    ## Thứ tự ghi có chủ ý

    MongoDB ở đây không dùng giao dịch, nên không thể hứa hai lần ghi cùng thành
    công. Thứ có thể làm là **kiểm hết trước khi ghi bất cứ thứ gì**, rồi chọn thứ
    tự sao cho nửa chừng là nửa ít hại hơn.

    Ghi trình độ trước, trạng thái sau. Nếu trượt ở bước hai: hồ sơ năng lực đã có
    trình độ đã đối chứng, còn hồ sơ tuyển dụng vẫn nằm ở bước sơ tuyển — nhân
    viên mở ra thấy việc chưa xong và làm lại. Ngược lại thì tệ hơn nhiều: hồ sơ
    tuyển dụng ghi "đạt" trong khi trình độ vẫn là lời khai chưa ai kiểm, tức hệ
    thống khẳng định một người đủ điều kiện dựa trên dữ liệu nó chưa xác nhận.

    ## Không có cửa sau cho máy trạng thái

    Chuyển trạng thái vẫn đi qua đúng `_validate_status_transition` như đường sửa
    hồ sơ thường. Một đường ghi mới mà nới luật chuyển trạng thái thì máy trạng
    thái coi như không còn.
    """
    from app.db import candidate_profiles as profiles
    from app.matching import catalog

    existing = await get_recruitment_application(application_code)
    if existing is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ tuyển dụng.")
    if not can_access(existing, current_user):
        raise HTTPException(status_code=403, detail="Hồ sơ này do người khác phụ trách.")

    # --- Kiểm hết trước khi ghi ---
    muc = catalog.normalize_japanese_level(payload.japanese_level)
    if muc is None:
        raise HTTPException(
            status_code=422,
            detail=f"Trình độ tiếng Nhật không hợp lệ: {payload.japanese_level!r}.",
        )
    if payload.chung_cu not in profiles.CAC_CHUNG_CU:
        raise HTTPException(
            status_code=422,
            detail=f"Cách đối chứng không hợp lệ. Chọn một trong {profiles.CAC_CHUNG_CU}.",
        )
    if payload.hinh_thuc not in HINH_THUC_GAP:
        raise HTTPException(
            status_code=422,
            detail=f"Hình thức gặp không hợp lệ. Chọn một trong {HINH_THUC_GAP}.",
        )
    if payload.next_status not in APPLICATION_STATUSES:
        raise HTTPException(
            status_code=422, detail=f"Trạng thái không hợp lệ: {payload.next_status!r}."
        )
    _validate_status_transition(existing["status"], payload.next_status)

    ma_ho_so = existing.get("profile_code")
    if not ma_ho_so:
        raise HTTPException(
            status_code=409,
            detail="Hồ sơ tuyển dụng này chưa gắn hồ sơ năng lực nên chưa ghi được "
            "trình độ. Nhân viên tạo tay thì phải gắn hồ sơ trước.",
        )
    ho_so = await profiles.get_by_code(ma_ho_so)
    if ho_so is None:
        raise HTTPException(
            status_code=409, detail=f"Không tìm thấy hồ sơ năng lực {ma_ho_so}."
        )

    # --- Bước 1: trình độ tiếng Nhật, nguồn `staff` ---
    fields, _ = profiles.merge_section(
        ho_so.get("fields"),
        {"japanese_level": muc},
        source="staff",
        allowed=profiles.FIELD_KEYS,
        promote_on_equal=True,
    )
    fields = profiles.danh_dau_xac_thuc(
        fields, chung_cu=payload.chung_cu, nguoi_ghi=current_user["email"]
    )
    da_ghi = await profiles.apply_changes(
        ho_so["session_id"],
        expected_version=ho_so.get("version", 0),
        fields=fields,
        preferences=ho_so.get("preferences") or {},
        history=ho_so,
    )
    if da_ghi is None:
        raise HTTPException(
            status_code=409,
            detail="Hồ sơ năng lực vừa được người khác sửa. Tải lại rồi ghi lại "
            "kết quả — chưa có gì được lưu.",
        )

    # --- Bước 2: trạng thái hồ sơ tuyển dụng ---
    cap_nhat = {"status": payload.next_status}
    if payload.note:
        cap_nhat["note"] = payload.note
    updated = await update_recruitment_application(application_code, cap_nhat)
    if updated is None:
        raise HTTPException(
            status_code=409,
            detail=f"Đã ghi trình độ {muc} vào hồ sơ {ma_ho_so}, nhưng KHÔNG đổi "
            f"được trạng thái hồ sơ tuyển dụng. Mở lại hồ sơ và đổi trạng thái tay.",
        )

    chi_tiet = {
        "japanese_level": muc,
        "chung_cu": payload.chung_cu,
        "muc_xac_thuc": profiles.muc_xac_thuc(payload.chung_cu),
        "hinh_thuc": payload.hinh_thuc,
        "old_status": existing["status"],
        "new_status": payload.next_status,
        "profile_code": ma_ho_so,
    }
    await _record_event(application_code, "so_tuyen", current_user, chi_tiet)
    await audit_action(
        http_request,
        "application.so_tuyen",
        actor=current_user,
        target_type="recruitment_application",
        target_id=application_code,
        details=chi_tiet,
    )
    return {
        **updated,
        "so_tuyen": chi_tiet,
        # Nói thẳng khi trình độ vẫn chỉ là lời khai, dù nhân viên đã cho đi tiếp.
        # Đây là quyết định của con người và hệ thống không chặn — nhưng nó phải
        # hiện ra, không được lặng lẽ mang nhãn "đã xác thực".
        "canh_bao": (
            "Ứng viên không xuất trình được căn cứ nào, nên trình độ tiếng Nhật "
            "vẫn được ghi là TỰ KHAI. Buổi phỏng vấn với công ty Nhật sẽ kiểm lại."
            if payload.chung_cu == profiles.CHUNG_CU_KHONG_CO
            else None
        ),
    }
