"""Đơn quá hạn nộp mà vẫn "Đang tuyển": tự ẩn rồi báo Admin gỡ (12/10).

Đơn qua hạn **đã tự ẩn** khỏi website từ trước (`job_orders.public_filter` lọc theo
hạn lúc đọc), nên khách không thấy nó nữa. Nhưng trên màn quản trị nó vẫn để "Đang
tuyển" cho tới khi có người đổi — và chưa ai được báo. Module này báo.

- **Không tự đổi trạng thái.** Chủ đồ án chốt: ẩn rồi báo Admin để gỡ. Gỡ (chuyển "Hết
  hạn" hay "Đã đóng") vẫn là quyết định của người, và được ghi lịch sử theo tên người đó.
- **Mỗi đơn, mỗi hạn nộp — một thông báo.** Quét lại không sinh thêm. Admin gia hạn đơn
  rồi đơn lại quá hạn mới thì là hạn mới, có thông báo mới.
- Quét lúc khởi động và định kỳ (`chay_dinh_ky`). Thông báo cũ được tắt khi Admin đổi
  trạng thái đơn ấy (`api/job_orders.change_job_order_status`).
"""
from __future__ import annotations

import asyncio
import logging

from app.db import job_orders as don_store
from app.db.common import get_db
from app.services.chi_tieu import REFERENCE_JOB_ORDER, bao_admin

logger = logging.getLogger(__name__)

LOAI = "job_order.expired"
#: 30 phút: hạn nộp tính theo ngày, quét dày hơn cũng không thêm gì.
CHU_KY_GIAY = 30 * 60


def _ngay_vn(iso: str) -> str:
    y, m, d = (iso or "")[:10].split("-") if iso and len(iso) >= 10 else ("", "", "")
    return f"{d}/{m}/{y}" if d else iso


async def quet(today: str | None = None) -> list[str]:
    """Báo những đơn quá hạn chưa gỡ, chưa từng được báo cho hạn này. Trả mã đơn vừa báo."""
    da_bao: list[str] = []
    for don in await don_store.don_qua_han_chua_go(today):
        da_co = await get_db().notifications.find_one({
            "type": LOAI, "reference_type": REFERENCE_JOB_ORDER,
            "reference_code": don["code"], "detail.deadline": don["deadline"],
        })
        if da_co:
            continue
        await bao_admin(
            LOAI, don["code"],
            f"Đơn {don['code']} ({don.get('title', '')}) đã hết hạn nộp hồ sơ ngày {_ngay_vn(don['deadline'])} "
            f"và đã tự ẩn khỏi website. Hãy gỡ đơn: chuyển sang \"Hết hạn\" hoặc \"Đã đóng\".",
            {"deadline": don["deadline"]},
        )
        da_bao.append(don["code"])
    if da_bao:
        logger.info("Đơn quá hạn chưa gỡ, vừa báo Admin: %s", ", ".join(da_bao))
    return da_bao


async def chay_dinh_ky(chu_ky_giay: float = CHU_KY_GIAY) -> None:
    """Vòng quét nền. Một lần quét hỏng không được làm dừng vòng."""
    while True:
        try:
            await quet()
        except Exception:  # noqa: BLE001
            logger.exception("Quét đơn quá hạn không thành công; thử lại ở chu kỳ sau.")
        await asyncio.sleep(chu_ky_giay)
