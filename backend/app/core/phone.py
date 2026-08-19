import re


def normalize_vietnamese_phone(value: str) -> str:
    """Return one stable local format for supported Vietnamese phone numbers."""
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("84"):
        digits = f"0{digits[2:]}"
    if not re.fullmatch(r"0\d{9,10}", digits):
        raise ValueError("Số điện thoại phải có 10–11 chữ số và bắt đầu bằng 0 hoặc +84.")
    return digits
