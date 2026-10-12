"""Tình hình hồ sơ HIỆN TẠI của chính phiên khách — khối ngữ cảnh cho trợ lý (08/10).

Trước 08/10 trợ lý chỉ biết hồ sơ năng lực và kết quả đối chiếu: khách quay lại sau
buổi sơ tuyển vẫn được tư vấn theo CV ban đầu, như thể nhân viên chưa gặp họ. Khối
này đưa thêm đúng những gì nhân viên đã ghi mà khách **được phép biết**, tách năm
loại khác nhau:

1. Năng lực — căn cứ của trình độ tiếng Nhật (tự khai / đã đạt / có chứng chỉ).
2. Nguyện vọng — nằm sẵn ở khối hồ sơ (`context_builder`), không lặp lại ở đây.
3. Tiến độ học — `hoc_tap`, do nhân viên ghi; đang học KHÔNG phải trình độ đã có.
4. Tiến độ hồ sơ đăng ký — theo đúng các chặng khách thấy ở "Hồ sơ của tôi".
5. Trạng thái đơn tuyển dụng — đơn khách đăng ký còn nhận hồ sơ hay không.

## Không bao giờ có ở đây

Ghi chú nội bộ (`note` của hồ sơ đăng ký, `result_note` của lịch hẹn, `internal_note`
của đơn), người phụ trách, điểm nhân viên, và bất cứ thứ gì của khách khác. Cố ý liệt
kê **trường được lấy** chứ không liệt kê trường bị bỏ: thêm một trường nội bộ vào bản
ghi sau này thì nó không tự lọt vào prompt.

Trợ lý chỉ **đọc** khối này. Mọi việc đổi trạng thái vẫn đi qua API riêng và cần khách
hoặc nhân viên xác nhận — không có đường nào từ câu trả lời của mô hình tới database.
"""
import logging
from typing import Any

from app.db import candidate_profiles as profiles

logger = logging.getLogger(__name__)

#: Cùng bảng với `frontend/lib/applicationStages.ts` — có ca kiểm so hai bản.
CHANG_CUA_TRANG_THAI: dict[str, str] = {
    "draft": "Đã đăng ký",
    "collecting_documents": "Đang xem xét",
    "screening": "Đang xem xét",
    "eligible": "Đủ điều kiện sơ bộ",
    "training": "Đủ điều kiện sơ bộ",
    "waiting_interview": "Đủ điều kiện sơ bộ",
    "passed": "Đã trúng tuyển",
    "visa_processing": "Đã trúng tuyển",
    "ready_departure": "Đã trúng tuyển",
    "departed": "Đã xuất cảnh",
    "rejected": "Chưa đạt lần này",
    "withdrawn": "Đã rút hồ sơ",
    "cancelled": "Đã hủy đăng ký",
}

NHAN_HO_TRO = {"nhan_tin": "nhắn tin cho nhân viên", "hoc_tap": "tư vấn việc học", "gap_mat": "xin gặp nhân viên"}
NHAN_TT_HO_TRO = {"cho_xu_ly": "đang chờ nhân viên nhận", "dang_xu_ly": "nhân viên đang xử lý",
                  "da_xong": "nhân viên đã trả lời", "da_huy": "đã hủy"}
NHAN_TT_LICH = {"pending": "chờ xác nhận", "confirmed": "đã xác nhận", "completed": "đã diễn ra",
                "cancelled": "đã hủy", "no_show": "khách không đến"}


async def nap(session_id: str, profile: dict[str, Any] | None) -> dict[str, Any]:
    """Đọc những gì được phép chia sẻ cho phiên này. **Không ném lỗi** — thiếu thì bỏ.

    Một lần đọc tiến độ trục trặc không được làm hỏng lượt tư vấn của khách: thiếu
    khối này thì trợ lý vẫn trả lời theo hồ sơ và kết quả đối chiếu như trước 08/10.
    """
    ra: dict[str, Any] = {"tieng_nhat": profiles.trang_thai_tieng_nhat(profile)}
    for ten, viec in (("dang_ky", _dang_ky), ("lich_hen", _lich_hen), ("ho_tro", _ho_tro)):
        try:
            ra.update(await viec(session_id))
        except Exception:  # noqa: BLE001 — xem docstring
            logger.warning("Không đọc được %s cho phiên %s", ten, session_id, exc_info=True)
    ra["de_xuat_cho"] = [
        {"muc": c.get("field"), "ban_noi": c.get("suggested")}
        for c in profiles.de_xuat_dang_cho(profile or {})
    ]
    return ra


async def _dang_ky(session_id: str) -> dict[str, Any]:
    from app.db import job_orders
    from app.db.database import list_unassigned_registrations

    ra: dict[str, Any] = {}
    don = await list_unassigned_registrations(session_id=session_id, include_assigned=True, limit=10)
    ra["dang_ky"] = [
        {
            "ma_don": d.get("job_order_code"),
            "ten_don": d.get("job_order_title"),
            "chang": CHANG_CUA_TRANG_THAI.get(d.get("status") or "", "Đang xử lý"),
            "cap_nhat": str(d.get("updated_at") or d.get("created_at") or "")[:10],
        }
        for d in don
    ]
    trang_thai_don: dict[str, str] = {}
    for d in ra["dang_ky"]:
        ma = d.get("ma_don")
        if ma and ma not in trang_thai_don:
            cong_khai = await job_orders.get_job_order(ma, public=True)
            trang_thai_don[ma] = "còn nhận hồ sơ" if cong_khai else "hiện không nhận hồ sơ mới"
    ra["trang_thai_don"] = trang_thai_don
    return ra


async def _lich_hen(session_id: str) -> dict[str, Any]:
    from app.db.database import list_appointments_for_session

    return {"lich_hen": [
        {
            "ngay": l.get("appointment_date"),
            "gio": l.get("appointment_time"),
            "hinh_thuc": "trực tuyến" if l.get("meeting_kind") == "truc_tuyen" else (
                "trực tiếp" if l.get("meeting_kind") == "truc_tiep" else None),
            "trang_thai": NHAN_TT_LICH.get(l.get("status") or "", l.get("status")),
        }
        for l in await list_appointments_for_session(session_id, limit=5)
    ]}


async def _ho_tro(session_id: str) -> dict[str, Any]:
    from app.db import support_requests

    return {"ho_tro": [
        {"loai": NHAN_HO_TRO.get(y.get("kind") or "", y.get("kind")),
         "trang_thai": NHAN_TT_HO_TRO.get(y.get("status") or "", y.get("status"))}
        for y in await support_requests.list_for_session(session_id, limit=5)
    ]}


def render(td: dict[str, Any] | None) -> str:
    """Khối chữ cho prompt. Rỗng khi không có gì ngoài hồ sơ đã có ở khối khác."""
    if not td:
        return ""
    from app.consultation.context_builder import NHAN

    dong = ["[Tình hình hồ sơ hiện tại — do hệ thống và nhân viên ghi, mới nhất]"]
    tn = td.get("tieng_nhat") or {}
    if tn.get("nhan"):
        dong.append(f"- Tiếng Nhật đang có: {tn['nhan']}.")
    if tn.get("dang_hoc"):
        dong.append(f"- Việc học: {tn['dang_hoc']['nhan']}.")
    if tn.get("chuong_trinh"):
        # Không phải trình độ đã xác minh; đối chiếu đơn vẫn theo dòng "Tiếng Nhật đang có".
        dong.append(f"- Học tại trung tâm: {tn['chuong_trinh']['nhan']}.")
    for d in td.get("dang_ky") or ():
        tt = (td.get("trang_thai_don") or {}).get(d.get("ma_don"), "")
        dong.append(
            f"- Đã đăng ký đơn {d.get('ma_don')}"
            + (f" ({d['ten_don']})" if d.get("ten_don") else "")
            + f": chặng \"{d.get('chang')}\""
            + (f"; đơn {tt}" if tt else "")
            + "."
        )
    for l in td.get("lich_hen") or ():
        dong.append(
            f"- Lịch hẹn {l.get('ngay')} {l.get('gio') or ''}".rstrip()
            + (f", {l['hinh_thuc']}" if l.get("hinh_thuc") else "")
            + f": {l.get('trang_thai')}."
        )
    for y in td.get("ho_tro") or ():
        dong.append(f"- Yêu cầu {y.get('loai')}: {y.get('trang_thai')}.")
    for c in td.get("de_xuat_cho") or ():
        dong.append(
            f"- Khách vừa nói {NHAN.get(c.get('muc'), c.get('muc'))} khác điều nhân viên đã ghi; "
            "nhân viên sẽ xem lại. Chưa đổi gì."
        )
    if len(dong) == 1:
        return ""
    dong.append(
        "(Chỉ nói lại đúng những điều trên. KHÔNG tự suy ra chặng tiếp theo, KHÔNG hứa "
        "kết quả, KHÔNG nói đã đổi hay sẽ đổi trạng thái nào — việc ấy là của nhân viên. "
        "\"Đang học\" là CHƯA đạt trình độ ấy. \"Hoàn thành chương trình tại trung tâm\" "
        "CHƯA phải chứng chỉ — không nói khách đã đủ yêu cầu chứng chỉ của đơn.)"
    )
    return "\n".join(dong)
