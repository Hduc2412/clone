"""API hồ sơ gốc ứng viên tải lên.

Hai router như bên hồ sơ ứng viên: một công khai cho ứng viên gửi file ngay trong
khung chat, một sau đăng nhập cho nhân viên xem và tải bản gốc về.

Bản gốc **không phát ra đường công khai**. Ứng viên gửi file lên thì thấy lại
thông tin đã bóc tách, không thấy đường tải file. Lý do: đường dẫn tới file chỉ
cần lộ một lần là lộ mãi, mà trong CV có số điện thoại, địa chỉ và ngày sinh của
một người thật. Tải bản gốc là việc của nhân viên đã đăng nhập.
"""
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Path,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse

from app.auth.security import get_current_user
from app.core.config import settings
from app.core.rate_limit import client_ip, rate_limiter
from app.db import candidate_documents as store
from app.db import candidate_profiles as profiles
from app.documents import reader, storage
from app.services import cv_service
from app.services.assignment import can_access, is_privileged
from app.services.audit_service import audit_action


public_router = APIRouter(prefix="/public/documents", tags=["Hồ sơ gốc (công khai)"])
router = APIRouter(
    prefix="/documents",
    tags=["Hồ sơ gốc"],
    dependencies=[Depends(get_current_user)],
)

SESSION_PATTERN = r"^[A-Za-z0-9_-]{8,64}$"

# Đọc CV vừa tốn tiền gọi mô hình vừa tốn chỗ trên đĩa, nên hạn mức chặt hơn hẳn
# các endpoint ghi khác. Năm lượt một phút vẫn thoải mái cho người dùng thật.
UPLOAD_LIMIT = 5
UPLOAD_WINDOW_SECONDS = 60


def _session(session_id: str = Path(pattern=SESSION_PATTERN)) -> str:
    return session_id


@public_router.post("/{session_id}", status_code=201)
async def upload_document(
    http_request: Request,
    session_id: str = Depends(_session),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Nhận một file CV cho phiên trò chuyện này."""
    rate_limiter.check(
        f"cv-upload:{client_ip(http_request)}",
        limit=UPLOAD_LIMIT,
        window_seconds=UPLOAD_WINDOW_SECONDS,
    )

    data = await file.read()
    try:
        result = await cv_service.ingest(
            data=data,
            filename=file.filename or "cv",
            content_type=file.content_type or "",
            session_id=session_id,
        )
    except cv_service.UploadRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "message": result.message,
        "document": result.document,
        # Phai qua decorate nhu moi endpoint ho so khac. Tra thieu `labels` o day
        # tung lam trang tu van trang xoa: giao dien doc profile.labels ngay sau khi
        # gui CV, va cung mot tai nguyen tra ve hai hinh dang la loi cua API.
        "profile": (
            profiles.decorate(profiles.public_view(result.profile))
            if result.profile
            else None
        ),
        "accepted_fields": result.accepted_fields,
        # Trả cả phần bị loại kèm lý do. Nhân viên nhìn vào là biết máy đã đọc ra
        # một giá trị nhưng không dám nhận, thay vì tưởng CV không có thông tin đó.
        "rejected": result.rejected,
    }


@public_router.get("/{session_id}")
async def list_session_documents(session_id: str = Depends(_session)) -> dict[str, Any]:
    items = await store.list_for_session(session_id)
    return {
        "items": [store.public_view(item) for item in items],
        "max_per_session": store.MAX_PER_SESSION,
        "accepted_types": reader.SUPPORTED_LABEL,
        "max_upload_mb": settings.max_upload_mb,
    }


@router.get("/stats")
async def document_stats(current_user=Depends(get_current_user)) -> dict[str, Any]:
    """Đếm tài liệu theo trạng thái, kèm riêng số file ảnh.

    Con số ảnh là thứ dùng để quyết định có làm phần đọc ảnh hay không. Hiện hệ
    thống nhận ảnh nhưng chưa đọc được chữ; nếu sau một thời gian chạy thật mà
    ảnh chiếm phần lớn, thì đó là bằng chứng để làm, chứ không phải phỏng đoán.
    """
    if not is_privileged(current_user):
        raise HTTPException(status_code=403, detail="Chỉ quản lý xem được thống kê này.")
    by_status = await store.count_by_status()
    return {
        "by_status": by_status,
        "images": await store.count_images(),
        "total": sum(by_status.values()),
    }


@router.get("")
async def list_documents(
    status: str | None = Query(default=None, max_length=20),
    limit: int = Query(default=100, ge=1, le=500),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Danh sách tài liệu, kể cả tài liệu chưa gắn vào hồ sơ nào."""
    if not is_privileged(current_user):
        raise HTTPException(status_code=403, detail="Chỉ quản lý xem được danh sách này.")
    items = await store.list_all(status=status, limit=limit)
    return {"items": [store.public_view(item) for item in items]}


@router.get("/profile/{profile_code}")
async def list_profile_documents(
    profile_code: str,
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    profile = await profiles.get_by_code(profile_code)
    if profile is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ.")
    if not can_access(profile, current_user):
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem hồ sơ này.")

    items = await store.list_for_profile(profile_code)
    return {"items": [store.public_view(item) for item in items]}


@router.get("/{code}/original")
async def download_original(
    code: str,
    request: Request,
    current_user=Depends(get_current_user),
):
    """Tải bản gốc. Ghi nhật ký vì đây là lúc dữ liệu cá nhân rời khỏi hệ thống."""
    document = await store.get_by_code(code)
    if document is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    await _ensure_can_read(document, current_user)

    path = storage.absolute_path(document["stored_path"])
    if not path.exists():
        raise HTTPException(
            status_code=410,
            detail="Bản gốc không còn trên máy chủ. Hãy đề nghị ứng viên gửi lại.",
        )

    await audit_action(
        request,
        action="document.download",
        actor=current_user,
        target_type="candidate_document",
        target_id=code,
        details={"profile_code": document.get("profile_code")},
    )
    return FileResponse(
        path,
        media_type=document.get("content_type") or "application/octet-stream",
        filename=document.get("filename") or code,
    )


@router.get("/{code}/text")
async def document_text(
    code: str,
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Toàn văn đã rút, để đối chiếu với đoạn dẫn của từng trường."""
    document = await store.get_by_code(code)
    if document is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    await _ensure_can_read(document, current_user)
    return {"code": code, "text": document.get("text", "")}


async def _ensure_can_read(document: dict[str, Any], current_user) -> None:
    """Tư vấn viên chỉ đọc được tài liệu của hồ sơ mình phụ trách.

    Dùng lại đúng quy tắc phân quyền của hồ sơ ứng viên thay vì viết một quy tắc
    thứ hai ở đây: hai quy tắc song song thì sớm muộn cũng lệch nhau, và lúc đó
    tài liệu sẽ rộng hơn hồ sơ chứa nó.
    """
    profile_code = document.get("profile_code")
    if not profile_code:
        # Tài liệu chưa gắn được vào hồ sơ nào (đọc hỏng, hoặc là bản scan). Chưa
        # có ai phụ trách thì chỉ quản lý được xem.
        if not is_privileged(current_user):
            raise HTTPException(status_code=403, detail="Bạn không có quyền xem tài liệu này.")
        return

    profile = await profiles.get_by_code(profile_code)
    if profile is None or not can_access(profile, current_user):
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem tài liệu này.")
