"""Quản lý danh mục khóa học tiếng Nhật.

Trước đường này, bảng khóa học chỉ vào được bằng `python -m scripts.seed_courses`:
thêm một khóa nghĩa là sửa một file Python rồi chạy lệnh trên máy chủ. Với một
bảng mà **nhân viên trung tâm là người biết nội dung**, đó là rào cản sai chỗ —
người biết thì không sửa được, người sửa được thì không biết.

## Vì sao khóa nháp không bao giờ lọt ra ngoài

`status` có hai giá trị, và `list_published()` là cửa duy nhất phần tư vấn dùng.
Một khóa đang khai dở với học phí để trống mà lọt vào lộ trình thì ứng viên nhận
một con đường học không có giá tiền — tệ hơn là không nhận gì, vì họ sẽ tưởng
mình đã biết đủ để quyết định.

## Vì sao xóa chỉ dành cho khóa nháp

Khóa đã công khai có thể đang nằm trong lộ trình mà ai đó vừa được tư vấn. Xóa nó
làm những lần tư vấn ấy mất căn cứ, mà không nơi nào ghi lại là đã mất. Muốn dừng
một khóa thì chuyển về nháp: nó rời khỏi phần tư vấn ngay, nhưng bản ghi còn đó để
đối chiếu về sau.
"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from pymongo.errors import DuplicateKeyError

from app.auth.security import get_current_user, require_roles
from app.db import courses as store
from app.learning import path as learning_path
from app.services.audit_service import audit_action


router = APIRouter(prefix="/khoa-hoc", tags=["Courses"])

CODE_PATTERN = r"^KH-\d{4,6}$"


class KhoaHocBody(BaseModel):
    """Trường của một khóa. `None` nghĩa là chưa biết, không phải bằng không.

    `tuition_vnd` và `package_total_vnd` để trống được, và đó là chủ ý: bảng này
    tồn tại để giữ con số **có nguồn**, nên thà thiếu một ô hơn là điền phỏng đoán.
    Phần tư vấn đã biết cách nói định tính khi thiếu số.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=200)
    level_from: str = Field(max_length=20)
    level_to: str = Field(max_length=20)
    months_min: int = Field(ge=1, le=60)
    months_max: int | None = Field(default=None, ge=1, le=60)
    tuition_vnd: int | None = Field(default=None, ge=0, le=10_000_000_000)
    package_total_vnd: int | None = Field(default=None, ge=0, le=10_000_000_000)
    format: str | None = Field(default=None, max_length=1000)
    curriculum: str | None = Field(default=None, max_length=500)
    status: str = Field(default=store.STATUS_DRAFT, max_length=20)
    source_url: str | None = Field(default=None, max_length=500)
    source_note: str | None = Field(default=None, max_length=2000)


class KhoaHocTaoMoiBody(KhoaHocBody):
    code: str = Field(pattern=CODE_PATTERN)


def _kiem_tra(entry: dict[str, Any]) -> None:
    """Dùng đúng bộ luật của tầng dữ liệu, đổi lỗi thành 422 kèm câu tiếng Việt.

    Không viết lại luật ở đây. Bộ nạp và đường này phải khắt khe bằng nhau, không
    thì cửa lỏng hơn sẽ nhận những dòng cửa kia từ chối.
    """
    try:
        store.kiem_tra(entry)
    except store.KhoaHocKhongHopLe as loi:
        raise HTTPException(status_code=422, detail=str(loi)) from loi


@router.get("/meta")
async def meta(current_user=Depends(get_current_user)) -> dict[str, Any]:
    """Danh mục cho biểu mẫu: trình độ và trạng thái. Một nguồn, không hai bản."""
    return {
        "levels": [
            {"value": muc, "label": learning_path.label(muc)}
            for muc in sorted(
                learning_path.JAPANESE_RANK, key=learning_path.JAPANESE_RANK.get
            )
        ],
        "statuses": [
            {"value": store.STATUS_PUBLISHED, "label": "Đang áp dụng"},
            {"value": store.STATUS_DRAFT, "label": "Nháp"},
        ],
    }


@router.get("")
async def danh_sach(
    status: str | None = Query(default=None, max_length=20),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    items = await store.list_courses(status=status)
    return {"items": items, "count": len(items)}


@router.get("/{code}")
async def chi_tiet(
    code: Annotated[str, Path(pattern=CODE_PATTERN)],
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    khoa = await store.get_course(code)
    if khoa is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học này.")
    return khoa


@router.post("", status_code=201)
async def tao_moi(
    payload: KhoaHocTaoMoiBody,
    http_request: Request,
    current_user=Depends(require_roles("admin", "manager")),
) -> dict[str, Any]:
    entry = payload.model_dump()
    _kiem_tra(entry)
    try:
        khoa = await store.create_course(entry)
    except DuplicateKeyError as loi:
        raise HTTPException(
            status_code=409, detail=f"Mã khóa {payload.code} đã có trong bảng."
        ) from loi
    await audit_action(
        http_request,
        "course.created",
        actor=current_user,
        target_type="course",
        target_id=payload.code,
        details={"status": entry["status"]},
    )
    return khoa


@router.patch("/{code}")
async def sua(
    code: Annotated[str, Path(pattern=CODE_PATTERN)],
    payload: KhoaHocBody,
    http_request: Request,
    current_user=Depends(require_roles("admin", "manager")),
) -> dict[str, Any]:
    hien_co = await store.get_course(code)
    if hien_co is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học này.")

    # Kiểm trên bản ghi SAU khi trộn, không kiểm riêng phần gửi lên. Sửa một ô có
    # thể làm cả dòng sai luật — đổi `level_to` xuống dưới `level_from` chẳng hạn —
    # và kiểm từng ô rời thì không bắt được.
    entry = {**hien_co, **payload.model_dump(), "code": code}
    _kiem_tra(entry)

    khoa = await store.update_course(code, payload.model_dump())
    if khoa is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học này.")
    await audit_action(
        http_request,
        "course.updated",
        actor=current_user,
        target_type="course",
        target_id=code,
        details={"status": entry["status"]},
    )
    return khoa


@router.delete("/{code}")
async def xoa(
    code: Annotated[str, Path(pattern=CODE_PATTERN)],
    http_request: Request,
    current_user=Depends(require_roles("admin", "manager")),
) -> dict[str, Any]:
    """Chỉ xóa được khóa nháp. Khóa đã áp dụng thì chuyển về nháp.

    Khóa đã công khai có thể đang nằm trong lộ trình mà ai đó vừa được tư vấn. Xóa
    nó làm những lần tư vấn ấy mất căn cứ, và không nơi nào ghi lại là đã mất.
    """
    hien_co = await store.get_course(code)
    if hien_co is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học này.")
    if hien_co.get("status") == store.STATUS_PUBLISHED:
        raise HTTPException(
            status_code=409,
            detail="Khóa đang áp dụng thì không xóa được — nó có thể đang nằm trong "
            "lộ trình đã tư vấn cho ứng viên. Chuyển về nháp để nó rời khỏi phần "
            "tư vấn mà bản ghi vẫn còn để đối chiếu.",
        )
    await store.delete_course(code)
    await audit_action(
        http_request,
        "course.deleted",
        actor=current_user,
        target_type="course",
        target_id=code,
    )
    return {"code": code, "deleted": True}
