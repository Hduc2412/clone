"""
Response Validator — Sprint 2
Kiểm tra câu trả lời của Gemini trước khi trả về user.
"""

import re

CORRECT_PHONE = ["0971.716.939", "0971716939"]
MIN_LENGTH = 20

FALLBACK = (
    "Xin lỗi, mình chưa có đủ thông tin để trả lời câu này. "
    "Vui lòng liên hệ anh Quang qua số 0971.716.939 để được tư vấn trực tiếp nhé!"
)

def validate(answer: str, intent: str = "chung") -> tuple[bool, str]:
    if not answer or len(answer.strip()) < MIN_LENGTH:
        print(f"[Validator] Câu trả lời quá ngắn: '{answer}'")
        return False, FALLBACK

    if answer.strip().startswith("Lỗi Gemini:"):
        print(f"[Validator] Phát hiện lỗi Gemini: '{answer[:50]}'")
        return False, FALLBACK

    # Bỏ qua check SĐT khi đang trong luồng lead (answer có thể echo SĐT khách)
    if intent != "lead":
        phone_pattern = r"0\d{9,10}"
        found_phones = re.findall(phone_pattern, answer.replace(".", ""))
        for phone in found_phones:
            normalized = phone.replace(".", "")
            if normalized not in [p.replace(".", "") for p in CORRECT_PHONE]:
                print(f"[Validator] Phát hiện SĐT lạ: {phone}")
                return False, FALLBACK

    return True, answer