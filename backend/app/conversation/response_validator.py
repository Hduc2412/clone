"""
Response Validator — Sprint 2
Kiểm tra câu trả lời của Gemini trước khi trả về user.
"""

import re

from app.conversation.fallback_messages import (
    ALLOWED_PHONES,
    INVALID_ANSWER,
    RATE_LIMITED,
)

CORRECT_PHONE = list(ALLOWED_PHONES)
MIN_LENGTH = 20

# Giữ tên cũ để không phá chỗ đang import; nội dung lấy từ fallback_messages.
FALLBACK = INVALID_ANSWER
RATE_LIMIT_FALLBACK = RATE_LIMITED

# Số điện thoại viết kiểu nào cũng bắt được: liền, có dấu chấm, có khoảng trắng,
# có gạch nối. Hai chốt chặn hai đầu để không cắt bừa một dãy số dài hơn — thiếu
# chúng thì "năm 2026 0912345678" bị đọc thành một số bắt đầu từ chữ số của năm.
PHONE_IN_TEXT = re.compile(r"(?<!\d)0(?:[ .\-]?\d){9,10}(?!\d)")


def _phones_in(text: str) -> set[str]:
    """Các số điện thoại xuất hiện trong đoạn chữ, đã bỏ hết dấu phân cách."""
    return {re.sub(r"\D", "", match) for match in PHONE_IN_TEXT.findall(text)}


def validate(
    answer: str,
    intent: str = "chung",
    user_message: str = "",
) -> tuple[bool, str]:
    """Kiểm câu trả lời trước khi đưa ra cho khách.

    ## Vì sao bỏ ngoại lệ theo ý định

    Bản trước tắt hẳn bước dò số điện thoại khi ý định là `lead`, với lý do câu
    trả lời có thể nhắc lại số của chính khách. Nhưng bộ phân loại ý định khớp
    chuỗi con không có ranh giới từ, nên nó gán `lead` cho cả những câu hỏi rất
    đỗi bình thường — đo thử thì *"Em muốn đi Nhật thì cần bằng cấp gì?"* cũng ra
    `lead`. Hệ quả: chỉ cần câu hỏi có chữ "muốn đi" hay "tư vấn" là lá chắn tắt,
    và một số điện thoại do mô hình bịa ra đi thẳng tới khách.

    Vế `awaiting_lead` đi kèm là mã chết — không nơi nào đặt nó thành `True`, và
    cũng không nơi nào truyền nó vào. Nên trên thực tế lá chắn chỉ còn phụ thuộc
    vào một phép đoán ý định sai bốn trên mười lần.

    Thay bằng điều kiện nói đúng thứ cần nói: **số nào khách vừa nhắc thì được
    nhắc lại, số nào không thì không.** Nó xử lý đúng trường hợp mà ngoại lệ cũ
    muốn bảo vệ, mà không mở cửa cho số bịa.
    """
    if not answer or len(answer.strip()) < MIN_LENGTH:
        print(f"[Validator] Câu trả lời quá ngắn: '{answer}'")
        return False, FALLBACK

    if answer.strip().startswith("Lỗi Gemini:"):
        print(f"[Validator] Phát hiện lỗi Gemini: '{answer[:50]}'")
        normalized_error = answer.lower()
        if (
            "429" in normalized_error
            or "quota" in normalized_error
            or "resource_exhausted" in normalized_error
            or "rate limit" in normalized_error
        ):
            return False, RATE_LIMIT_FALLBACK
        return False, FALLBACK

    allowed = {re.sub(r"\D", "", phone) for phone in CORRECT_PHONE}
    # Số khách vừa nhắn thì bot được nhắc lại. Đây là chỗ thay cho ngoại lệ theo
    # ý định: nó chỉ mở đúng những số đã có trong câu của khách.
    allowed |= _phones_in(user_message)

    for phone in _phones_in(answer):
        if phone not in allowed:
            print(f"[Validator] Phát hiện SĐT lạ: {phone}")
            return False, FALLBACK

    return True, answer
