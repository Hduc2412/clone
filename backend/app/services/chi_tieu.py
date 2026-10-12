"""Chỉ tiêu của đơn tuyển dụng — đếm, tự ẩn khi đủ, trả lại khi rút (12/10).

## Luật (chủ đồ án chốt 12/10)

- **Đăng ký không đổi gì.** Khách bấm đăng ký, nhân viên nhận hồ sơ, sơ tuyển đạt —
  chỉ tiêu vẫn nguyên.
- **Trừ một chỉ tiêu khi hồ sơ chuyển sang "Trúng tuyển"** (`passed`): cơ sở bên Nhật
  đã nhận người. Đơn vẫn mở trong lúc phỏng vấn, vì cơ sở thường phỏng vấn nhiều người
  hơn chỉ tiêu.
- **Đủ chỉ tiêu → "Đã hoàn thành chỉ tiêu"** (`filled`) và tự ẩn khỏi website
  (`job_orders.increment_hired`), rồi báo Admin/Manager.
- **Người đã tính mà rút hoặc bị hủy → trả lại một chỉ tiêu và báo Admin.** Đơn KHÔNG
  tự mở lại; Admin tự bấm mở nếu muốn tuyển bù.

## Mỗi hồ sơ chỉ tính một lần

Hồ sơ mang dấu `chi_tieu` (mã đơn + lúc tính) ngay khi được tính, đặt bằng một lệnh
nguyên tử chỉ khớp khi dấu chưa có. Nhân viên bấm "Trúng tuyển" hai lần, hay hai người
bấm cùng lúc, thì chỉ một lần đi qua. Trả lại cũng vậy: gỡ dấu trước, thành công mới
trừ — nên không trả hai lần cho một người.

Hồ sơ không gắn đơn nào (nhân viên tạo tay, không qua đăng ký) thì không tính vào đâu.
"""
from __future__ import annotations

import logging
from typing import Any

from app.db import job_orders as don_store
from app.db.common import get_db, now

logger = logging.getLogger(__name__)

TINH = "passed"
TRA_LAI = ("withdrawn", "cancelled")
REFERENCE_JOB_ORDER = "job_order"


async def _danh_dau(application_code: str, ma_don: str) -> bool:
    ra = await get_db().recruitment_applications.update_one(
        {"application_code": application_code, "chi_tieu": {"$exists": False}},
        {"$set": {"chi_tieu": {"job_order_code": ma_don, "luc": now()}}},
    )
    return ra.modified_count == 1


async def _go_dau(application_code: str) -> str | None:
    doc = await get_db().recruitment_applications.find_one_and_update(
        {"application_code": application_code, "chi_tieu": {"$exists": True}},
        {"$unset": {"chi_tieu": ""}},
        projection={"_id": 0, "chi_tieu": 1},
    )
    return ((doc or {}).get("chi_tieu") or {}).get("job_order_code")


async def bao_admin(loai: str, ma_don: str, tieu_de: str, chi_tiet: dict[str, Any] | None = None) -> None:
    """Thông báo về một đơn — chỉ Admin/Manager thấy (`list_notifications` lọc theo loại)."""
    from app.db.database import create_notification

    await create_notification(
        notification_type=loai,
        title=tieu_de,
        reference_type=REFERENCE_JOB_ORDER,
        reference_code=ma_don,
        detail=chi_tiet or {},
    )


async def khi_doi_trang_thai(application: dict[str, Any], trang_thai_moi: str) -> dict[str, Any] | None:
    """Gọi SAU khi hồ sơ đã đổi trạng thái thành công. Trả đơn sau khi cập nhật, nếu có.

    Không bao giờ ném lỗi ra ngoài: hồ sơ đã đổi trạng thái rồi, một lỗi ở đây không
    được làm nhân viên tưởng thao tác của họ hỏng. Lỗi ghi log để đối soát.
    """
    try:
        if trang_thai_moi == TINH:
            return await _tinh(application)
        if trang_thai_moi in TRA_LAI:
            return await _tra(application, trang_thai_moi)
    except Exception:  # noqa: BLE001 — xem docstring
        logger.exception("Chỉ tiêu: không cập nhật được cho hồ sơ %s", application.get("application_code"))
    return None


async def _tinh(application: dict[str, Any]) -> dict[str, Any] | None:
    ma_don = application.get("job_order_code")
    if not ma_don:
        return None
    if not await _danh_dau(application["application_code"], ma_don):
        return None  # đã tính rồi
    don = await don_store.increment_hired(ma_don)
    if don is None:
        logger.warning("Chỉ tiêu: hồ sơ %s trỏ tới đơn %s không còn", application["application_code"], ma_don)
        return None
    if don.get("status") == "filled":
        await bao_admin(
            "job_order.filled", ma_don,
            f"Đơn {ma_don} đã đủ chỉ tiêu ({don.get('hired_count')}/{don.get('quota')}) — đã chuyển sang "
            f"\"Đã hoàn thành chỉ tiêu\" và tự ẩn khỏi website.",
            {"hired_count": don.get("hired_count"), "quota": don.get("quota")},
        )
    return don


async def _tra(application: dict[str, Any], trang_thai_moi: str) -> dict[str, Any] | None:
    ma_don = await _go_dau(application["application_code"])
    if not ma_don:
        return None  # chưa từng được tính
    don = await don_store.decrement_hired(ma_don)
    if don is None:
        return None
    ly_do = "rút hồ sơ" if trang_thai_moi == "withdrawn" else "bị hủy"
    them = (
        " Đơn đang ở \"Đã hoàn thành chỉ tiêu\" và vẫn ẩn — mở lại nếu muốn tuyển bù."
        if don.get("status") == "filled" else ""
    )
    await bao_admin(
        "job_order.slot_released", ma_don,
        f"Đơn {ma_don}: một người đã trúng tuyển {ly_do} ({application['application_code']}) — trả lại 1 chỉ "
        f"tiêu, còn {don.get('hired_count')}/{don.get('quota')}.{them}",
        {"application_code": application["application_code"], "hired_count": don.get("hired_count"),
         "quota": don.get("quota")},
    )
    return don
