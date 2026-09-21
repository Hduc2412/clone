"""Dựng nội dung Phiếu tóm tắt tư vấn.

**Không gọi mô hình ngôn ngữ.** Cả module không import gì liên quan tới nó, và có
một ca kiểm thử khẳng định điều đó — giống `app/matching/explain.py`.

Lý do: phiếu là thứ nhân viên đọc rồi gọi điện nói lại với ứng viên. Một câu chữ
mượt mà nhưng sai một con số ở đây sẽ đi thẳng ra ngoài qua miệng người thật. Mọi
dòng trong phiếu vì vậy đều chép từ dữ liệu có sẵn: hồ sơ, đơn hàng, và khối lý
do do bộ đối chiếu sinh ra.

Phiếu được dựng thành **chữ thuần**, không phải HTML hay PDF. Nhân viên cần đọc
nhanh trên màn hình, dán được vào tin nhắn nội bộ, và in ra giấy cũng đọc được.
"""
from typing import Any

from app.matching import catalog
from app.db.candidate_profiles import consultation_view

# Thứ tự các trường trong phiếu. Xếp theo trình tự nhân viên hỏi khi gọi điện,
# không phải theo thứ tự bảng chữ cái.
FIELD_ORDER: tuple[tuple[str, str], ...] = (
    ("full_name", "Họ và tên"),
    ("birth_year", "Năm sinh"),
    ("gender", "Giới tính"),
    ("phone", "Điện thoại"),
    ("education_level", "Bằng cấp"),
    ("major", "Chuyên ngành"),
    ("japanese_level", "Tiếng Nhật"),
    ("experience_years", "Kinh nghiệm"),
    ("care_experience", "Từng chăm sóc người bệnh"),
)

PREFERENCE_ORDER: tuple[tuple[str, str], ...] = (
    ("desired_prefecture", "Tỉnh mong muốn"),
    ("desired_region_group", "Vùng mong muốn"),
    ("desired_employer_type", "Loại cơ sở"),
    ("salary_expectation_jpy", "Lương mong muốn"),
    ("budget_vnd", "Ngân sách"),
    ("reason", "Lý do tham gia"),
    ("notes", "Ghi chú"),
)

SOURCE_NOTE = {
    "cv": "đọc từ CV",
    "chat": "nghe trong hội thoại",
    "user_confirmed": "ứng viên xác nhận",
    "staff": "nhân viên nhập",
}


def build(
    *,
    profile: dict[str, Any],
    order_item: dict[str, Any],
    explanation_block: str,
    documents: list[dict[str, Any]],
) -> dict[str, Any]:
    """Bản chụp đầy đủ của phiếu: vừa phần chữ để đọc, vừa dữ liệu thô để tra."""
    return {
        "candidate": _snapshot(profile),
        "consultation_profile": consultation_view(profile),
        "job_order": {
            "code": order_item.get("code"),
            "title": order_item.get("title"),
            "employer_name": order_item.get("employer_name"),
            "prefecture": order_item.get("prefecture"),
            "score": order_item.get("score"),
            "rank": order_item.get("rank"),
            "eligible": order_item.get("eligible"),
        },
        "explanation_block": explanation_block,
        "gaps": list(order_item.get("gaps") or ()),
        "missing_info": list(order_item.get("missing_info") or ()),
        "documents": [
            {"code": item.get("code"), "filename": item.get("filename"), "status": item.get("status")}
            for item in documents
        ],
        "text": render_text(
            profile=profile,
            order_item=order_item,
            explanation_block=explanation_block,
            documents=documents,
        ),
    }


def render_text(
    *,
    profile: dict[str, Any],
    order_item: dict[str, Any],
    explanation_block: str,
    documents: list[dict[str, Any]],
) -> str:
    # Gom từng mục lại rồi mới đánh số. Đánh số cứng sẵn thì mục rỗng bị bỏ đi
    # vẫn giữ chỗ của nó, và người đọc thấy phiếu nhảy từ 1 sang 3 sang 6 — trông
    # y như phiếu bị mất trang.
    sections: list[tuple[str, list[str]]] = [
        ("ỨNG VIÊN", _section(profile, profile.get("fields") or {}, FIELD_ORDER)),
        (
            "NGUYỆN VỌNG ỨNG VIÊN NÓI",
            _section(profile, profile.get("preferences") or {}, PREFERENCE_ORDER),
        ),
        (
            "ĐƠN ỨNG VIÊN ĐÃ CHỌN",
            [
                f"   {order_item.get('code')} · {order_item.get('title')}",
                f"   {order_item.get('employer_name')} · {order_item.get('prefecture')}",
            ],
        ),
        ("VÌ SAO HỆ THỐNG CHO LÀ PHÙ HỢP", _indent(explanation_block)),
        (
            "ĐIỂM CÒN THIẾU — CẦN HỎI THÊM KHI GỌI",
            [f"   - {gap}" for gap in (order_item.get("gaps") or ())],
        ),
        (
            "THÔNG TIN CHƯA RÕ",
            [f"   - {item}" for item in (order_item.get("missing_info") or ())],
        ),
        (
            "TÀI LIỆU ỨNG VIÊN ĐÃ GỬI",
            [f"   - {item.get('filename')} ({item.get('code')})" for item in documents],
        ),
    ]

    lines: list[str] = ["PHIẾU TÓM TẮT TƯ VẤN"]
    context = consultation_view(profile)
    sections.append(("HỘI THOẠI GẦN ĐÂY — CHƯA PHẢI THÔNG TIN ĐÃ XÁC NHẬN", [
        f"   - {item['content']}" for item in context.get("recent_messages", [])
    ]))
    sections.append(("THÔNG TIN MÂU THUẪN CẦN KIỂM TRA", [
        f"   - {item['field']}: {item['previous']} / {item['suggested']}"
        for item in context.get("conflicts", [])
    ]))
    number = 0
    for title, body in sections:
        if not body:
            continue
        number += 1
        lines += ["", f"{number}. {title}", *body]

    lines += [
        "",
        "Phiếu lập từ dữ liệu đã lưu; nguồn và thông tin chưa xác nhận được ghi riêng.",
        "Mọi con số trong phiếu cần được kiểm chứng lại khi gọi điện.",
    ]
    return "\n".join(lines)


def _section(
    profile: dict[str, Any],
    cells: dict[str, Any],
    order: tuple[tuple[str, str], ...],
) -> list[str]:
    labels = profile.get("labels") or {}
    lines: list[str] = []
    for key, title in order:
        cell = cells.get(key)
        if not cell:
            continue
        value = _value_text(key, cell.get("value"), labels.get(key))
        if value is None:
            continue
        note = SOURCE_NOTE.get(cell.get("source", ""), cell.get("source", ""))
        lines.append(f"   {title}: {value}  [{note}]")
    return lines


def _value_text(key: str, value: Any, label: str | None) -> str | None:
    if value is None or value == "":
        return None
    if label:
        return label
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


def _snapshot(profile: dict[str, Any]) -> dict[str, Any]:
    """Chép lại hồ sơ, giữ nguyên nguồn của từng giá trị."""
    return {
        "code": profile.get("code"),
        "version": profile.get("version"),
        "fields": profile.get("fields") or {},
        "preferences": profile.get("preferences") or {},
        "labels": profile.get("labels") or {},
    }


def _indent(block: str) -> list[str]:
    return [f"   {line}" for line in block.splitlines()] if block else []
