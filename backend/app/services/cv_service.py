"""Luồng nhận CV: từ file tải lên tới hồ sơ có dữ liệu.

Năm việc, theo đúng thứ tự, và **ghi bản ghi trước khi bóc tách**:

1. Kiểm tra file — dung lượng, định dạng thật.
2. Rút chữ ra khỏi file.
3. Lưu bản gốc xuống đĩa và tạo bản ghi tài liệu.
4. Nhờ mô hình bóc tách thành trường, lọc theo đoạn dẫn.
5. Gộp vào hồ sơ ứng viên với nguồn `cv`.

Bước 3 đứng trước bước 4 là có chủ ý. Bóc tách là bước dễ hỏng nhất: mạng chập,
hạn mức gọi mô hình hết, file scan không đọc được. Nếu chỉ ghi bản ghi khi bóc
tách thành công thì mỗi lần hỏng là **mất luôn dấu vết** — ứng viên đã gửi file,
hệ thống không còn gì để nói là đã nhận. Ghi trước thì hỏng ở đâu cũng còn bản
ghi mang trạng thái hỏng, nhân viên nhìn thấy và xử lý tay được.

## Hồ sơ sinh từ CV luôn ở trạng thái chờ xác nhận

Không bao giờ đặt thẳng thành `confirmed`. Máy đọc có thể đọc sai, và bộ đối
chiếu chỉ chạy sau khi ứng viên xác nhận — chốt chặn đó (spec bước 3) mất hết ý
nghĩa nếu bộ đọc CV tự cho mình quyền xác nhận hộ.
"""
from dataclasses import dataclass
from typing import Any

from fastapi.concurrency import run_in_threadpool
from pymongo.errors import DuplicateKeyError

from app.core.codes import PREFIX_DOCUMENT, PREFIX_PROFILE, new_code
from app.core.config import settings
from app.db import candidate_documents as documents
from app.db import candidate_profiles as profiles
from app.documents import extractor, reader, storage


SOURCE_CV = "cv"

# Hai câu này nói với ứng viên rằng file **đã tới nơi** rồi mới nói là chưa đọc
# được. Thứ tự đó có chủ ý: người vừa gửi xong sợ nhất là file rơi đi đâu mất.
_UNREADABLE_SCAN = (
    "Mình đã nhận file nhưng đây là bản scan nên chưa đọc được chữ. "
    "Bạn gửi bản có chữ hoặc tự khai nhanh vài thông tin giúp mình nhé."
)
_UNREADABLE_IMAGE = (
    "Mình đã nhận ảnh và lưu lại rồi, nhưng hiện chưa đọc được chữ trong ảnh. "
    "Bạn gửi thêm bản PDF hoặc Word, hoặc khai nhanh vài thông tin giúp mình nhé."
)


class UploadRejected(Exception):
    """File không nhận được. Thông điệp viết cho ứng viên đọc, không phải cho log."""


@dataclass
class IngestResult:
    document: dict[str, Any]
    profile: dict[str, Any] | None
    accepted_fields: list[str]
    rejected: dict[str, str]
    message: str


async def ingest(
    *,
    data: bytes,
    filename: str,
    content_type: str,
    session_id: str,
) -> IngestResult:
    if not data:
        raise UploadRejected("File rỗng.")
    if len(data) > settings.max_upload_bytes:
        raise UploadRejected(
            f"File vượt quá {settings.max_upload_mb}MB. Bạn gửi lại bản nhẹ hơn nhé."
        )

    if await documents.count_in_session(session_id) >= documents.MAX_PER_SESSION:
        raise UploadRejected(
            f"Mỗi cuộc trò chuyện chỉ nhận tối đa {documents.MAX_PER_SESSION} file. "
            "Bạn liên hệ nhân viên để gửi thêm nhé."
        )

    try:
        kind, read_result = await run_in_threadpool(reader.read, data, content_type, filename)
    except reader.UnsupportedDocument as exc:
        raise UploadRejected(str(exc)) from exc
    except Exception as exc:  # file đúng định dạng nhưng hỏng bên trong
        raise UploadRejected(
            f"Không mở được file. Bạn kiểm tra lại giúp mình ({exc.__class__.__name__})."
        ) from exc

    fingerprint = storage.digest(data)
    existing = await documents.find_in_session(session_id, fingerprint)
    if existing is not None and existing.get("status") == documents.STATUS_EXTRACTED:
        # Gửi lại đúng file cũ thì không lưu thêm bản sao, cũng không gọi lại mô
        # hình. Bấm nhầm hai lần là chuyện thường; tính phí hai lần thì không.
        #
        # Chỉ chặn khi lần trước **đã đọc xong**. Lần trước hỏng mà vẫn chặn thì
        # ứng viên gửi lại bao nhiêu lần cũng nhận đúng thông báo hỏng cũ, không
        # bao giờ thoát ra được — trong khi phần lớn lỗi ở đây chỉ là nhất thời.
        return IngestResult(
            document=documents.public_view(existing),
            profile=await profiles.get_by_session(session_id),
            accepted_fields=list(existing.get("extracted_fields") or []),
            rejected=dict(existing.get("rejected") or {}),
            message="File này đã được tiếp nhận trước đó.",
        )

    code = new_code(PREFIX_DOCUMENT)
    stored_path = await run_in_threadpool(
        storage.save, data, code, reader.SUPPORTED_TYPES[kind]
    )
    document = await documents.create(
        {
            "code": code,
            "session_id": session_id,
            "filename": filename[:200],
            "content_type": kind,
            "size_bytes": len(data),
            "sha256": fingerprint,
            "stored_path": stored_path,
            "text": read_result.text,
            "page_count": read_result.page_count,
        }
    )

    if read_result.needs_model_ocr:
        message = _UNREADABLE_IMAGE if kind in reader.IMAGE_TYPES else _UNREADABLE_SCAN
        await documents.mark_failed(code, documents.STATUS_UNREADABLE, message)
        return IngestResult(
            document=documents.public_view({**document, "status": documents.STATUS_UNREADABLE}),
            profile=await profiles.get_by_session(session_id),
            accepted_fields=[],
            rejected={},
            message=message,
        )

    try:
        extraction = await run_in_threadpool(extractor.extract_fields, read_result.text)
    except extractor.ExtractionFailed as exc:
        message = (
            "Mình đã nhận file nhưng chưa đọc được nội dung lúc này. "
            "Nhân viên sẽ xem giúp bạn."
        )
        await documents.mark_failed(code, documents.STATUS_FAILED, f"{exc}")
        return IngestResult(
            document=documents.public_view({**document, "status": documents.STATUS_FAILED}),
            profile=await profiles.get_by_session(session_id),
            accepted_fields=[],
            rejected={},
            message=message,
        )

    profile = await _merge_into_profile(session_id, extraction)
    await profiles.attach_document(profile["code"], code)
    await documents.mark_extracted(
        code,
        profile_code=profile["code"],
        extracted_fields=sorted(extraction.fields),
        rejected=extraction.rejected,
    )

    return IngestResult(
        document=documents.public_view(
            {**document, "status": documents.STATUS_EXTRACTED, "profile_code": profile["code"]}
        ),
        profile=profile,
        accepted_fields=sorted(extraction.fields),
        rejected=extraction.rejected,
        message=_summary(extraction),
    )


async def _merge_into_profile(
    session_id: str,
    extraction: extractor.Extraction,
) -> dict[str, Any]:
    profile = await profiles.get_by_session(session_id)
    if profile is None:
        profile = await _create_profile(session_id, extraction)
        if profile is not None:
            return profile
        # Hai file gửi gần như cùng lúc: bản kia vừa tạo hồ sơ trước. Đọc lại rồi
        # đi tiếp theo nhánh gộp, thay vì báo lỗi cho ứng viên.
        profile = await profiles.get_by_session(session_id)
        if profile is None:
            raise RuntimeError("Không tạo được hồ sơ cho phiên này.")

    merged, changed = profiles.merge_section(
        profile.get("fields"),
        extraction.fields,
        source=SOURCE_CV,
        allowed=profiles.FIELD_KEYS,
        evidence=extraction.evidence,
    )
    if not changed:
        return profile

    updated = await profiles.apply_changes(
        session_id,
        expected_version=profile.get("version", 1),
        fields=merged,
        preferences=profile.get("preferences") or {},
        history=profiles.history_entry(
            profile, "cv", f"đọc CV: {', '.join(changed)}"
        ),
    )
    # `None` nghĩa là số phiên bản đã đổi giữa chừng. Trả bản hiện tại chứ không
    # ném lỗi: ứng viên vừa sửa tay xong, mà sửa tay thì ưu tiên cao hơn bản đọc
    # từ CV — mất lượt gộp này không làm hỏng gì.
    return updated or await profiles.get_by_session(session_id) or profile


async def _create_profile(
    session_id: str,
    extraction: extractor.Extraction,
) -> dict[str, Any] | None:
    fields, _ = profiles.merge_section(
        {},
        extraction.fields,
        source=SOURCE_CV,
        allowed=profiles.FIELD_KEYS,
        evidence=extraction.evidence,
    )
    try:
        return await profiles.create_profile(
            {
                "code": new_code(PREFIX_PROFILE),
                "session_id": session_id,
                "status": profiles.STATUS_EXTRACTED,
                "fields": fields,
                "preferences": {},
            }
        )
    except DuplicateKeyError:
        return None


def _summary(extraction: extractor.Extraction) -> str:
    if not extraction.fields:
        return (
            "Mình đã đọc file nhưng chưa rút được thông tin nào chắc chắn. "
            "Bạn khai nhanh giúp mình vài mục nhé."
        )
    labels = {
        "full_name": "họ tên",
        "birth_year": "năm sinh",
        "gender": "giới tính",
        "education_level": "bằng cấp",
        "major": "chuyên ngành",
        "japanese_level": "trình độ tiếng Nhật",
        "experience_years": "số năm kinh nghiệm",
        "care_experience": "kinh nghiệm chăm sóc",
        "phone": "số điện thoại",
    }
    named = ", ".join(labels.get(key, key) for key in sorted(extraction.fields))
    return f"Mình đã đọc được: {named}. Bạn xem lại giúp mình có đúng không nhé."
