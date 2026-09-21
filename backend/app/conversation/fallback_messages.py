"""Nơi duy nhất định nghĩa các câu trả lời dự phòng của chatbot.

Trước đây bốn câu này nằm rải ở `chat_service` và `response_validator`, nên
`analytics_service` phải dò chuỗi để đếm tỷ lệ fallback và chỉ bắt được một
trong bốn câu. Gom về đây để mọi nơi dùng chung một nguồn.
"""
import re

from app.core.config import settings


def _digits(phone: str) -> str:
    return phone.replace(".", "").replace(" ", "").replace("-", "")


SUPPORT_PHONE = settings.support_phone
SUPPORT_PHONE_DIGITS = _digits(SUPPORT_PHONE)

# Các số được phép xuất hiện trong câu trả lời (dạng có dấu chấm và không dấu).
ALLOWED_PHONES = (SUPPORT_PHONE, SUPPORT_PHONE_DIGITS)

# Không tìm được đoạn tri thức nào vượt ngưỡng.
NO_KNOWLEDGE = (
    "Xin lỗi, tôi không tìm thấy thông tin liên quan. "
    f"Vui lòng liên hệ {SUPPORT_PHONE} để được tư vấn trực tiếp."
)

# Người dùng tỏ ý quan tâm nhưng chưa có tri thức để trả lời.
LEAD_NO_KNOWLEDGE = (
    "Nếu bạn muốn nhân viên liên hệ, hãy nhắn **đặt lịch tư vấn** "
    "để mình hỗ trợ chọn ngày và giờ."
)

# Câu trả lời của mô hình không qua được bước kiểm chứng.
INVALID_ANSWER = (
    "Xin lỗi, mình chưa có đủ thông tin để trả lời câu này. "
    f"Vui lòng liên hệ anh Quang qua số {SUPPORT_PHONE} để được tư vấn trực tiếp nhé!"
)

# Dịch vụ ngôn ngữ đang quá tải.
RATE_LIMITED = (
    "Hiện chatbot đang có nhiều yêu cầu cùng lúc. "
    "Bạn vui lòng thử lại sau khoảng một phút nhé!"
)

# Câu từ chối mà prompt yêu cầu mô hình dùng nguyên văn.
#
# Trước đây mô hình tự nghĩ lời từ chối, mỗi lần một kiểu: "website chưa cung
# cấp", "tôi chưa tìm thấy", "thông tin từ website chưa đề cập"… Hệ thống phải dò
# bằng biểu thức chính quy, mà dò thì có lúc trượt — và trượt nghĩa là một lời từ
# chối bị đếm như câu trả lời thành công.
#
# Ấn định một câu cố định thì việc nhận biết thành so chuỗi chính xác. Biểu thức
# chính quy bên dưới vẫn giữ, vì mô hình không phải lúc nào cũng nghe lời, và vì
# những câu đã lưu từ trước vẫn mang lời lẽ cũ.
MODEL_REFUSAL = (
    "Thông tin này chưa có trong tài liệu của công ty. "
    f"Bạn liên hệ {SUPPORT_PHONE} để được nhân viên tư vấn trực tiếp nhé."
)

ALL_FALLBACKS = (NO_KNOWLEDGE, LEAD_NO_KNOWLEDGE, INVALID_ANSWER, RATE_LIMITED, MODEL_REFUSAL)


# Mô hình có cách từ chối riêng của nó, không dùng bốn câu trên. Những câu đó
# trước đây không được gắn cờ nào cả, nên thống kê đếm chúng như câu trả lời
# thành công — đo trên dữ liệu thật: 3 câu được gắn cờ, trong khi có thêm 7 câu
# mô hình tự từ chối mà không ai đếm.
#
# Nhận diện bằng chữ là cách duy nhất còn lại: mô hình không trả về tín hiệu nào
# cho biết nó vừa từ chối. Vì vậy mẫu dưới đây cố ý hẹp — thà bỏ sót một câu từ
# chối còn hơn gắn nhầm cờ cho một câu trả lời thật, vì cờ này đi thẳng vào con
# số "tỷ lệ trả lời được" của báo cáo.
_REFUSAL = re.compile(
    r"(website|tài liệu|thông tin|nguồn|dữ liệu)[^.]{0,40}(chưa|không) (cung cấp|có|đề cập|nêu)"
    r"|(chưa|không) (có|đủ|tìm thấy) (thông tin|dữ liệu|căn cứ)"
    r"|không thuộc chuyên môn"
    r"|ngoài phạm vi"
    r"|không thể (đoán|dự đoán|khẳng định|cam kết|bảo đảm|đảm bảo|trả lời)",
    re.IGNORECASE,
)


def looks_like_refusal(answer: str) -> bool:
    """Câu này có phải là một lời từ chối không, dù do mô hình tự viết ra.

    Dùng chung cho `chat_service` (để gắn cờ) và bộ nghiệm thu (để chấm điểm).
    Hai nơi tự định nghĩa riêng thì sớm muộn sẽ lệch nhau, và lúc đó bộ nghiệm
    thu sẽ báo đạt cho đúng thứ mà hệ thống đang đếm sai.
    """
    if not answer:
        return False
    return answer in ALL_FALLBACKS or bool(_REFUSAL.search(answer))
