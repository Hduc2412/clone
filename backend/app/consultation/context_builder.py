"""Dựng khối "ĐANG BIẾT VỀ KHÁCH" để đưa vào ngữ cảnh mỗi lượt chat.

## Vấn đề được giải

Đo trên máy chủ thật ngày 22/09/2026: một khách đã khai đủ hồ sơ — N4, ba năm
kinh nghiệm chăm sóc, muốn đi Tokyo — và hệ thống đã xếp hạng 11 đơn phù hợp cho
họ. Nhưng khi chính người ấy hỏi trong cửa sổ chat, bot trả lời như với người lạ
hoàn toàn và chỉ sang số tổng đài.

Nguyên nhân không nằm ở mô hình: `chat_service` chưa bao giờ đọc hồ sơ. Hai nửa
hệ thống dùng chung một mã phiên mà không nửa nào nhìn sang nửa kia.

## Phân biệt ba mức tin cậy, không gộp làm một

Khối chữ này tách rõ **đã xác nhận / đọc từ CV / nghe trong hội thoại**, vì ba
thứ đó không được phép nói bằng cùng một giọng:

- *Đã xác nhận* là ứng viên đã nhìn tận mắt và bấm đồng ý. Dùng được.
- *Đọc từ CV* là máy đọc ra, có câu trích làm chứng, nhưng chưa ai xác nhận. Nói
  về nó thì phải kèm "theo CV bạn gửi".
- *Nghe trong hội thoại* là chuyện khách kể, chưa kiểm chứng gì. Yếu nhất.

Gộp cả ba thành "hồ sơ của bạn" sẽ khiến bot nói chắc nịch về một thứ máy vừa
đoán ra — đúng kiểu hỏng mà toàn bộ ràng buộc R1/R3 sinh ra để chặn.

## "Chưa rõ" khác "không có"

Trường vắng mặt nghĩa là **chưa ai hỏi tới**, không phải ứng viên không có. Khối
chữ nói rõ điều đó, vì mô hình rất dễ tự suy "CV không ghi chứng chỉ" thành
"ứng viên không có chứng chỉ".
"""
from typing import Any

from app.db import candidate_profiles as profiles
from app.matching import catalog


# Thứ tự hiển thị: xếp theo trình tự một người tư vấn thật sẽ hỏi khi gọi điện,
# không theo bảng chữ cái.
THU_TU_NANG_LUC: tuple[str, ...] = (
    "full_name",
    "birth_year",
    "gender",
    "education_level",
    "major",
    "japanese_level",
    "experience_years",
    "care_experience",
)

THU_TU_NGUYEN_VONG: tuple[str, ...] = (
    "desired_prefecture",
    "desired_region_group",
    "desired_employer_type",
    "salary_expectation_jpy",
    "budget_vnd",
    "reason",
)

NHAN: dict[str, str] = {
    "full_name": "Họ tên",
    "birth_year": "Năm sinh",
    "gender": "Giới tính",
    "education_level": "Bằng cấp",
    "major": "Chuyên ngành",
    "japanese_level": "Tiếng Nhật",
    "experience_years": "Kinh nghiệm",
    "care_experience": "Từng chăm sóc người bệnh",
    "desired_prefecture": "Tỉnh mong muốn",
    "desired_region_group": "Vùng mong muốn",
    "desired_employer_type": "Loại cơ sở mong muốn",
    "salary_expectation_jpy": "Lương mong muốn",
    "budget_vnd": "Ngân sách",
    "reason": "Lý do tham gia",
}

# Số điện thoại KHÔNG có trong hai danh sách trên, và đó là chủ ý: không có lý do
# nghiệp vụ nào để bot nhắc lại số của khách trong câu trả lời, nên tốt nhất là
# nó không bao giờ nhìn thấy số ấy. Bộ kiểm chứng ở tầng sau cũng chặn, nhưng
# không đưa vào là lớp rẻ nhất.

TEN_NGUON: dict[str, str] = {
    "user_confirmed": "đã xác nhận",
    "staff": "đã xác nhận",
    "cv": "đọc từ CV, chưa xác nhận",
    "chat": "nghe trong hội thoại, chưa xác nhận",
}

# Gom theo mức tin cậy để mỗi nhóm được nói bằng một giọng khác nhau.
NHOM: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Đã xác nhận", ("user_confirmed", "staff")),
    ("Đọc từ CV, khách chưa xác nhận", ("cv",)),
    ("Khách nói trong hội thoại, chưa xác nhận", ("chat",)),
)


def _gia_tri(key: str, cell: dict[str, Any], labels: dict[str, Any]) -> str | None:
    value = cell.get("value")
    if value is None or value == "":
        return None
    nhan_san = labels.get(key)
    if nhan_san:
        return str(nhan_san)
    if isinstance(value, bool):
        return "Có" if value else "Không"
    if key == "experience_years":
        return f"{value:g} năm"
    if key == "salary_expectation_jpy":
        return f"{int(value):,} yên/tháng".replace(",", ".")
    if key == "budget_vnd":
        return f"{int(value):,} đồng".replace(",", ".")
    if key == "japanese_level":
        return catalog.JAPANESE_LEVEL_LABELS.get(str(value), str(value))
    if key == "education_level":
        return catalog.EDUCATION_LABELS.get(str(value), str(value))
    return str(value)


def _thu_thap(profile: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Mọi ô đã có giá trị, dạng `(nguồn, nhãn, giá trị)`."""
    labels = profile.get("labels") or {}
    fields = profile.get("fields") or {}
    preferences = profile.get("preferences") or {}

    ra: list[tuple[str, str, str]] = []
    for kho, thu_tu in ((fields, THU_TU_NANG_LUC), (preferences, THU_TU_NGUYEN_VONG)):
        for key in thu_tu:
            cell = kho.get(key)
            if not cell:
                continue
            value = _gia_tri(key, cell, labels)
            if value is None:
                continue
            ra.append((cell.get("source", "chat"), NHAN.get(key, key), value))
    return ra


def con_thieu(profile: dict[str, Any]) -> list[str]:
    """Những trường bộ đối chiếu cần mà hồ sơ chưa có.

    Dùng lại đúng thứ tự ưu tiên của bộ đối chiếu (`engine.MISSING_ORDER`) thay
    vì tự đặt một thứ tự khác: nếu hai nơi xếp khác nhau thì bot sẽ hỏi một
    trường mà kết quả đối chiếu chẳng bận tâm, trong khi trường quyết định nhất
    vẫn bỏ trống.
    """
    from app.matching.engine import MISSING_ORDER

    fields = profile.get("fields") or {}
    preferences = profile.get("preferences") or {}
    thieu = []
    for key in MISSING_ORDER:
        kho = preferences if key in profiles.PREFERENCE_KEYS else fields
        if not (kho.get(key) or {}).get("value"):
            thieu.append(key)
    return thieu


def render(profile: dict[str, Any] | None) -> str:
    """Khối chữ đưa vào ngữ cảnh. Rỗng khi chưa biết gì về khách."""
    if not profile:
        return ""

    muc = _thu_thap(profile)
    if not muc:
        return ""

    dong = ["[Đang biết về khách này]"]
    for tieu_de, cac_nguon in NHOM:
        trong_nhom = [m for m in muc if m[0] in cac_nguon]
        if not trong_nhom:
            continue
        dong.append(f"{tieu_de}:")
        dong.extend(f"  - {nhan}: {gia_tri}" for _, nhan, gia_tri in trong_nhom)

    thieu = con_thieu(profile)
    if thieu:
        ten_thieu = ", ".join(NHAN.get(key, key) for key in thieu)
        dong.append(f"Chưa rõ (chưa ai hỏi tới, KHÔNG phải là khách không có): {ten_thieu}")

    # Cảnh báo phải đi KÈM dữ liệu, không để riêng ở phần luật phía trên.
    #
    # Đo trên máy chủ thật ngày 22/09/2026, ngay lượt đầu sau khi khối này được
    # nối vào: bot đáp "Với hồ sơ của bạn, bạn hoàn toàn đủ điều kiện tham gia
    # chương trình". Luật cấm phán quyết đã có sẵn ở prompt và vẫn bị bỏ qua —
    # vì đưa hồ sơ vào làm mô hình **sẵn lòng kết luận hơn hẳn**. Tính năng này
    # tự nó tạo ra cám dỗ ấy, nên nó phải tự mang theo lời cảnh báo.
    #
    # Nói rõ ai mới là người kết luận, chứ không chỉ nói "đừng": mô hình cần một
    # việc thay thế để làm, nếu không nó sẽ lách bằng một cách diễn đạt khác.
    dong.append(
        "(Đây là thông tin của chính người đang nhắn. Đừng hỏi lại những mục đã "
        "có ở trên, và đừng đọc lại cả danh sách cho khách nghe.\n"
        "KHÔNG dùng những thông tin này để kết luận khách đủ hay không đủ điều "
        "kiện, dù nghe có vẻ chắc chắn đến đâu. Việc đối chiếu từng đơn là của "
        "bộ đối chiếu, việc chốt hồ sơ là của nhân viên. Được nói điều kiện của "
        "chương trình và nói thông tin nào của khách còn thiếu — không được nói "
        "khách 'đủ điều kiện', 'hoàn toàn phù hợp' hay 'chắc chắn đi được'.)"
    )
    return "\n".join(dong)


async def context_for(session_id: str) -> str:
    """Đọc hồ sơ của phiên rồi dựng khối chữ. Rỗng nếu phiên chưa có hồ sơ."""
    profile = await profiles.get_by_session(session_id)
    if profile is None:
        return ""
    profiles.decorate(profile)
    return render(profile)
