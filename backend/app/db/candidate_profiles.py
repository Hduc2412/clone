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

#: Mã lỗi ổn định khi một đường tư vấn phía khách gặp hồ sơ chưa xác nhận. Giao diện
#: dựa vào mã này (không dựa vào câu chữ) để đưa khách về bước kiểm tra và xác nhận.
MA_CHUA_XAC_NHAN = "ho_so_chua_xac_nhan"


def loi_chua_xac_nhan() -> dict[str, Any]:
    return {
        "code": MA_CHUA_XAC_NHAN,
        "message": (
            "Hồ sơ chưa được bạn xác nhận. Bạn kiểm tra và xác nhận hồ sơ trước, "
            "rồi bảng đối chiếu mới hiện."
        ),
    }


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



# --- Bốn trạng thái tiếng Nhật mà khách và trợ lý phải nói khác nhau (08/10) ---
#
# "N4" một mình không đủ: "đang học N4", "tự khai N4", "đã đạt N4" và "có chứng chỉ
# N4" là bốn mức tin khác nhau, và chỉ ba mức sau là trình độ ĐÃ CÓ. Bộ đối chiếu
# vẫn đọc đúng `japanese_level` như cũ — trạng thái này chỉ nói căn cứ của nó.
#
# - `tu_khai`: khách khai, CV ghi, hoặc nhân viên ghi mà khách không xuất trình gì.
# - Hoàn thành chương trình tại trung tâm: nằm trong `hoc_tap`, nhãn "Hoàn thành
#   chương trình N4 tại trung tâm — chưa xác minh chứng chỉ". KHÔNG đổi `japanese_level`
#   và không tự coi tương đương yêu cầu chứng chỉ của đơn (quyết định 08/10).
# - `co_chung_chi`: nhân viên đã đối chứng bằng gốc hoặc tra cứu chính thức.
# - `dang_hoc` không phải một mức của `japanese_level`: nó nằm trong `hoc_tap`, và
#   trình độ đang học tới **không** được tính là đã có.

TT_TU_KHAI = "tu_khai"
#: Bản ghi cũ mang mức `center`. Từ 08/10 (bản 2) không còn đường nào ghi mức này: hoàn
#: thành chương trình tại trung tâm KHÔNG đổi trình độ bộ đối chiếu đọc — xem `hoc_tap`.
TT_HOAN_THANH_TRUNG_TAM = "hoan_thanh_chuong_trinh"
TT_CO_CHUNG_CHI = "co_chung_chi"


def da_xac_minh_co_can_cu(o: dict[str, Any] | None) -> bool:
    """Ô có căn cứ đối chứng: nhân viên đã xem bản gốc hoặc tra cứu trên trang chính thức.

    Đây là điều kiện DUY NHẤT để khóa một ô trước lời khách tự khai (08/10, bản 2).
    "Nhân viên nhập" không có nghĩa là "đã kiểm chứng": nhân viên ghi lại điều khách nói
    qua điện thoại cũng mang nguồn `staff`, và khóa nó là giữ lời khai cũ trước lời khai mới
    của chính người ấy.
    """
    o = o or {}
    return o.get("verification") == XAC_THUC_DOI_CHUNG and o.get("evidence_type") in (
        CHUNG_CU_BAN_GOC, CHUNG_CU_TRA_CUU
    )
TT_DANG_HOC = "dang_hoc"

HOC_DANG_HOC = "dang_hoc"
HOC_TAM_DUNG = "tam_dung"
HOC_HOAN_THANH = "da_hoan_thanh"
CAC_TRANG_THAI_HOC = (HOC_DANG_HOC, HOC_TAM_DUNG, HOC_HOAN_THANH)
NHAN_TRANG_THAI_HOC = {
    HOC_DANG_HOC: "đang học",
    HOC_TAM_DUNG: "tạm dừng học",
    HOC_HOAN_THANH: "đã hoàn thành khóa",
}


def trang_thai_tieng_nhat(profile: dict[str, Any] | None) -> dict[str, Any]:
    """Trình độ đang có, căn cứ của nó, và việc học đang diễn ra — tách rõ từng phần."""
    from app.matching import catalog

    o = ((profile or {}).get("fields") or {}).get("japanese_level") or {}
    muc = o.get("value")
    nhan_muc = catalog.JAPANESE_LEVEL_LABELS.get(str(muc), str(muc)) if muc else None
    if not muc:
        ma, nhan = None, None
    elif o.get("verification") == XAC_THUC_DOI_CHUNG and o.get("evidence_type") in (
        CHUNG_CU_BAN_GOC, CHUNG_CU_TRA_CUU
    ):
        ma = TT_CO_CHUNG_CHI
        cach = "bản gốc" if o.get("evidence_type") == CHUNG_CU_BAN_GOC else "tra cứu chính thức"
        nhan = f"{nhan_muc} — có chứng chỉ, nhân viên đã đối chứng ({cach})"
    elif o.get("verification") == XAC_THUC_TRUNG_TAM:
        ma = TT_HOAN_THANH_TRUNG_TAM
        nhan = f"Hoàn thành chương trình {nhan_muc} tại trung tâm — chưa xác minh chứng chỉ"
    else:
        ma, nhan = TT_TU_KHAI, f"{nhan_muc} — tự khai, chưa được đối chứng"
    hoc = (profile or {}).get("hoc_tap") or {}
    dang_hoc = None
    if hoc.get("trang_thai") in (HOC_DANG_HOC, HOC_TAM_DUNG):
        dich = hoc.get("muc_tieu")
        dang_hoc = {
            "trang_thai": hoc["trang_thai"],
            "nhan": (
                f"{NHAN_TRANG_THAI_HOC[hoc['trang_thai']]} hướng tới "
                f"{catalog.JAPANESE_LEVEL_LABELS.get(str(dich), str(dich))}"
                + (f" (khóa {hoc['khoa_code']})" if hoc.get("khoa_code") else "")
                + " — chưa phải trình độ đã có"
            ),
            "muc_tieu": dich,
            "khoa_code": hoc.get("khoa_code"),
            "cap_nhat_luc": hoc.get("cap_nhat_luc"),
        }
    # Hoàn thành chương trình tại trung tâm: thông tin học tập, KHÔNG phải trình độ đã
    # xác minh và không tự coi tương đương yêu cầu chứng chỉ của đơn (08/10, bản 2).
    chuong_trinh = None
    if hoc.get("trang_thai") == HOC_HOAN_THANH and hoc.get("ket_qua"):
        kq = catalog.JAPANESE_LEVEL_LABELS.get(str(hoc["ket_qua"]), str(hoc["ket_qua"]))
        chuong_trinh = {
            "muc": hoc["ket_qua"],
            "khoa_code": hoc.get("khoa_code"),
            "nhan": f"Hoàn thành chương trình {kq} tại trung tâm — chưa xác minh chứng chỉ",
        }
    return {"muc": muc, "ma": ma, "nhan": nhan, "dang_hoc": dang_hoc, "chuong_trinh": chuong_trinh}


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
            #
            # Ngoại lệ (08/10, bản 2): KHÁCH sửa một ô nhân viên nhập mà KHÔNG có căn
            # cứ đối chứng — đó là lời khai được nhân viên chép lại, không phải điều đã
            # kiểm. Khách sửa lời khai của chính mình thì lời mới thắng; nhân viên nhận
            # một dòng thông báo (`o_khach_sua`). CV và hội thoại vẫn không đè được.
            khach_sua_loi_khai = (
                source == "user_confirmed"
                and current.get("source") == "staff"
                and not da_xac_minh_co_can_cu(current)
            )
            if incoming_priority < current_priority and not khach_sua_loi_khai:
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


# --- Giá trị nhân viên đã ghi: không bị ghi đè, cũng không bị lờ đi (08/10) ---
#
# `merge_section` vốn bỏ qua giá trị của nguồn yếu hơn — đúng về quyền ghi, nhưng
# **im lặng**: khách sửa trình độ từ N4 (nhân viên đã đối chứng bằng gốc) thành N5,
# màn hình báo lưu xong, giá trị vẫn N4, và không ai biết khách vừa nói một điều
# khác. Kiểm sống XM-1. Nay giá trị ấy thành một **đề xuất chờ nhân viên**, nằm
# trong `consultation.conflicts` — chỗ trợ lý vẫn ghi mâu thuẫn nghe được trong hội
# thoại — chứ không tạo cấu trúc thứ hai cho cùng một việc.

LOAI_DE_XUAT_NHAN_VIEN = "khac_gia_tri_nhan_vien"
DE_XUAT_CHO = "cho_nhan_vien"
DE_XUAT_DA_XU_LY = "da_xu_ly"
TRAN_DE_XUAT = 20
TRAN_LICH_SU_XAC_MINH = 20


def o_bi_giu(
    existing: dict[str, Any] | None,
    incoming: dict[str, Any],
    *,
    source: str,
) -> list[dict[str, Any]]:
    """Những ô ĐÃ XÁC MINH CÓ CĂN CỨ mà người gửi (nguồn yếu hơn) muốn đổi giá trị.

    Thuần, không ghi gì. Ô nhân viên nhập mà không có căn cứ thì không bị khóa — khách
    tự sửa được (`merge_section`), nhân viên nhận một dòng thông báo (`o_khach_sua`).
    """
    muc_gui = SOURCE_PRIORITY.get(source, 0)
    ra: list[dict[str, Any]] = []
    for key, value in incoming.items():
        if value is None or value == "":
            continue
        o = (existing or {}).get(key) or {}
        if not da_xac_minh_co_can_cu(o) or muc_gui >= SOURCE_PRIORITY["staff"]:
            continue
        if o.get("value") == value:
            continue
        ra.append({
            "field": key,
            "gia_tri_nhan_vien": o.get("value"),
            "gia_tri_de_xuat": value,
            "verification": o.get("verification"),
        })
    return ra


LOAI_KHACH_SUA_O_NHAN_VIEN = "khach_sua_o_nhan_vien_nhap"
DA_AP_DUNG = "da_ap_dung"


def o_khach_sua(existing: dict[str, Any] | None, incoming: dict[str, Any], *, source: str) -> list[dict[str, Any]]:
    """Ô nhân viên nhập (không có căn cứ) mà khách vừa sửa sang giá trị khác. Thuần."""
    if source != "user_confirmed":
        return []
    ra = []
    for key, value in incoming.items():
        o = (existing or {}).get(key) or {}
        if value in (None, "") or o.get("source") != "staff" or da_xac_minh_co_can_cu(o):
            continue
        if o.get("value") != value:
            ra.append({"field": key, "gia_tri_nhan_vien": o.get("value"), "gia_tri_de_xuat": value})
    return ra


async def ghi_thong_bao_khach_sua(session_id: str, da_sua: list[dict[str, Any]], *, by: str) -> None:
    """Báo nhân viên: khách đã sửa ô nhân viên nhập. Đã áp dụng — không chờ ai duyệt."""
    if not da_sua:
        return
    moi = [
        {"field": d["field"], "previous": d["gia_tri_nhan_vien"], "suggested": d["gia_tri_de_xuat"],
         "source": "user_confirmed", "kind": LOAI_KHACH_SUA_O_NHAN_VIEN, "trang_thai": DA_AP_DUNG,
         "recorded_at": now(), "by": by}
        for d in da_sua
    ]
    await get_db()[COLLECTION].update_one(
        {"session_id": session_id},
        {"$push": {"consultation.conflicts": {"$each": moi, "$slice": -TRAN_DE_XUAT}}},
    )


async def ghi_de_xuat(
    session_id: str, bi_giu: list[dict[str, Any]], *, source: str, by: str
) -> None:
    """Lưu đề xuất chờ nhân viên. **Không** tăng phiên bản hồ sơ.

    Đề xuất không đổi gì bộ đối chiếu đọc, nên không có lý do làm mất hiệu lực kết
    quả đối chiếu. Gửi lại đúng đề xuất đang chờ thì không thêm dòng thứ hai.
    """
    if not bi_giu:
        return
    hien = await get_by_session(session_id)
    cho = {
        (c.get("field"), c.get("suggested"))
        for c in ((hien or {}).get("consultation") or {}).get("conflicts") or []
        if c.get("kind") == LOAI_DE_XUAT_NHAN_VIEN and c.get("trang_thai") == DE_XUAT_CHO
    }
    moi = [
        {
            "field": b["field"],
            "previous": b["gia_tri_nhan_vien"],
            "suggested": b["gia_tri_de_xuat"],
            "source": source,
            "kind": LOAI_DE_XUAT_NHAN_VIEN,
            "trang_thai": DE_XUAT_CHO,
            "recorded_at": now(),
            "by": by,
        }
        for b in bi_giu
        if (b["field"], b["gia_tri_de_xuat"]) not in cho
    ]
    if not moi:
        return
    await get_db()[COLLECTION].update_one(
        {"session_id": session_id},
        {"$push": {"consultation.conflicts": {"$each": moi, "$slice": -TRAN_DE_XUAT}}},
    )


def de_xuat_dang_cho(profile: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        c for c in ((profile.get("consultation") or {}).get("conflicts") or [])
        if c.get("kind") == LOAI_DE_XUAT_NHAN_VIEN and c.get("trang_thai") == DE_XUAT_CHO
    ]


def ghi_nhan_nhan_vien_sua(
    profile: dict[str, Any],
    merged_fields: dict[str, Any],
    changed: list[str],
    *,
    by: str,
) -> dict[str, Any]:
    """Phần `consultation` mới sau khi nhân viên sửa các ô `changed`. Thuần.

    Hai việc, cùng lúc với lần ghi hồ sơ:

    1. Ô đang mang nhãn xác minh mà nhân viên đổi giá trị: nhãn **không đi theo** giá
       trị mới (`merge_section` dựng ô mới), nhưng nhãn cũ — ai xác minh, lúc nào,
       bằng gì — được chép vào `lich_su_xac_minh` chứ không mất theo năm bản lịch sử.
    2. Đề xuất đang chờ của chính ô ấy: nhân viên vừa quyết giá trị, nên đề xuất
       chuyển sang đã xử lý.
    """
    tu_van = dict(profile.get("consultation") or {})
    lich_su = list(tu_van.get("lich_su_xac_minh") or [])
    for key in changed:
        cu = ((profile.get("fields") or {}).get(key)) or {}
        if cu.get("verification") and (merged_fields.get(key) or {}).get("value") != cu.get("value"):
            lich_su.append({
                "field": key,
                "value": cu.get("value"),
                "verification": cu.get("verification"),
                "evidence_type": cu.get("evidence_type"),
                "verified_by": cu.get("verified_by"),
                "verified_at": cu.get("verified_at"),
                "thay_boi": by,
                "thay_luc": now(),
                "gia_tri_moi": (merged_fields.get(key) or {}).get("value"),
            })
    tu_van["lich_su_xac_minh"] = lich_su[-TRAN_LICH_SU_XAC_MINH:]
    xung = []
    for c in tu_van.get("conflicts") or []:
        if (
            c.get("kind") == LOAI_DE_XUAT_NHAN_VIEN
            and c.get("trang_thai") == DE_XUAT_CHO
            and c.get("field") in changed
        ):
            c = {**c, "trang_thai": DE_XUAT_DA_XU_LY, "xu_ly_boi": by, "xu_ly_luc": now()}
        xung.append(c)
    tu_van["conflicts"] = xung
    return tu_van


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
    profile["trang_thai_tieng_nhat"] = trang_thai_tieng_nhat(profile)
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
    ra = {key: value for key, value in profile.items() if key not in hidden}
    # Nhãn xác minh thì khách được biết; ai xác minh (email nhân viên) thì không.
    ra["fields"] = {
        key: {k: v for k, v in (cell or {}).items() if k != "verified_by"}
        for key, cell in (profile.get("fields") or {}).items()
    }
    # Lịch sử nhãn xác minh, người xử lý và lý do đóng đề xuất là sổ nội bộ.
    tu_van = dict(profile.get("consultation") or {})
    tu_van.pop("lich_su_xac_minh", None)
    tu_van["conflicts"] = [
        {k: v for k, v in c.items() if k not in ("by", "xu_ly_boi", "ly_do")}
        for c in tu_van.get("conflicts") or []
    ]
    if profile.get("consultation") is not None:
        ra["consultation"] = tu_van
    if profile.get("hoc_tap"):
        ra["hoc_tap"] = {k: v for k, v in profile["hoc_tap"].items() if k != "cap_nhat_boi"}
    return ra


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
    extra: dict[str, Any] | None = None,
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
    # Trường cấp hồ sơ khác (`hoc_tap`) — đi cùng khóa phiên bản như mọi lần ghi.
    for key, value in (extra or {}).items():
        changes[key] = value
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


async def ghi_xung_dot(session_id: str, conflicts: list[dict[str, Any]]) -> None:
    """Ghi lại danh sách đề xuất/mâu thuẫn. Không tăng phiên bản — xem `ghi_de_xuat`."""
    await get_db()[COLLECTION].update_one(
        {"session_id": session_id}, {"$set": {"consultation.conflicts": conflicts[-TRAN_DE_XUAT:]}}
    )
