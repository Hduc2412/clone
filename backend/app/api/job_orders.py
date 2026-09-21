"""API danh mục đơn tuyển dụng.

Hai router tách biệt vì hai nhóm người dùng khác nhau hoàn toàn:

- `public_router` phục vụ website, không cần đăng nhập, và **chỉ** trả về đơn đã
  duyệt công khai, đang tuyển, còn hạn. Dữ liệu nội bộ như ghi chú riêng hay số
  đã tuyển được loại ngay ở tầng projection của database, không dựa vào việc
  tầng trên nhớ bỏ đi.
- `router` phục vụ hệ thống quản trị, bắt buộc đăng nhập. Xem thì mọi vai trò
  đều được; thêm, sửa, đổi trạng thái thì chỉ quản lý và quản trị viên.
"""
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pymongo.errors import DuplicateKeyError

from app.auth.security import get_current_user, require_roles
from app.core.timeutil import local_today
from app.db import job_orders as store
from app.matching import catalog
from app.services import job_order_import
from app.services.audit_service import audit_action


# Giới hạn kích thước file nhập. Một danh mục đơn hàng vài trăm dòng chỉ nặng
# vài trăm KB; file lớn hơn nhiều gần như chắc chắn là nhầm file.
MAX_IMPORT_BYTES = 5 * 1024 * 1024
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


public_router = APIRouter(prefix="/public/job-orders", tags=["Đơn tuyển dụng (công khai)"])
router = APIRouter(
    prefix="/job-orders",
    tags=["Đơn tuyển dụng"],
    dependencies=[Depends(get_current_user)],
)


# --- Mô hình dữ liệu vào ---


def _require(value: object, normalizer, field_label: str) -> str:
    normalized = normalizer(value)
    if normalized is None:
        raise ValueError(f"{field_label} không hợp lệ: {value!r}")
    return normalized


class RequirementsPayload(BaseModel):
    """Điều kiện bắt buộc — dùng để loại trừ, không dùng để xếp hạng."""

    model_config = ConfigDict(extra="forbid")

    japanese_required: str = "N5"
    education_required: str | None = None
    experience_min: float = Field(default=0, ge=0, le=40)
    age_min: int | None = Field(default=None, ge=16, le=70)
    age_max: int | None = Field(default=None, ge=16, le=70)
    gender_pref: str = "khong_yeu_cau"

    @field_validator("japanese_required", mode="before")
    @classmethod
    def _japanese(cls, value: object) -> str:
        return _require(value, catalog.normalize_japanese_level, "Trình độ tiếng Nhật")

    @field_validator("education_required", mode="before")
    @classmethod
    def _education(cls, value: object) -> str | None:
        if value in (None, ""):
            return None
        return _require(value, catalog.normalize_education, "Bằng cấp yêu cầu")

    @field_validator("gender_pref", mode="before")
    @classmethod
    def _gender(cls, value: object) -> str:
        if value in (None, ""):
            return "khong_yeu_cau"
        return _require(value, catalog.normalize_gender_pref, "Yêu cầu giới tính")

    @model_validator(mode="after")
    def _age_range(self) -> "RequirementsPayload":
        if (
            self.age_min is not None
            and self.age_max is not None
            and self.age_min > self.age_max
        ):
            raise ValueError("Tuổi tối thiểu phải nhỏ hơn hoặc bằng tuổi tối đa.")
        return self


class ReferencePayload(BaseModel):
    """Thông tin tham khảo — hiển thị và xếp hạng, không bao giờ loại ứng viên."""

    model_config = ConfigDict(extra="forbid")

    salary_min: int | None = Field(default=None, ge=0, le=2_000_000)
    salary_max: int | None = Field(default=None, ge=0, le=2_000_000)
    allowances: list[str] = Field(default_factory=list, max_length=15)
    cost_total_vnd: int | None = Field(default=None, ge=0)
    interview_date: date | None = None
    departure_expected: str | None = Field(default=None, max_length=50)
    highlights: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _salary_range(self) -> "ReferencePayload":
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("Lương tối thiểu phải nhỏ hơn hoặc bằng lương tối đa.")
        return self


class JobOrderCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=150)
    employer_name: str = Field(min_length=2, max_length=150)
    employer_type: str
    program: str
    prefecture: str
    city: str | None = Field(default=None, max_length=100)
    quota: int = Field(ge=1, le=500)
    deadline: date
    requirements: RequirementsPayload = Field(default_factory=RequirementsPayload)
    reference: ReferencePayload = Field(default_factory=ReferencePayload)
    description: str | None = Field(default=None, max_length=4000)
    internal_note: str | None = Field(default=None, max_length=1000)
    status: str = "draft"
    published: bool = False

    @field_validator("employer_type", mode="before")
    @classmethod
    def _employer_type(cls, value: object) -> str:
        return _require(value, catalog.normalize_employer_type, "Loại hình cơ sở")

    @field_validator("program", mode="before")
    @classmethod
    def _program(cls, value: object) -> str:
        return _require(value, catalog.normalize_program, "Diện chương trình")

    @field_validator("prefecture", mode="before")
    @classmethod
    def _prefecture(cls, value: object) -> str:
        return _require(value, catalog.normalize_prefecture, "Tỉnh tại Nhật Bản")

    @field_validator("status", mode="before")
    @classmethod
    def _status(cls, value: object) -> str:
        if value in (None, ""):
            return "draft"
        return _require(value, catalog.normalize_job_order_status, "Trạng thái đơn")

    @model_validator(mode="after")
    def _creatable_status(self) -> "JobOrderCreateRequest":
        # Đơn mới chỉ được tạo ở hai trạng thái này. Tạo thẳng một đơn "đã đóng"
        # hay "đủ số lượng" là vô nghĩa và làm hỏng lịch sử chuyển trạng thái.
        if self.status not in {"draft", "open"}:
            raise ValueError("Đơn mới chỉ có thể ở trạng thái Nháp hoặc Đang tuyển.")
        return self


class RequirementsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    japanese_required: str | None = None
    education_required: str | None = None
    experience_min: float | None = Field(default=None, ge=0, le=40)
    age_min: int | None = Field(default=None, ge=16, le=70)
    age_max: int | None = Field(default=None, ge=16, le=70)
    gender_pref: str | None = None

    @field_validator("japanese_required", mode="before")
    @classmethod
    def _japanese(cls, value: object) -> str | None:
        if value in (None, ""):
            return None
        return _require(value, catalog.normalize_japanese_level, "Trình độ tiếng Nhật")

    @field_validator("gender_pref", mode="before")
    @classmethod
    def _gender(cls, value: object) -> str | None:
        if value in (None, ""):
            return None
        return _require(value, catalog.normalize_gender_pref, "Yêu cầu giới tính")

    @field_validator("education_required", mode="before")
    @classmethod
    def _education(cls, value: object) -> str | None:
        if value in (None, ""):
            return None
        return _require(value, catalog.normalize_education, "Bằng cấp yêu cầu")


class ReferenceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    salary_min: int | None = Field(default=None, ge=0, le=2_000_000)
    salary_max: int | None = Field(default=None, ge=0, le=2_000_000)
    allowances: list[str] | None = Field(default=None, max_length=15)
    cost_total_vnd: int | None = Field(default=None, ge=0)
    interview_date: date | None = None
    departure_expected: str | None = Field(default=None, max_length=50)
    highlights: list[str] | None = Field(default=None, max_length=10)


class JobOrderUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=3, max_length=150)
    employer_name: str | None = Field(default=None, min_length=2, max_length=150)
    employer_type: str | None = None
    program: str | None = None
    prefecture: str | None = None
    city: str | None = Field(default=None, max_length=100)
    quota: int | None = Field(default=None, ge=1, le=500)
    deadline: date | None = None
    requirements: RequirementsUpdate | None = None
    reference: ReferenceUpdate | None = None
    description: str | None = Field(default=None, max_length=4000)
    internal_note: str | None = Field(default=None, max_length=1000)

    @field_validator("employer_type", mode="before")
    @classmethod
    def _employer_type(cls, value: object) -> str | None:
        if value in (None, ""):
            return None
        return _require(value, catalog.normalize_employer_type, "Loại hình cơ sở")

    @field_validator("program", mode="before")
    @classmethod
    def _program(cls, value: object) -> str | None:
        if value in (None, ""):
            return None
        return _require(value, catalog.normalize_program, "Diện chương trình")

    @field_validator("prefecture", mode="before")
    @classmethod
    def _prefecture(cls, value: object) -> str | None:
        if value in (None, ""):
            return None
        return _require(value, catalog.normalize_prefecture, "Tỉnh tại Nhật Bản")


class JobOrderStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    note: str | None = Field(default=None, max_length=500)

    @field_validator("status", mode="before")
    @classmethod
    def _status(cls, value: object) -> str:
        return _require(value, catalog.normalize_job_order_status, "Trạng thái đơn")


class JobOrderPublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    published: bool


# --- Hàm dùng chung ---


def _to_document(payload: JobOrderCreateRequest, code: str, actor: dict) -> dict[str, Any]:
    data = payload.model_dump()
    reference = data["reference"]
    interview_date = reference.get("interview_date")
    return {
        **data,
        "code": code,
        "deadline": data["deadline"].isoformat(),
        "reference": {
            **reference,
            "interview_date": interview_date.isoformat() if interview_date else None,
        },
        "region_group": catalog.region_for_prefecture(data["prefecture"]),
        "hired_count": 0,
        "created_by": actor["email"],
        "updated_by": actor["email"],
    }


def _serialize_dates(fields: dict[str, Any]) -> dict[str, Any]:
    """Ngày lưu dạng chuỗi ISO để so sánh được trực tiếp trong truy vấn MongoDB."""
    if isinstance(fields.get("deadline"), date):
        fields["deadline"] = fields["deadline"].isoformat()
    reference = fields.get("reference")
    if isinstance(reference, dict) and isinstance(reference.get("interview_date"), date):
        reference["interview_date"] = reference["interview_date"].isoformat()
    return fields


def _decorate(order: dict[str, Any]) -> dict[str, Any]:
    """Gắn nhãn tiếng Việt để giao diện không phải giữ bản sao của bảng danh mục."""
    requirements = order.get("requirements") or {}
    education = requirements.get("education_required")
    order["labels"] = {
        "status": catalog.JOB_ORDER_STATUS_LABELS.get(order.get("status", "")),
        "employer_type": catalog.EMPLOYER_TYPE_LABELS.get(order.get("employer_type", "")),
        "program": catalog.PROGRAM_LABELS.get(order.get("program", "")),
        "region_group": catalog.REGION_LABELS.get(order.get("region_group") or ""),
        "japanese_required": catalog.JAPANESE_LEVEL_LABELS.get(
            requirements.get("japanese_required", "")
        ),
        "education_required": catalog.EDUCATION_LABELS.get(education) if education else None,
        "gender_pref": catalog.GENDER_PREF_LABELS.get(
            requirements.get("gender_pref", "")
        ),
    }
    return order


async def _load_or_404(code: str) -> dict[str, Any]:
    order = await store.get_job_order(code)
    if order is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn tuyển dụng.")
    return order


# --- Endpoint công khai ---


@public_router.get("")
async def public_job_orders(
    prefecture: str | None = Query(default=None, max_length=50),
    region_group: str | None = Query(default=None, max_length=30),
    employer_type: str | None = Query(default=None, max_length=40),
    program: str | None = Query(default=None, max_length=40),
    japanese_required: str | None = Query(default=None, max_length=15),
    limit: int = Query(default=30, ge=1, le=100),
):
    query = store.build_query(
        only_public=True,
        prefecture=catalog.normalize_prefecture(prefecture),
        region_group=catalog.normalize_region(region_group),
        employer_type=catalog.normalize_employer_type(employer_type),
        program=catalog.normalize_program(program),
        japanese_required=catalog.normalize_japanese_level(japanese_required),
    )
    orders = await store.list_job_orders(query, limit=limit, public=True)
    return [_decorate(order) for order in orders]


@public_router.get("/facets")
async def public_job_order_facets():
    return await store.public_facets()


@public_router.get("/{code}")
async def public_job_order_detail(code: str):
    order = await store.get_job_order(code, public=True)
    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Đơn tuyển dụng không tồn tại hoặc đã ngừng nhận hồ sơ.",
        )
    return _decorate(order)


# --- Endpoint quản trị ---


@router.get("")
async def job_orders(
    status: str | None = Query(default=None, max_length=20),
    published: bool | None = None,
    prefecture: str | None = Query(default=None, max_length=50),
    region_group: str | None = Query(default=None, max_length=30),
    employer_type: str | None = Query(default=None, max_length=40),
    program: str | None = Query(default=None, max_length=40),
    japanese_required: str | None = Query(default=None, max_length=15),
    limit: int = Query(default=100, ge=1, le=500),
):
    if status and catalog.normalize_job_order_status(status) is None:
        raise HTTPException(status_code=400, detail="Trạng thái đơn không hợp lệ.")
    query = store.build_query(
        status=catalog.normalize_job_order_status(status),
        published=published,
        prefecture=catalog.normalize_prefecture(prefecture),
        region_group=catalog.normalize_region(region_group),
        employer_type=catalog.normalize_employer_type(employer_type),
        program=catalog.normalize_program(program),
        japanese_required=catalog.normalize_japanese_level(japanese_required),
    )
    orders = await store.list_job_orders(query, limit=limit)
    return [_decorate(order) for order in orders]


@router.get("/meta")
async def job_order_meta():
    """Danh mục và bảng chuyển trạng thái cho giao diện quản trị."""
    return catalog.catalog_meta()


@router.get("/import/template")
async def download_import_template(
    include_samples: bool = True,
    _current_user=Depends(require_roles("admin", "manager")),
):
    """Tải file Excel mẫu để doanh nghiệp điền đơn hàng thật."""
    content = job_order_import.template_bytes(include_samples=include_samples)
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": 'attachment; filename="MauDonHang.xlsx"',
        },
    )


@router.post("/import")
async def import_job_orders(
    http_request: Request,
    file: UploadFile = File(...),
    dry_run: bool = Query(default=True),
    current_user=Depends(require_roles("admin", "manager")),
):
    """Đọc file Excel, kiểm tra từng dòng, và chỉ ghi khi được xác nhận.

    Mặc định `dry_run=true`: chỉ trả về kết quả kiểm tra để người dùng xem trước.
    Ghi nửa chừng rồi mới báo lỗi ở dòng thứ tám mươi là tình huống không dọn được,
    nên bước xem trước là bắt buộc trong luồng giao diện.
    """
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=415,
            detail="Chỉ nhận file Excel định dạng .xlsx.",
        )
    content = await file.read()
    if len(content) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="File vượt quá 5MB.")

    try:
        preview = job_order_import.parse_workbook(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if preview.missing_columns:
        raise HTTPException(
            status_code=400,
            detail=(
                "File thiếu cột bắt buộc: "
                + ", ".join(preview.missing_columns)
                + ". Hãy tải lại file mẫu."
            ),
        )

    result = preview.as_dict()
    result["dry_run"] = dry_run
    if dry_run:
        return result

    created, updated, failed = 0, 0, []
    for row in preview.valid_rows():
        try:
            if row.action == "update":
                order = await store.update_job_order(
                    row.code, row.data, updated_by=current_user["email"]
                )
                if order is None:
                    failed.append(
                        {"row_number": row.row_number, "reason": f"Không tìm thấy đơn {row.code}."}
                    )
                    continue
                updated += 1
                await store.record_event(
                    row.code,
                    "imported",
                    actor_email=current_user["email"],
                    actor_name=current_user["full_name"],
                    details={"row_number": row.row_number, "action": "update"},
                )
            else:
                code = await store.next_job_order_code()
                document = {
                    **row.data,
                    "code": code,
                    "created_by": current_user["email"],
                    "updated_by": current_user["email"],
                }
                await store.create_job_order(document)
                created += 1
                await store.record_event(
                    code,
                    "imported",
                    actor_email=current_user["email"],
                    actor_name=current_user["full_name"],
                    new_status=document["status"],
                    details={"row_number": row.row_number, "action": "create"},
                )
        except DuplicateKeyError:
            failed.append(
                {"row_number": row.row_number, "reason": "Mã đơn đã tồn tại."}
            )

    await audit_action(
        http_request,
        "job_order.imported",
        actor=current_user,
        target_type="job_order",
        target_id=file.filename,
        details={"created": created, "updated": updated, "failed": len(failed)},
    )
    result["applied"] = {"created": created, "updated": updated, "failed": failed}
    return result


@router.get("/{code}")
async def job_order_detail(code: str):
    return _decorate(await _load_or_404(code))


@router.get("/{code}/events")
async def job_order_events(code: str):
    await _load_or_404(code)
    return await store.list_events(code)


@router.post("", status_code=201)
async def create_job_order(
    payload: JobOrderCreateRequest,
    http_request: Request,
    current_user=Depends(require_roles("admin", "manager")),
):
    if payload.deadline < local_today():
        raise HTTPException(status_code=400, detail="Hạn nộp hồ sơ đã qua.")
    code = await store.next_job_order_code()
    try:
        order = await store.create_job_order(_to_document(payload, code, current_user))
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Mã đơn đã tồn tại.") from exc
    await store.record_event(
        code,
        "created",
        actor_email=current_user["email"],
        actor_name=current_user["full_name"],
        new_status=order["status"],
    )
    await audit_action(
        http_request,
        "job_order.created",
        actor=current_user,
        target_type="job_order",
        target_id=code,
        details={"status": order["status"], "published": order["published"]},
    )
    return _decorate(order)


@router.patch("/{code}")
async def update_job_order(
    code: str,
    payload: JobOrderUpdateRequest,
    http_request: Request,
    current_user=Depends(require_roles("admin", "manager")),
):
    existing = await _load_or_404(code)
    if existing["status"] == "closed":
        raise HTTPException(
            status_code=409,
            detail="Đơn đã đóng nên không sửa được. Hãy mở lại đơn trước khi sửa.",
        )
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        return _decorate(existing)
    if isinstance(fields.get("deadline"), date) and fields["deadline"] < local_today():
        raise HTTPException(status_code=400, detail="Hạn nộp hồ sơ đã qua.")
    fields = _serialize_dates(fields)
    if "prefecture" in fields:
        fields["region_group"] = catalog.region_for_prefecture(fields["prefecture"])

    merged_requirements = {
        **(existing.get("requirements") or {}),
        **{
            key: value
            for key, value in (fields.get("requirements") or {}).items()
            if key in {"age_min", "age_max"}
        },
    }
    if (
        merged_requirements.get("age_min") is not None
        and merged_requirements.get("age_max") is not None
        and merged_requirements["age_min"] > merged_requirements["age_max"]
    ):
        raise HTTPException(
            status_code=400,
            detail="Tuổi tối thiểu phải nhỏ hơn hoặc bằng tuổi tối đa.",
        )

    order = await store.update_job_order(
        code, fields, updated_by=current_user["email"]
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn tuyển dụng.")
    changed = sorted(fields)
    await store.record_event(
        code,
        "updated",
        actor_email=current_user["email"],
        actor_name=current_user["full_name"],
        details={"changed_fields": changed},
    )
    await audit_action(
        http_request,
        "job_order.updated",
        actor=current_user,
        target_type="job_order",
        target_id=code,
        details={"changed_fields": changed},
    )
    return _decorate(order)


@router.patch("/{code}/status")
async def change_job_order_status(
    code: str,
    payload: JobOrderStatusRequest,
    http_request: Request,
    current_user=Depends(require_roles("admin", "manager")),
):
    existing = await _load_or_404(code)
    current_status = existing["status"]
    if payload.status == current_status:
        return _decorate(existing)
    allowed = catalog.JOB_ORDER_TRANSITIONS.get(current_status, frozenset())
    if payload.status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Không thể chuyển đơn từ "
                f"{catalog.JOB_ORDER_STATUS_LABELS[current_status]} sang "
                f"{catalog.JOB_ORDER_STATUS_LABELS[payload.status]}."
            ),
        )
    # Đơn không còn nhận hồ sơ thì phải rời khỏi website ngay, không chờ ai nhớ
    # tắt công khai bằng tay.
    order = await store.change_status(
        code,
        new_status=payload.status,
        expected_status=current_status,
        updated_by=current_user["email"],
        unpublish=payload.status != "open",
    )
    if order is None:
        raise HTTPException(
            status_code=409,
            detail="Đơn vừa được người khác thay đổi. Vui lòng tải lại trang.",
        )
    await store.record_event(
        code,
        "status_changed",
        actor_email=current_user["email"],
        actor_name=current_user["full_name"],
        old_status=current_status,
        new_status=payload.status,
        details={"note": payload.note},
    )
    await audit_action(
        http_request,
        "job_order.status_changed",
        actor=current_user,
        target_type="job_order",
        target_id=code,
        details={"from": current_status, "to": payload.status},
    )
    return _decorate(order)


@router.patch("/{code}/publish")
async def publish_job_order(
    code: str,
    payload: JobOrderPublishRequest,
    http_request: Request,
    current_user=Depends(require_roles("admin", "manager")),
):
    existing = await _load_or_404(code)
    order = await store.set_published(
        code, published=payload.published, updated_by=current_user["email"]
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn tuyển dụng.")
    # Bật công khai cho đơn chưa mở tuyển hoặc đã hết hạn là thao tác hợp lệ
    # nhưng chưa có tác dụng; báo lại để người dùng không tưởng đơn đã lên web.
    visible = (
        order["published"]
        and order["status"] == "open"
        and order["deadline"] >= local_today().isoformat()
    )
    await store.record_event(
        code,
        "published_changed",
        actor_email=current_user["email"],
        actor_name=current_user["full_name"],
        details={"published": payload.published, "visible_publicly": visible},
    )
    await audit_action(
        http_request,
        "job_order.published_changed",
        actor=current_user,
        target_type="job_order",
        target_id=code,
        details={"published": payload.published},
    )
    return _decorate(order) | {"visible_publicly": visible}


@router.delete("/{code}", status_code=204)
async def delete_job_order(
    code: str,
    http_request: Request,
    current_user=Depends(require_roles("admin")),
):
    existing = await _load_or_404(code)
    if existing["status"] != "draft":
        raise HTTPException(
            status_code=409,
            detail="Chỉ xóa được đơn ở trạng thái Nháp. Đơn đã công bố thì hãy đóng đơn.",
        )
    if not await store.delete_job_order(code):
        raise HTTPException(status_code=409, detail="Đơn vừa thay đổi, không xóa được.")
    await audit_action(
        http_request,
        "job_order.deleted",
        actor=current_user,
        target_type="job_order",
        target_id=code,
    )
