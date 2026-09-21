"""Danh mục dùng chung: tỉnh Nhật Bản, chương trình, loại hình cơ sở, trình độ.

Hai vai trò:

1. **Chuẩn hóa đầu vào.** Nhân viên nhập đơn hàng bằng tiếng Việt có dấu, file
   Excel của công ty ghi mỗi nơi một kiểu ("Viện dưỡng lão", "vien duong lao",
   "VIEN_DUONG_LAO"). Tất cả phải quy về một mã duy nhất, nếu không bộ đối chiếu
   sẽ coi hai đơn giống nhau là khác nhau.
2. **Nhãn hiển thị.** Mã lưu trong database là tiếng Anh không dấu để bền vững,
   nhãn tiếng Việt trả về qua API để giao diện không phải tự chép bảng — chép
   bảng ở hai nơi là cách chắc chắn nhất để chúng lệch nhau về sau.

Thứ tự trong `JAPANESE_RANK` và `EDUCATION_RANK` là thứ tự so sánh của bộ lọc
điều kiện cứng, nên đừng đổi nếu không có lý do nghiệp vụ.
"""
from app.core.text import normalize_key as normalize_text


# --- Vùng tại Nhật Bản ---

REGION_LABELS: dict[str, str] = {
    "hokkaido": "Hokkaidō",
    "tohoku": "Tōhoku",
    "kanto": "Kantō",
    "chubu": "Chūbu",
    "kansai": "Kansai",
    "chugoku": "Chūgoku",
    "shikoku": "Shikoku",
    "kyushu": "Kyūshū – Okinawa",
}

# 47 tỉnh, viết theo chữ Latinh không dấu để khớp với cách nhân viên gõ.
PREFECTURE_REGION: dict[str, str] = {
    "Hokkaido": "hokkaido",
    "Aomori": "tohoku",
    "Iwate": "tohoku",
    "Miyagi": "tohoku",
    "Akita": "tohoku",
    "Yamagata": "tohoku",
    "Fukushima": "tohoku",
    "Ibaraki": "kanto",
    "Tochigi": "kanto",
    "Gunma": "kanto",
    "Saitama": "kanto",
    "Chiba": "kanto",
    "Tokyo": "kanto",
    "Kanagawa": "kanto",
    "Niigata": "chubu",
    "Toyama": "chubu",
    "Ishikawa": "chubu",
    "Fukui": "chubu",
    "Yamanashi": "chubu",
    "Nagano": "chubu",
    "Gifu": "chubu",
    "Shizuoka": "chubu",
    "Aichi": "chubu",
    "Mie": "kansai",
    "Shiga": "kansai",
    "Kyoto": "kansai",
    "Osaka": "kansai",
    "Hyogo": "kansai",
    "Nara": "kansai",
    "Wakayama": "kansai",
    "Tottori": "chugoku",
    "Shimane": "chugoku",
    "Okayama": "chugoku",
    "Hiroshima": "chugoku",
    "Yamaguchi": "chugoku",
    "Tokushima": "shikoku",
    "Kagawa": "shikoku",
    "Ehime": "shikoku",
    "Kochi": "shikoku",
    "Fukuoka": "kyushu",
    "Saga": "kyushu",
    "Nagasaki": "kyushu",
    "Kumamoto": "kyushu",
    "Oita": "kyushu",
    "Miyazaki": "kyushu",
    "Kagoshima": "kyushu",
    "Okinawa": "kyushu",
}

# Cách viết khác mà nhân viên hay gõ, quy về tên chuẩn ở trên.
PREFECTURE_ALIASES: dict[str, str] = {
    "tokyo to": "Tokyo",
    "tokyo-to": "Tokyo",
    "osaka fu": "Osaka",
    "osaka-fu": "Osaka",
    "kyoto fu": "Kyoto",
    "hokkaido do": "Hokkaido",
    "hyogo ken": "Hyogo",
    "hyougo": "Hyogo",
    "tokio": "Tokyo",
    "oosaka": "Osaka",
    "kyouto": "Kyoto",
    "gifu ken": "Gifu",
    "ooita": "Oita",
    "kouchi": "Kochi",
}


# --- Enum nghiệp vụ ---

EMPLOYER_TYPE_LABELS: dict[str, str] = {
    "vien_duong_lao": "Viện dưỡng lão",
    "benh_vien": "Bệnh viện",
    "cham_soc_tai_gia": "Chăm sóc tại gia",
}

PROGRAM_LABELS: dict[str, str] = {
    "epa": "EPA",
    "tokutei_ginou": "Kỹ năng đặc định (Tokutei Ginou)",
    "thuc_tap_sinh": "Thực tập sinh kỹ năng",
}

JAPANESE_LEVEL_LABELS: dict[str, str] = {
    "chua_hoc": "Chưa học",
    "N5": "N5",
    "N4": "N4",
    "N3": "N3",
    "N2": "N2",
    "N1": "N1",
}

# Thứ tự so sánh: ứng viên đạt khi thứ hạng của mình không thấp hơn yêu cầu.
JAPANESE_RANK: dict[str, int] = {
    "chua_hoc": 0,
    "N5": 1,
    "N4": 2,
    "N3": 3,
    "N2": 4,
    "N1": 5,
}

EDUCATION_LABELS: dict[str, str] = {
    "khac": "Khác",
    "trung_cap": "Trung cấp",
    "cao_dang": "Cao đẳng",
    "dai_hoc": "Đại học",
}

EDUCATION_RANK: dict[str, int] = {
    "khac": 0,
    "trung_cap": 1,
    "cao_dang": 2,
    "dai_hoc": 3,
}

GENDER_PREF_LABELS: dict[str, str] = {
    "khong_yeu_cau": "Không yêu cầu",
    "nam": "Nam",
    "nu": "Nữ",
}

GENDER_LABELS: dict[str, str] = {
    "nam": "Nam",
    "nu": "Nữ",
}

# Kết quả đối chiếu một tiêu chí bắt buộc. "Chưa rõ" là trạng thái riêng chứ
# không gộp vào "không đạt": thiếu thông tin thì hỏi thêm, không loại đơn.
RESULT_LABELS: dict[str, str] = {
    "DAT": "ĐẠT",
    "KHONG_DAT": "KHÔNG ĐẠT",
    "CHUA_RO": "CHƯA RÕ",
}

PROFILE_STATUS_LABELS: dict[str, str] = {
    "extracted": "Đã trích xuất",
    "confirmed": "Đã xác nhận",
}

# Nguồn của từng trường trong hồ sơ, xếp theo mức độ đáng tin tăng dần.
SOURCE_LABELS: dict[str, str] = {
    "chat": "Hội thoại",
    "cv": "Từ CV",
    "user_confirmed": "Ứng viên xác nhận",
    "staff": "Nhân viên nhập",
}

SOURCE_PRIORITY: dict[str, int] = {
    "chat": 1,
    "cv": 2,
    "user_confirmed": 3,
    "staff": 4,
}

JOB_ORDER_STATUS_LABELS: dict[str, str] = {
    "draft": "Nháp",
    "open": "Đang tuyển",
    "paused": "Tạm dừng",
    "filled": "Đủ số lượng",
    "expired": "Hết hạn",
    "closed": "Đã đóng",
}

# Từ trạng thái nào chuyển được sang trạng thái nào. Trạng thái đóng là điểm cuối.
JOB_ORDER_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"open", "closed"}),
    "open": frozenset({"paused", "filled", "expired", "closed"}),
    "paused": frozenset({"open", "expired", "closed"}),
    "filled": frozenset({"open", "closed"}),
    "expired": frozenset({"open", "closed"}),
    "closed": frozenset(),
}


def _lookup_table(labels: dict[str, str]) -> dict[str, str]:
    """Bảng tra từ mọi cách viết về mã chuẩn: theo mã và theo nhãn không dấu."""
    table: dict[str, str] = {}
    for code, label in labels.items():
        table[normalize_text(code)] = code
        table[normalize_text(label)] = code
    return table


_EMPLOYER_TYPE_LOOKUP = _lookup_table(EMPLOYER_TYPE_LABELS)
_PROGRAM_LOOKUP = _lookup_table(PROGRAM_LABELS) | {
    "tokutei": "tokutei_ginou",
    "tokutei ginou": "tokutei_ginou",
    "ky nang dac dinh": "tokutei_ginou",
    "thuc tap sinh ky nang": "thuc_tap_sinh",
    "tts": "thuc_tap_sinh",
}
_JAPANESE_LEVEL_LOOKUP = _lookup_table(JAPANESE_LEVEL_LABELS) | {
    "chua co": "chua_hoc",
    "mat goc": "chua_hoc",
    "khong yeu cau": "chua_hoc",
}
_EDUCATION_LOOKUP = _lookup_table(EDUCATION_LABELS) | {
    "khong yeu cau": "khac",
    "trung cap dieu duong": "trung_cap",
    "cao dang dieu duong": "cao_dang",
    "dai hoc dieu duong": "dai_hoc",
}
_GENDER_PREF_LOOKUP = _lookup_table(GENDER_PREF_LABELS) | {
    "any": "khong_yeu_cau",
    "khong": "khong_yeu_cau",
    "nam nu": "khong_yeu_cau",
}
_GENDER_LOOKUP = _lookup_table(GENDER_LABELS) | {"male": "nam", "female": "nu"}
_JOB_ORDER_STATUS_LOOKUP = _lookup_table(JOB_ORDER_STATUS_LABELS)
_REGION_LOOKUP = _lookup_table(REGION_LABELS)
_PREFECTURE_LOOKUP = {
    normalize_text(name): name for name in PREFECTURE_REGION
} | PREFECTURE_ALIASES


def _normalize(value: object, lookup: dict[str, str]) -> str | None:
    if value is None:
        return None
    key = normalize_text(str(value)).strip()
    return lookup.get(key)


def normalize_employer_type(value: object) -> str | None:
    return _normalize(value, _EMPLOYER_TYPE_LOOKUP)


def normalize_program(value: object) -> str | None:
    return _normalize(value, _PROGRAM_LOOKUP)


def find_japanese_levels(value: object) -> list[str]:
    """Mọi mức tiếng Nhật xuất hiện trong chuỗi, xếp từ dễ đến khó.

    File đơn hàng thật hay ghi kiểu "N4 trở lên, ưu tiên N3" hoặc CV ghi
    "N4, đang ôn N3". Trả về danh sách để nơi gọi tự quyết định, thay vì âm thầm
    chọn một mức rồi giấu đi chuyện câu gốc có nhiều mức.
    """
    if value is None:
        return []
    text = normalize_text(str(value))
    found = [code for code in ("N5", "N4", "N3", "N2", "N1") if code.lower() in text]
    return sorted(found, key=JAPANESE_RANK.__getitem__)


def normalize_japanese_level(value: object) -> str | None:
    """Nhận "N4", "n4", "Chưa học"... Bắt cả mức lẫn trong câu như "trình độ N4".

    Khi câu có nhiều mức thì lấy **mức thấp nhất**, vì trường này là điều kiện
    tối thiểu: "N4 trở lên, ưu tiên N3" nghĩa là bắt buộc N4, còn N3 chỉ là ưu
    tiên. Lấy nhầm mức cao hơn sẽ loại oan mọi ứng viên N4 ngay ở bộ lọc cứng —
    đúng loại sai mà hệ thống này tồn tại để tránh. Đọc CV cũng theo quy tắc ấy:
    "N4, đang ôn N3" thì chứng chỉ đang có là N4.

    Nơi nào cần cảnh báo khi câu mập mờ (bộ nhập liệu hàng loạt) thì gọi
    `find_japanese_levels` để thấy đủ các mức rồi hỏi lại người nhập.
    """
    direct = _normalize(value, _JAPANESE_LEVEL_LOOKUP)
    if direct is not None:
        return direct
    levels = find_japanese_levels(value)
    return levels[0] if levels else None


def normalize_education(value: object) -> str | None:
    return _normalize(value, _EDUCATION_LOOKUP)


def normalize_gender_pref(value: object) -> str | None:
    return _normalize(value, _GENDER_PREF_LOOKUP)


def normalize_gender(value: object) -> str | None:
    return _normalize(value, _GENDER_LOOKUP)


def normalize_job_order_status(value: object) -> str | None:
    return _normalize(value, _JOB_ORDER_STATUS_LOOKUP)


def normalize_region(value: object) -> str | None:
    return _normalize(value, _REGION_LOOKUP)


def normalize_prefecture(value: object) -> str | None:
    return _normalize(value, _PREFECTURE_LOOKUP)


def region_for_prefecture(prefecture: object) -> str | None:
    """Suy vùng từ tỉnh, để nhân viên không phải nhập cả hai và nhập lệch nhau."""
    canonical = normalize_prefecture(prefecture)
    return PREFECTURE_REGION.get(canonical) if canonical else None


def prefecture_label(prefecture: str | None) -> str | None:
    return normalize_prefecture(prefecture)


def label_options(labels: dict[str, str]) -> list[dict[str, str]]:
    """Đưa bảng nhãn về dạng danh sách cho giao diện đổ vào ô chọn."""
    return [{"code": code, "label": label} for code, label in labels.items()]


def catalog_meta() -> dict[str, object]:
    """Toàn bộ danh mục cho giao diện, trả qua endpoint `/job-orders/meta`."""
    return {
        "employer_types": label_options(EMPLOYER_TYPE_LABELS),
        "programs": label_options(PROGRAM_LABELS),
        "japanese_levels": label_options(JAPANESE_LEVEL_LABELS),
        "education_levels": label_options(EDUCATION_LABELS),
        "gender_prefs": label_options(GENDER_PREF_LABELS),
        "statuses": label_options(JOB_ORDER_STATUS_LABELS),
        "transitions": {
            status: sorted(targets)
            for status, targets in JOB_ORDER_TRANSITIONS.items()
        },
        "regions": label_options(REGION_LABELS),
        "prefectures": [
            {"code": name, "label": name, "region_group": region}
            for name, region in PREFECTURE_REGION.items()
        ],
    }
