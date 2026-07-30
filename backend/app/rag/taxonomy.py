"""Taxonomy nghiệp vụ dùng chung cho ingestion và truy xuất RAG."""

import unicodedata


VALID_TOPICS = {
    "chi_phi",
    "quy_trinh",
    "dieu_kien",
    "luong_thuong",
    "cong_viec",
    "phong_van",
    "thoi_gian",
    "hoc_tap",
    "ky_tuc_xa",
    "chung",
}

TOPIC_TITLE_PATTERNS = {
    "chung": (
        "van de ban dang gap",
        "duoc gi khi chon",
    ),
    "chi_phi": (
        "chi phi",
        "dong phi",
        "dat coc",
        "hoan tien",
        "tra lai tien",
    ),
    "phong_van": (
        "phong van",
        "khong do",
    ),
    "dieu_kien": (
        "dieu kien",
        "yeu cau",
        "tieu chuan",
    ),
    "luong_thuong": (
        "luong",
        "thu nhap",
        "kiem duoc bao nhieu",
    ),
    "thoi_gian": (
        "bao lau",
        "xuat canh",
        "duoc bay",
        "may thang",
        "may nam",
    ),
    "cong_viec": (
        "cong viec",
        "lam nhung gi",
        "vat va",
    ),
    "ky_tuc_xa": (
        "ky tuc xa",
        "ki tuc xa",
    ),
    "hoc_tap": (
        "hoc tieng",
        "lop hoc",
        "hoc vien",
        "ngoai khoa",
        "su kien",
        "le hoi",
        "le giang sinh",
        "le that tich",
        "ngam hoa",
        "thu phap",
    ),
    "quy_trinh": (
        "quy trinh",
        "dang ky",
        "ho so",
        "thu tuc",
        "cac buoc",
    ),
}

SECTION_DEFAULT_TOPIC = {
    "chi_phi": "chi_phi",
    "quy_trinh": "quy_trinh",
    "don_hang": "cong_viec",
    "lop_hoc": "hoc_tap",
}


def normalize_text(text: str) -> str:
    """Đưa tiếng Việt về chữ thường không dấu để so khớp ổn định."""
    normalized = unicodedata.normalize("NFD", text or "")
    text_without_marks = "".join(
        character
        for character in normalized
        if unicodedata.category(character) != "Mn"
    ).lower()
    return text_without_marks.replace("đ", "d")


def infer_topic(section: str, title: str) -> str:
    """Suy ra topic nghiệp vụ từ section nguồn và tiêu đề bài viết."""
    normalized_title = normalize_text(title)

    for topic, patterns in TOPIC_TITLE_PATTERNS.items():
        if any(pattern in normalized_title for pattern in patterns):
            return topic

    return SECTION_DEFAULT_TOPIC.get(section, "chung")
