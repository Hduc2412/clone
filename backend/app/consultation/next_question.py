"""Chọn câu hỏi bổ sung cho lượt tiếp theo.

## Vì sao không để mô hình tự nghĩ câu hỏi

Mô hình hỏi được những câu nghe rất tự nhiên mà chẳng ảnh hưởng gì tới kết quả —
"bạn đã từng đi nước ngoài chưa?" — trong khi trường quyết định nhất vẫn bỏ
trống. Hỏi sai trọng tâm còn tệ hơn không hỏi: khách trả lời xong mà hệ thống
vẫn không tiến thêm được bước nào, và người ta cảm thấy đang bị tra hỏi vô ích.

Ở đây câu hỏi lấy thẳng từ **`engine.MISSING_PROMPTS`**, tức đúng bộ câu mà bộ
đối chiếu đã khai báo cho từng trường nó cần. Một nguồn duy nhất: thêm tiêu chí
mới vào bộ đối chiếu thì bot hỏi thêm câu ấy, không phải sửa hai nơi.

## Nhiều nhất hai câu

Đo trên các phiên đã lưu: câu trả lời càng dài, câu hỏi cuối càng bị bỏ qua.
Hỏi ba thứ một lúc thì khách chọn trả lời một thứ, và hai thứ kia coi như mất.
Hai câu là giới hạn còn giữ được mạch trò chuyện.
"""
from typing import Any

from app.consultation.context_builder import con_thieu


TOI_DA = 2


def chon(profile: dict[str, Any] | None) -> list[str]:
    """Tối đa hai câu hỏi, theo đúng thứ tự ưu tiên của bộ đối chiếu."""
    if not profile:
        return []

    from app.matching.engine import MISSING_PROMPTS

    return [
        MISSING_PROMPTS[key]
        for key in con_thieu(profile)[:TOI_DA]
        if key in MISSING_PROMPTS
    ]


def render(profile: dict[str, Any] | None) -> str:
    """Khối gợi ý hỏi thêm. Rỗng khi hồ sơ đã đủ cho bộ đối chiếu."""
    cac_cau = chon(profile)
    if not cac_cau:
        return ""

    dong = ["[Nên hỏi thêm — tối đa 2 câu, và chỉ sau khi đã trả lời câu hiện tại]"]
    dong.extend(f"  - {cau}" for cau in cac_cau)
    dong.append(
        "(Hỏi bằng lời của bạn cho tự nhiên. Khách đang hỏi chuyện khác thì trả "
        "lời họ trước đã; không có chỗ hỏi thì thôi, để lượt sau.)"
    )
    return "\n".join(dong)
