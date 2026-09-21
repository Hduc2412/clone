"""API hồ sơ ứng viên.

Hai router như bên đơn tuyển dụng: một công khai cho ứng viên tự nhập, một sau
đăng nhập cho nhân viên.

Điểm cần chú ý nhất: **nguồn của dữ liệu không bao giờ nhận từ phía client**.
Router công khai luôn ghi `user_confirmed`, router quản trị luôn ghi `staff`, và
bộ đọc CV sau này gọi thẳng tầng dữ liệu với `cv`. Nếu để client tự khai nguồn
thì một người bất kỳ có thể gửi `{"source": "staff"}` và giá trị của họ sẽ đè lên
thứ nhân viên đã sửa. Mọi mô hình dữ liệu vào đều đặt `extra="forbid"` nên trường
lạ bị chặn ngay chứ không âm thầm bỏ qua.
"""
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pymongo.errors import DuplicateKeyError

from app.auth.security import get_current_user, require_roles
from app.core.codes import PREFIX_PROFILE, new_code
from app.core.phone import normalize_vietnamese_phone
from app.core.rate_limit import client_ip, rate_limiter
from app.core.timeutil import local_today, utc_now
from app.db import candidate_profiles as store
from app.matching import catalog
from app.services.assignment import can_access, ensure_can_assign, is_privileged, validate_assignee
from app.services.audit_service import audit_action


public_router = APIRouter(prefix="/public/profiles", tags=["Hồ sơ ứng viên (công khai)"])
router = APIRouter(
    prefix="/profiles",
    tags=["Hồ sơ ứng viên"],
    dependencies=[Depends(get_current_user)],
)

SESSION_PATTERN = r"^[A-Za-z0-9_-]{8,64}$"


def _optional(normalizer, label: str):
    """Dựng validator cho trường tùy chọn: rỗng thì bỏ qua, sai thì báo rõ."""

    def validate(value: object) -> str | None:
        if value in (None, ""):
            return None
        normalized = normalizer(value)
        if normalized is None:
            raise ValueError(f"{label} không hợp lệ: {value!r}")
        return normalized

    return validate


class FieldsPayload(BaseModel):
    """Năng lực kiểm chứng được. Chỉ mục này tham gia vào điều kiện bắt buộc."""

    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    birth_year: int | None = Field(default=None, ge=1950, le=2015)
    gender: str | None = None
    education_level: str | None = None
    major: str | None = Field(default=None, max_length=100)
    japanese_level: str | None = None
    experience_years: float | None = Field(default=None, ge=0, le=50)
    care_experience: bool | None = None
    phone: str | None = None

    @field_validator("gender", mode="before")
    @classmethod
    def _gender(cls, value: object) -> str | None:
        return _optional(catalog.normalize_gender, "Giới tính")(value)

    @field_validator("education_level", mode="before")
    @classmethod
    def _education(cls, value: object) -> str | None:
        return _optional(catalog.normalize_education, "Bằng cấp")(value)

    @field_validator("japanese_level", mode="before")
    @classmethod
    def _japanese(cls, value: object) -> str | None:
        return _optional(catalog.normalize_japanese_level, "Trình độ tiếng Nhật")(value)

    @field_validator("phone", mode="before")
    @classmethod
    def _phone(cls, value: object) -> str | None:
        if value in (None, ""):
            return None
        return normalize_vietnamese_phone(str(value))

    @model_validator(mode="after")
    def _birth_year_not_in_the_future(self) -> "FieldsPayload":
        if self.birth_year and self.birth_year > local_today().year - 15:
            raise ValueError("Năm sinh không hợp lệ.")
        return self


class PreferencesPayload(BaseModel):
    """Nguyện vọng do ứng viên nói. Chỉ dùng để xếp hạng, không bao giờ loại đơn."""

    model_config = ConfigDict(extra="forbid")

    desired_prefecture: str | None = None
    desired_region_group: str | None = None
    desired_employer_type: str | None = None
    salary_expectation_jpy: int | None = Field(default=None, ge=0, le=2_000_000)
    budget_vnd: int | None = Field(default=None, ge=0, le=1_000_000_000)
    reason: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("desired_prefecture", mode="before")
    @classmethod
    def _prefecture(cls, value: object) -> str | None:
        return _optional(catalog.normalize_prefecture, "Tỉnh mong muốn")(value)

    @field_validator("desired_region_group", mode="before")
    @classmethod
    def _region(cls, value: object) -> str | None:
        return _optional(catalog.normalize_region, "Vùng mong muốn")(value)

    @field_validator("desired_employer_type", mode="before")
    @classmethod
    def _employer_type(cls, value: object) -> str | None:
        return _optional(catalog.normalize_employer_type, "Loại hình cơ sở mong muốn")(value)

    @model_validator(mode="after")
    def _derive_region(self) -> "PreferencesPayload":
        # Nêu tỉnh là đủ. Bắt chọn cả tỉnh lẫn vùng chỉ tạo cơ hội cho hai giá
        # trị mâu thuẫn nhau.
        if self.desired_region_group is None and self.desired_prefecture:
            region = catalog.region_for_prefecture(self.desired_prefecture)
            object.__setattr__(self, "desired_region_group", region)
            # Phải đánh dấu là đã đặt, nếu không `exclude_unset=True` ở
            # `_payload_values` sẽ loại đúng giá trị vừa suy ra. Hậu quả không hề
            # nhẹ: ứng viên muốn Tokyo sẽ chấm một đơn ở Kanagawa (cùng vùng
            # Kantō, đáng +25) ngang bằng một đơn ở Fukuoka.
            if region is not None:
                self.__pydantic_fields_set__.add("desired_region_group")
        return self


class ProfileCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(pattern=SESSION_PATTERN)
    mode: Literal["manual", "extracted"] = "manual"
    fields: FieldsPayload = Field(default_factory=FieldsPayload)
    preferences: PreferencesPayload = Field(default_factory=PreferencesPayload)


class ProfilePatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: FieldsPayload | None = None
    preferences: PreferencesPayload | None = None
    expected_version: int | None = Field(default=None, ge=1)


class AssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assigned_to: str | None = Field(default=None, max_length=150)


# --- Hàm dùng chung ---


def _payload_values(payload: BaseModel | None) -> dict[str, Any]:
    if payload is None:
        return {}
    return {
        key: value
        for key, value in payload.model_dump(exclude_unset=True).items()
        if value is not None
    }


def _decorate(profile: dict[str, Any]) -> dict[str, Any]:
    """Nhãn hiển thị. Định nghĩa nằm ở tầng dữ liệu vì phiếu tóm tắt cũng dùng."""
    return store.decorate(profile)


async def _load_or_404(session_id: str) -> dict[str, Any]:
    profile = await store.get_by_session(session_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Chưa có hồ sơ cho phiên này.")
    return profile


async def _apply(
    profile: dict[str, Any],
    *,
    fields: dict[str, Any],
    preferences: dict[str, Any],
    source: str,
    changed_by: str,
    expected_version: int | None,
    confirm: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    if confirm:
        # Confirming a machine draft promotes its values, not just its status.
        fields = {key: item["value"] for key, item in profile.get("fields", {}).items()}
        preferences = {key: item["value"] for key, item in profile.get("preferences", {}).items()}
    # Chỉ bước xác nhận mới được nâng nguồn của một ô khi giá trị không đổi. Ở
    # các luồng khác — nhất là nhân viên sửa hồ sơ — gửi lại đúng giá trị cũ phải
    # giữ nguyên ô, để không xóa mất dấu "ứng viên xác nhận" và đoạn trích từ CV.
    merged_fields, changed_fields = store.merge_section(
        profile.get("fields"), fields, source=source, allowed=store.FIELD_KEYS,
        promote_on_equal=confirm,
    )
    merged_preferences, changed_preferences = store.merge_section(
        profile.get("preferences"), preferences, source=source, allowed=store.PREFERENCE_KEYS,
        promote_on_equal=confirm,
    )
    changed = changed_fields + changed_preferences

    # Gửi lên đúng những giá trị đang có thì không tạo phiên bản mới. Một bản ghi
    # lịch sử không có gì thay đổi chỉ làm loãng phần lịch sử thật.
    if not changed and not confirm:
        return profile, []

    version = expected_version if expected_version is not None else profile.get("version", 1)
    updated = await store.apply_changes(
        profile["session_id"],
        expected_version=version,
        fields=merged_fields,
        preferences=merged_preferences,
        history=store.history_entry(
            profile, changed_by, f"sửa: {', '.join(changed) or 'xác nhận'}"
        ),
        status=store.STATUS_CONFIRMED if confirm else None,
        confirmed_at=utc_now() if confirm else None,
    )
    if updated is None:
        raise HTTPException(
            status_code=409,
            detail="Hồ sơ vừa được cập nhật ở nơi khác. Vui lòng tải lại trang.",
        )
    return updated, changed


# --- Endpoint công khai ---


def _meta_payload() -> dict[str, Any]:
    """Danh mục cho biểu mẫu nhập hồ sơ.

    Một hàm cho cả hai router. Biểu mẫu của ứng viên và biểu mẫu của nhân viên
    ghi vào đúng những trường ấy, nên chúng phải nhìn thấy đúng một danh sách
    lựa chọn; hai bản chép tay sẽ lệch nhau ngay lần đầu thêm một mức tiếng Nhật.
    """
    meta = catalog.catalog_meta()
    return {
        "japanese_levels": meta["japanese_levels"],
        "education_levels": meta["education_levels"],
        "employer_types": meta["employer_types"],
        "regions": meta["regions"],
        "prefectures": meta["prefectures"],
        "genders": catalog.label_options(catalog.GENDER_LABELS),
        "required_fields": list(store.REQUIRED_FOR_CONFIRM),
    }


@public_router.get("/meta")
async def profile_meta():
    return _meta_payload()


@public_router.post("", status_code=201)
async def create_profile(payload: ProfileCreateRequest, http_request: Request):
    rate_limiter.check(f"profile-write:{client_ip(http_request)}", limit=20, window_seconds=60)

    fields, _ = store.merge_section(
        {}, _payload_values(payload.fields), source="user_confirmed", allowed=store.FIELD_KEYS
    )
    preferences, _ = store.merge_section(
        {},
        _payload_values(payload.preferences),
        source="user_confirmed",
        allowed=store.PREFERENCE_KEYS,
    )

    # Nhập tay là ứng viên tự khai nên coi như đã xác nhận ngay. Hồ sơ do bộ đọc
    # CV sinh ra thì phải chờ ứng viên xem lại, vì máy đọc có thể đọc sai.
    confirmed = payload.mode == "manual"
    document = {
        "code": new_code(PREFIX_PROFILE),
        "session_id": payload.session_id,
        "status": store.STATUS_CONFIRMED if confirmed else store.STATUS_EXTRACTED,
        "fields": fields,
        "preferences": preferences,
        "confirmed_at": utc_now() if confirmed else None,
    }
    try:
        profile = await store.create_profile(document)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=409, detail="Phiên này đã có hồ sơ. Hãy cập nhật hồ sơ hiện có."
        ) from exc
    return _decorate(store.public_view(profile))


@public_router.get("/{session_id}")
async def get_profile(session_id: str):
    return _decorate(store.public_view(await _load_or_404(session_id)))


@public_router.patch("/{session_id}")
async def patch_profile(
    session_id: str,
    payload: ProfilePatchRequest,
    http_request: Request,
):
    rate_limiter.check(f"profile-write:{client_ip(http_request)}", limit=20, window_seconds=60)
    profile = await _load_or_404(session_id)
    updated, _ = await _apply(
        profile,
        fields=_payload_values(payload.fields),
        preferences=_payload_values(payload.preferences),
        source="user_confirmed",
        changed_by=f"session:{session_id}",
        expected_version=payload.expected_version,
    )
    return _decorate(store.public_view(updated))


@public_router.post("/{session_id}/confirm")
async def confirm_profile(session_id: str, http_request: Request):
    """Ứng viên xác nhận hồ sơ đúng. Bộ đối chiếu chỉ chạy sau bước này."""
    rate_limiter.check(f"profile-write:{client_ip(http_request)}", limit=20, window_seconds=60)
    profile = await _load_or_404(session_id)

    missing = store.missing_required(profile)
    if missing:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Hồ sơ còn thiếu thông tin bắt buộc.",
                "missing": missing,
            },
        )
    if profile.get("status") == store.STATUS_CONFIRMED:
        return _decorate(store.public_view(profile))

    updated, _ = await _apply(
        profile,
        fields={},
        preferences={},
        source="user_confirmed",
        changed_by=f"session:{session_id}",
        expected_version=None,
        confirm=True,
    )
    return _decorate(store.public_view(updated))


# --- Endpoint quản trị ---


@router.get("")
async def profiles(
    status: str | None = Query(default=None, max_length=20),
    assigned_to: str | None = Query(default=None, max_length=150),
    lead_code: str | None = Query(default=None, max_length=30),
    limit: int = Query(default=100, ge=1, le=500),
    current_user=Depends(get_current_user),
):
    if not is_privileged(current_user):
        assigned_to = current_user["email"]
    query = store.build_query(status=status, assigned_to=assigned_to, lead_code=lead_code)
    return [_decorate(profile) for profile in await store.list_profiles(query, limit=limit)]


@router.get("/meta")
async def admin_profile_meta():
    """Danh mục cho biểu mẫu sửa hồ sơ bên quản trị.

    Phải khai trước `/{code}`: FastAPI khớp theo thứ tự khai báo, đặt sau thì
    `/profiles/meta` rơi vào `/{code}` và trả 404 "không tìm thấy hồ sơ".
    """
    return _meta_payload()


@router.get("/{code}")
async def profile_detail(code: str, current_user=Depends(get_current_user)):
    profile = await store.get_by_code(code)
    if profile is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ ứng viên.")
    if not can_access(profile, current_user):
        raise HTTPException(status_code=403, detail="Bạn không được xem hồ sơ này.")
    return _decorate(profile)


@router.patch("/{code}")
async def update_profile(
    code: str,
    payload: ProfilePatchRequest,
    http_request: Request,
    current_user=Depends(get_current_user),
):
    profile = await store.get_by_code(code)
    if profile is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ ứng viên.")
    if not can_access(profile, current_user):
        raise HTTPException(status_code=403, detail="Bạn không được sửa hồ sơ này.")

    updated, changed = await _apply(
        profile,
        fields=_payload_values(payload.fields),
        preferences=_payload_values(payload.preferences),
        source="staff",
        changed_by=current_user["email"],
        expected_version=payload.expected_version,
    )
    await audit_action(
        http_request,
        "candidate_profile.updated",
        actor=current_user,
        target_type="candidate_profile",
        target_id=code,
        details={"changed_fields": sorted(changed)},
    )
    return _decorate(updated)


@router.patch("/{code}/assignment")
async def assign_profile(
    code: str,
    payload: AssignmentRequest,
    http_request: Request,
    current_user=Depends(require_roles("admin", "manager")),
):
    ensure_can_assign(current_user, "Chỉ Quản lý và Quản trị viên được phân công hồ sơ.")
    assignee = await validate_assignee(payload.assigned_to)
    profile = await store.set_assignment(code, assignee)
    if profile is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ ứng viên.")
    await audit_action(
        http_request,
        "candidate_profile.assigned",
        actor=current_user,
        target_type="candidate_profile",
        target_id=code,
        details={"assigned_to": assignee},
    )
    return _decorate(profile)
