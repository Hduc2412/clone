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


# --- Mức xác thực của trình độ tiếng Nhật ---
#
# Trình độ tiếng Nhật là tiêu chí loại người nhiều nhất trong bảy điều kiện bắt
# buộc, nên nó là chỗ duy nhất đáng ghi lại **đã tin vào căn cứ nào**.
#
# Cố ý KHÔNG nhận ảnh chụp bằng. Nhìn ảnh không phân biệt được bằng thật với bằng
# giả, còn ngồi đối diện thì hỏi vài câu tiếng Nhật là biết ngay — nên việc xác
# thực là của buổi gặp giữa người với người, và hệ thống chỉ ghi lại kết quả cùng
# cách đối chứng. Thêm một loại giấy tờ cá nhân vào kho là thêm một thứ để mất.
XAC_THUC_TRUNG_TAM = "center"      # học tại chính trung tâm — chắc nhất, khỏi đối chứng
XAC_THUC_DOI_CHUNG = "verified"    # đã gặp và đối chứng được
XAC_THUC_TU_KHAI = "claimed"       # khách tự khai, chưa ai kiểm

# Cách đối chứng tại buổi gặp.
CHUNG_CU_BAN_GOC = "ban_goc"                  # ứng viên cầm bằng gốc
CHUNG_CU_TRA_CUU = "tra_cuu_truc_tuyen"       # tra kết quả trên trang chính thức
CHUNG_CU_KHONG_CO = "khong_xuat_trinh"        # không xuất trình được gì
CAC_CHUNG_CU = (CHUNG_CU_BAN_GOC, CHUNG_CU_TRA_CUU, CHUNG_CU_KHONG_CO)


def muc_xac_thuc(chung_cu: str) -> str:
    """Cách đối chứng nào cho ra mức xác thực nào.

    Điểm quan trọng: **không xuất trình được gì thì trình độ vẫn là tự khai.**
    Không có luật này thì nhân viên bấm hết biểu mẫu là mọi hồ sơ đều thành "đã
    xác thực", kể cả hồ sơ không có một mẩu căn cứ nào — và nhãn ấy đi theo ứng
    viên tới tận buổi phỏng vấn với công ty Nhật, nơi nó bị lật lại.
    """
    return XAC_THUC_TU_KHAI if chung_cu == CHUNG_CU_KHONG_CO else XAC_THUC_DOI_CHUNG


def danh_dau_xac_thuc(
    fields: dict[str, Any], *, chung_cu: str, nguoi_ghi: str
) -> dict[str, Any]:
    """Gắn nhãn xác thực lên ô `japanese_level`, trả về bản `fields` mới.

    Chỉ gắn lên đúng ô ấy. Các ô khác không có khái niệm "đối chứng" — không ai
    đòi ứng viên chứng minh năm sinh bằng bản gốc trong một buổi sơ tuyển.
    """
    o = (fields or {}).get("japanese_level")
    if not o:
        return dict(fields or {})
    moi = dict(fields)
    moi["japanese_level"] = {
        **o,
        "verification": muc_xac_thuc(chung_cu),
        "evidence_type": chung_cu,
        "verified_by": nguoi_ghi,
        "verified_at": now(),
    }
    return moi


def merge_section(
    existing: dict[str, Any] | None,
    incoming: dict[str, Any],
    *,
    source: str,
    allowed: frozenset[str],
    evidence: dict[str, str] | None = None,
    promote_on_equal: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    """Gộp giá trị mới vào hồ sơ theo thứ tự ưu tiên nguồn.

    Trả về hồ sơ đã gộp và danh sách khóa thật sự thay đổi. Danh sách đó dùng để
    quyết định có tăng số phiên bản hay không: gửi lên đúng những giá trị đang có
    thì không nên đẻ ra một phiên bản mới và một bản lưu lịch sử vô nghĩa.

    `promote_on_equal` quyết định điều gì xảy ra khi một nguồn **mạnh hơn** gửi
    lại **đúng giá trị đang có**:

    - Mặc định `False` — giữ nguyên ô cũ, cả nguồn lẫn đoạn trích. Đây là điều
      biểu mẫu sửa hồ sơ cần: nhân viên đổi một ô rồi lưu thì form gửi lại toàn
      bộ các ô; nếu "staff gửi lại giá trị cũ" bị coi là thay đổi, mọi trường
      ứng viên tự xác nhận và mọi trích dẫn nguyên văn từ CV biến thành "nhân
      viên nhập" — đúng thứ mà dòng chữ trên form hứa sẽ giữ nguyên.
    - `True` — nâng nguồn của ô lên nguồn mới, **nhưng giữ lại đoạn trích cũ**.
      Đây là điều bước xác nhận cần: ứng viên bấm xác nhận thì một giá trị nghe
      được trong hội thoại (`chat`) trở thành `user_confirmed`, mà câu nói gốc
      vẫn còn làm căn cứ.
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
        carried_evidence = (evidence or {}).get(key)
        if current is not None:
            current_priority = SOURCE_PRIORITY.get(current.get("source", ""), 0)
            # Nguồn yếu hơn không được ghi đè nguồn mạnh hơn. Cùng nguồn thì giá
            # trị mới thắng, vì đó là người dùng tự sửa lại chính mình.
            if incoming_priority < current_priority:
                continue
            if current.get("value") == value:
                # Cùng nguồn và cùng giá trị: không có gì để làm. Nguồn mạnh hơn
                # mà không được phép nâng: cũng giữ nguyên.
                if incoming_priority == current_priority or not promote_on_equal:
                    continue
                # Nâng nguồn nhưng đừng vứt đoạn trích đang có.
                carried_evidence = carried_evidence or current.get("evidence")

        merged[key] = cell(value, source, carried_evidence)
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


def _chi_so(so: Any) -> str | None:
    """Số điện thoại ở dạng chuẩn để tra ngược, hoặc `None` nếu không đọc được.

    Không ném lỗi: đây là việc phụ trợ cho tra cứu, không được phép làm hỏng một
    lần lưu hồ sơ vốn đã hợp lệ. Số sai định dạng thì đơn giản là không tra
    ngược được, chứ không mất luôn cả hồ sơ.
    """
    from app.core.phone import normalize_vietnamese_phone

    try:
        return normalize_vietnamese_phone(str(so))
    except ValueError:
        return None


async def tim_ho_so_trung_so(
    phone_normalized: str, *, tru_ma: str | None = None
) -> list[dict[str, Any]]:
    """Những hồ sơ khác cùng số điện thoại — để nhân viên đối chiếu, không tự gộp.

    Trả về bản rút gọn: nhân viên chỉ cần biết *có* hồ sơ khác và nó trông thế
    nào để quyết định có phải cùng một người hay không.
    """
    if not phone_normalized:
        return []
    truy_van: dict[str, Any] = {"phone_normalized": phone_normalized}
    if tru_ma:
        truy_van["code"] = {"$ne": tru_ma}
    cursor = get_db()[COLLECTION].find(
        truy_van,
        {"_id": 0, "code": 1, "status": 1, "created_at": 1, "fields.full_name": 1},
    ).sort("created_at", -1).limit(10)
    return [row async for row in cursor]


async def apply_changes(
    session_id: str,
    *,
    expected_version: int,
    fields: dict[str, Any] | None,
    preferences: dict[str, Any] | None,
    history: dict[str, Any],
    status: str | None = None,
    confirmed_at: Any = None,
    consultation: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Ghi bản mới kèm khóa theo số phiên bản.

    Điều kiện `version: expected_version` là khóa lạc quan. Ứng viên mở hai tab và
    sửa cùng lúc thì tab sau nhận `None` và được yêu cầu tải lại, thay vì ghi đè
    âm thầm lên thay đổi của tab trước.

    ## `None` nghĩa là "giữ nguyên phần này", không phải "xoá phần này"

    Bản trước ghi thẳng giá trị nhận được, nên một lời gọi chỉ đổi `fields` mà
    truyền `preferences=None` sẽ **ghi `null` vào database** và xoá sạch nguyện
    vọng của ứng viên.

    Hỏng còn tệ hơn việc mất dữ liệu: `api/profiles._apply` đọc bằng
    `profile.get("preferences", {})`, mà `.get` chỉ trả mặc định khi **thiếu
    khóa** — khóa có mặt với giá trị `None` thì nó trả `None`, rồi `None.items()`
    ném `AttributeError`. Hệ quả là bước xác nhận hồ sơ trả 500, và giao diện
    hiện "Không kết nối được máy chủ" — một câu chỉ sai hướng hoàn toàn.

    Gặp thật ngày 05/10 trên luồng gửi CV: `api/agent._ghi_mot_truong` xác nhận
    một trường thuộc `fields` và truyền `preferences=None`. Hồ sơ hỏng ngay từ
    lúc ấy, nhưng chỉ nổ ở một bước khác, sau vài cú bấm nữa.

    Nên bất biến **"hồ sơ luôn có cả hai phần, có thể rỗng"** được canh ở đây —
    tại cửa ghi, nơi mọi người gọi đều đi qua — thay vì bắt từng người gọi nhớ.
    """
    changes: dict[str, Any] = {
        "version": expected_version + 1,
        "updated_at": now(),
    }
    if fields is not None:
        changes["fields"] = fields
    if preferences is not None:
        changes["preferences"] = preferences
    if status:
        changes["status"] = status
        if status == STATUS_EXTRACTED:
            changes["confirmed_at"] = None
    if consultation is not None:
        changes["consultation"] = consultation
    if confirmed_at is not None:
        changes["confirmed_at"] = confirmed_at

    # Ghi chỉ mục số điện thoại ngay khi biết số, đừng đợi tới lúc đăng ký đơn.
    #
    # Trước 22/09/2026 `phone_normalized` chỉ được đặt trong `attach_lead`, tức
    # chỉ khi ứng viên đã chọn đơn và bấm đăng ký. Đo trên dữ liệu thật:
    # **5 trên 88 hồ sơ** có nó. Tám mươi ba hồ sơ còn lại có số điện thoại nằm
    # trong `fields.phone` nhưng không tra ngược được, nên cùng một người quay
    # lại là thành một hồ sơ mới toanh, không ai biết.
    #
    # Chỉ ghi chỉ mục, **không tự gộp hồ sơ**: hai anh em dùng chung một số, hay
    # một người khai nhầm một chữ số, mà gộp tự động thì hai người dính vào nhau
    # và gỡ ra rất khó. Việc gộp để nhân viên quyết sau khi gọi điện xác minh.
    so_dien_thoai = ((fields or {}).get("phone") or {}).get("value")
    if so_dien_thoai:
        changes["phone_normalized"] = _chi_so(so_dien_thoai)

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


async def get_by_lead(lead_code: str) -> dict[str, Any] | None:
    """Hồ sơ năng lực của một khách hàng, tra theo mã khách chứ không theo phiên.

    Hệ khách hàng nhận diện bằng tài khoản, không bằng mã phiên trình duyệt, nên
    không dùng được `get_by_session`. Lấy bản mới nhất: một khách có thể đã khai
    nhiều lần từ nhiều phiên khác nhau trước khi được cấp tài khoản.
    """
    cursor = (
        get_db()[COLLECTION]
        .find({"lead_code": lead_code}, {"_id": 0})
        .sort("updated_at", DESCENDING)
        .limit(1)
    )
    found = await cursor.to_list(length=1)
    return found[0] if found else None


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
