"""Chuẩn hóa chuỗi tiếng Việt để so khớp.

`app/rag/taxonomy.py` có một hàm y hệt, nhưng file đó thuộc phần pipeline hội
thoại do nhóm khác phát triển và đang được sửa thường xuyên. Các module nghiệp vụ
ở đây giữ bản riêng để không gãy theo mỗi lần bên kia dọn dẹp file của họ — sáu
dòng trùng lặp rẻ hơn nhiều so với một phụ thuộc chéo giữa hai phần đang được
viết song song.
"""
import unicodedata


def strip_diacritics(text: str) -> str:
    """Bỏ dấu tiếng Việt và hạ về chữ thường.

    "Viện dưỡng lão", "vien duong lao" và "VIEN_DUONG_LAO" phải cho ra cùng một
    chuỗi, vì nhân viên và file Excel của công ty mỗi nơi viết một kiểu.
    """
    decomposed = unicodedata.normalize("NFD", text or "")
    without_marks = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )
    return without_marks.lower().replace("đ", "d")


def normalize_key(text: str) -> str:
    """Chuỗi dùng làm khóa tra cứu: bỏ dấu, gộp khoảng trắng, bỏ gạch nối."""
    plain = strip_diacritics(text).replace("_", " ").replace("-", " ")
    return " ".join(plain.split())
