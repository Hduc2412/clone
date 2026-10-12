"""Bản tối thiểu của một việc trong hàng đợi — đủ để nhận việc, không đủ để đọc hồ sơ.

## Quy tắc (yêu cầu 08/10/2026)

Việc **chưa ai nhận** thì mọi nhân viên phải thấy, không thì không ai nhận được. Nhưng
"thấy việc" khác "đọc hồ sơ": số điện thoại, lời nhắn, bản bàn giao, phiếu tóm tắt, CV
và hội thoại chỉ mở cho **người đang giữ việc** hoặc quản lý. Muốn đọc thì bấm nhận —
việc nhận là atomic (`claim`/`accept`), nên hai người không cùng mở được một khách.

Trước 08/10 hai hàng đợi cố ý trả nguyên bản ghi "để đọc rồi mới quyết định nhận"
(xem E2E cũ, bước 9–10). Kiểm sống ngày 08/10 cho thấy cách ấy cũng mở luôn cửa đọc
việc **người khác đang giữ** qua `?status=dang_xu_ly` và gọi thẳng chi tiết.

## Bản tối thiểu gồm gì

Loại việc, đơn liên quan, lúc gửi, có lịch hẹn hay không, và tên viết tắt để phân biệt
hai dòng — không có họ tên đầy đủ, số điện thoại, lời nhắn hay bất cứ khối nào dựng từ
hồ sơ. Cố ý liệt kê **những gì được giữ** thay vì liệt kê những gì phải bỏ: thêm một
trường nhạy cảm mới vào bản ghi thì nó không tự lọt ra đây.
"""
from typing import Any

#: Trường được giữ trong bản tối thiểu của yêu cầu hỗ trợ.
GIU_HO_TRO = ("code", "kind", "status", "job_order_code", "created_at", "assigned_to")

#: Trường được giữ trong bản tối thiểu của hồ sơ đăng ký.
GIU_DANG_KY = (
    "application_code", "job_order_code", "job_order_title", "status", "source",
    "created_at", "updated_at", "assigned_to", "is_active",
)


def ten_viet_tat(ho_ten: str | None) -> str:
    """"Lê Thị Minh" → "L. T. M." — đủ để phân biệt hai dòng, không đủ để nhận ra người."""
    chu = [p[0].upper() for p in (ho_ten or "").split() if p]
    return " ".join(f"{c}." for c in chu) if chu else "Khách"


def ho_tro(doc: dict[str, Any]) -> dict[str, Any]:
    ra = {k: doc.get(k) for k in GIU_HO_TRO}
    ra["ten_viet_tat"] = ten_viet_tat(doc.get("full_name"))
    ra["co_lich_hen"] = bool(doc.get("appointment_code"))
    ra["ban_toi_thieu"] = True
    return ra


def dang_ky(doc: dict[str, Any]) -> dict[str, Any]:
    ra = {k: doc.get(k) for k in GIU_DANG_KY}
    ra["ten_viet_tat"] = ten_viet_tat(doc.get("customer_name") or doc.get("full_name"))
    ra["ban_toi_thieu"] = True
    return ra
