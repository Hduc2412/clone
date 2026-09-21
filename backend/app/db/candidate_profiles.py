"""Hồ sơ ứng viên.

Một hồ sơ trên một phiên làm việc. Hồ sơ là thứ bộ đối chiếu đọc vào, nên hình
dạng của nó quyết định bộ đối chiếu có công bằng hay không.

## Ba quy tắc nằm ngay trong hình dạng dữ liệu

**Tách `fields` và `preferences`.** `fields` là năng lực kiểm chứng được trên giấy
tờ, dùng cho điều kiện bắt buộc. `preferences` là nguyện vọng do ứng viên nói,
chỉ dùng để xếp hạng. Bộ đối chiếu đọc hai mục này ở hai hàm khác nhau, nên một
nguyện vọng không bao giờ loại được ai — kể cả khi có người sửa nhầm code sau này.

**Trường vắng mặt nghĩa là chưa rõ.** Không ghi `{"value": null}`. Phải phân biệt
được "chưa hỏi" với "đã hỏi và ứng viên chưa học tiếng Nhật"; cái sau là
`japanese_level = "chua_hoc"`, một câu trả lời đã có.

**Mỗi trường mang nguồn của nó.** Thứ ứng viên tự xác nhận không bị bản đọc CV
ghi đè. Nhờ vậy đọc CV lần hai không xóa mất thứ ứng viên đã sửa tay.
"""
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.db.common import get_db, now, strip_id
from app.matching.catalog import SOURCE_PRIORITY


COLLECTION = "candidate_profiles"

# Giữ tối đa năm bản trước. Đủ để lần lại một chuỗi sửa gần đây mà không làm bản
# ghi phình vô hạn theo mỗi lần ứng viên gõ lại một ô.
HISTORY_LIMIT = 5

FIELD_KEYS: frozenset[str] = frozenset(
    {
        "full_name",
        "birth_year",
        "gender",
        "education_level",
        "major",
        "japanese_level",
        "experience_years",
        "care_experience",
        "phone",
    }
)

PREFERENCE_KEYS: frozenset[str] = frozenset(
    {
        "desired_prefecture",
        "desired_region_group",
        "desired_employer_type",
        "salary_expectation_jpy",
        "budget_vnd",
        "reason",
        "notes",
    }
)

# Hai trường tối thiểu để hồ sơ có ý nghĩa với bộ đối chiếu. Trình độ tiếng Nhật
# là tiêu chí quyết định nhất, và trả lời "chưa học" cũng tính là đã khai.
REQUIRED_FOR_CONFIRM: tuple[str, ...] = ("full_name", "japanese_level")

DEFAULT_CONFIDENCE: dict[str, float] = {
    "staff": 1.0,
    "user_confirmed": 1.0,
    "cv": 0.9,
    "chat": 0.7,
}

STATUS_EXTRACTED = "extracted"
STATUS_CONFIRMED = "confirmed"


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db[COLLECTION].create_index("code", unique=True)
    await db[COLLECTION].create_index("session_id", unique=True)
    await db[COLLECTION].create_index([("status", ASCENDING), ("updated_at", DESCENDING)])
    await db[COLLECTION].create_index([("assigned_to", ASCENDING), ("updated_at", DESCENDING)])
    await db[COLLECTION].create_index("lead_code")
    await db[COLLECTION].create_index("phone_normalized")


# --- Hàm thuần, kiểm thử được mà không cần database ---


def cell(value: Any, source: str, evidence: str | None = None) -> dict[str, Any]:
    return {
        "value": value,
        "source": source,
        "confidence": DEFAULT_CONFIDENCE.get(source, 0.5),
        "evidence": evidence,
    }


def merge_section(
    existing: dict[str, Any] | None,
    incoming: dict[str, Any],
    *,
    source: str,
    allowed: frozenset[str],
    evidence: dict[str, str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Gộp giá trị mới vào hồ sơ theo thứ tự ưu tiên nguồn.

    Trả về hồ sơ đã gộp và danh sách khóa thật sự thay đổi. Danh sách đó dùng để
    quyết định có tăng số phiên bản hay không: gửi lên đúng những giá trị đang có
    thì không nên đẻ ra một phiên bản mới và một bản lưu lịch sử vô nghĩa.
    """
    merged = dict(existing or {})
    changed: list[str] = []
    incoming_priority = SOURCE_PRIORITY.get(source, 0)

    for key, value in incoming.items():
        if key not in allowed:
            raise ValueError(f"Trường không hợp lệ: {key}")
        if value is None or value == "":
            continue

        current = merged.get(key)
        if current is not None:
            current_priority = SOURCE_PRIORITY.get(current.get("source", ""), 0)
            # Nguồn yếu hơn không được ghi đè nguồn mạnh hơn. Cùng nguồn thì giá
            # trị mới thắng, vì đó là người dùng tự sửa lại chính mình.
            if incoming_priority < current_priority:
                continue
            if current.get("value") == value and incoming_priority == current_priority:
                continue

        merged[key] = cell(value, source, (evidence or {}).get(key))
        changed.append(key)

    return merged, changed


def missing_required(profile: dict[str, Any]) -> list[str]:
    fields = profile.get("fields") or {}
    return [
        key
        for key in REQUIRED_FOR_CONFIRM
        if not (fields.get(key) or {}).get("value")
    ]


def decorate(profile: dict[str, Any]) -> dict[str, Any]:
    """Gắn nhãn tiếng Việt để nơi hiển thị không phải giữ bản sao bảng danh mục.

    Đặt ở tầng dữ liệu chứ không ở tầng API, vì phiếu tóm tắt tư vấn cũng cần
    đúng những nhãn này. Để mỗi nơi tự tra bảng thì sớm muộn phiếu và màn hình sẽ
    gọi cùng một thứ bằng hai cái tên khác nhau.
    """
    from app.matching import catalog

    fields = profile.get("fields") or {}
    preferences = profile.get("preferences") or {}

    def label(section: dict[str, Any], key: str, table: dict[str, str]) -> str | None:
        value = (section.get(key) or {}).get("value")
        return table.get(value) if value else None

    profile["labels"] = {
        "status": catalog.PROFILE_STATUS_LABELS.get(profile.get("status", "")),
        "japanese_level": label(fields, "japanese_level", catalog.JAPANESE_LEVEL_LABELS),
        "education_level": label(fields, "education_level", catalog.EDUCATION_LABELS),
        "gender": label(fields, "gender", catalog.GENDER_LABELS),
        "desired_employer_type": label(
            preferences, "desired_employer_type", catalog.EMPLOYER_TYPE_LABELS
        ),
        "desired_region_group": label(
            preferences, "desired_region_group", catalog.REGION_LABELS
        ),
    }
    profile["missing_required"] = missing_required(profile)
    profile["consultation_profile"] = consultation_view(profile)
    return profile


def consultation_view(profile: dict[str, Any]) -> dict[str, Any]:
    """Logical profile embedded in the same aggregate, no dual-write drift."""
    return {
        **(profile.get("consultation") or {}),
        "candidate_code": profile.get("code"),
        "version": profile.get("version", 1),
        "preferences": profile.get("preferences") or {},
    }


def public_view(profile: dict[str, Any]) -> dict[str, Any]:
    """Bản dành cho ứng viên. Ẩn lịch sử và thông tin phân công nội bộ."""
    hidden = {"history", "assigned_to", "lead_code", "phone_normalized", "_id"}
    return {key: value for key, value in profile.items() if key not in hidden}


def history_entry(profile: dict[str, Any], changed_by: str, note: str) -> dict[str, Any]:
    return {
        "version": profile.get("version", 1),
        "status": profile.get("status"),
        "fields": profile.get("fields", {}),
        "preferences": profile.get("preferences", {}),
        "consultation": profile.get("consultation", {}),
        "changed_at": now(),
        "changed_by": changed_by,
        "note": note,
    }


# --- Truy cập database ---


async def create_profile(document: dict[str, Any]) -> dict[str, Any]:
    timestamp = now()
    full = {
        "status": STATUS_EXTRACTED,
        "version": 1,
        "fields": {},
        "preferences": {},
        "history": [],
        "assigned_to": None,
        "lead_code": None,
        "source_document_codes": [],
        "confirmed_at": None,
        **document,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    await get_db()[COLLECTION].insert_one(full)
    return strip_id(full)


async def get_by_session(session_id: str) -> dict[str, Any] | None:
    return await get_db()[COLLECTION].find_one({"session_id": session_id}, {"_id": 0})


async def get_by_code(code: str) -> dict[str, Any] | None:
    return await get_db()[COLLECTION].find_one({"code": code}, {"_id": 0})


def build_query(
    *,
    status: str | None = None,
    assigned_to: str | None = None,
    session_id: str | None = None,
    lead_code: str | None = None,
) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if status:
        query["status"] = status
    if assigned_to:
        query["assigned_to"] = assigned_to.strip().lower()
    if session_id:
        query["session_id"] = session_id
    if lead_code:
        query["lead_code"] = lead_code
    return query


async def list_profiles(query: dict[str, Any], *, limit: int = 100) -> list[dict[str, Any]]:
    cursor = (
        get_db()[COLLECTION]
        .find(query, {"_id": 0, "history": 0})
        .sort("updated_at", DESCENDING)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def apply_changes(
    session_id: str,
    *,
    expected_version: int,
    fields: dict[str, Any],
    preferences: dict[str, Any],
    history: dict[str, Any],
    status: str | None = None,
    confirmed_at: Any = None,
    consultation: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Ghi bản mới kèm khóa theo số phiên bản.

    Điều kiện `version: expected_version` là khóa lạc quan. Ứng viên mở hai tab và
    sửa cùng lúc thì tab sau nhận `None` và được yêu cầu tải lại, thay vì ghi đè
    âm thầm lên thay đổi của tab trước.
    """
    changes: dict[str, Any] = {
        "fields": fields,
        "preferences": preferences,
        "version": expected_version + 1,
        "updated_at": now(),
    }
    if status:
        changes["status"] = status
        if status == STATUS_EXTRACTED:
            changes["confirmed_at"] = None
    if consultation is not None:
        changes["consultation"] = consultation
    if confirmed_at is not None:
        changes["confirmed_at"] = confirmed_at

    return await get_db()[COLLECTION].find_one_and_update(
        {"session_id": session_id, "version": expected_version},
        {
            "$set": changes,
            # `$slice` âm giữ lại N phần tử cuối, tức những bản mới nhất.
            "$push": {"history": {"$each": [history], "$slice": -HISTORY_LIMIT}},
        },
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )


async def set_assignment(code: str, assigned_to: str | None) -> dict[str, Any] | None:
    return await get_db()[COLLECTION].find_one_and_update(
        {"code": code},
        {"$set": {"assigned_to": assigned_to, "updated_at": now()}},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )


async def attach_document(code: str, document_code: str) -> None:
    """Ghi nhận hồ sơ này có dữ liệu đến từ file nào.

    `$addToSet` thay vì `$push`: tải lại đúng file cũ rồi bóc tách lần nữa là
    chuyện bình thường, và khi đó danh sách nguồn không nên có hai mục giống hệt.
    """
    await get_db()[COLLECTION].update_one(
        {"code": code},
        {
            "$addToSet": {"source_document_codes": document_code},
            "$set": {"updated_at": now()},
        },
    )


async def attach_lead(code: str, lead_code: str, phone_normalized: str) -> None:
    await get_db()[COLLECTION].update_one(
        {"code": code},
        {
            "$set": {
                "lead_code": lead_code,
                "phone_normalized": phone_normalized,
                "updated_at": now(),
            }
        },
    )


async def count_profiles(query: dict[str, Any] | None = None) -> int:
    return await get_db()[COLLECTION].count_documents(query or {})
