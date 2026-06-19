"""
Entity Extractor — Sprint 3
Tách tên và số điện thoại từ câu trả lời tự nhiên của user.
"""

import re 

PHONE_PATTERN = r"(0\d{9,10})"
NAME_PATTERNS = [
    r"(?:tôi tên|tên tôi là|tên là|tên tớ là|mình tên|em tên)\s+(?:là\s+)?([A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){0,3})",
    r"^([A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){0,3})\s*[,-]",
]

def extract_phone(text: str) -> str | None:
    """Tìm ra số điện thoại"""
    match = re.search(PHONE_PATTERN, text.replace(".", "").replace(" ", ""))
    return match.group(1) if match else None

def extract_name(text: str) -> str | None:
    """Tìm tên trong text dựa trên các pattern phổ biến."""
    for pattern in NAME_PATTERNS:
        match = re.search(pattern, text, re.UNICODE)
        if match:
            return match.group(1).strip()
    return None

def extract_lead_info(text: str) -> dict:
    """
    Trích xuất tên + SĐT từ 1 câu trả lời.
    Trả về dict, field nào không tìm thấy thì None.
    """
    result = {
        "name": extract_name(text),
        "phone": extract_phone(text),
    }
    print(f"[EntityExtractor] '{text}' → {result}")
    return result

