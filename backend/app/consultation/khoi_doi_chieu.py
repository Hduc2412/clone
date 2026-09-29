"""Dựng lại khối kết quả đối chiếu — **ở máy chủ, không nhận từ trình duyệt**.

## Vì sao có module này

Khi khách chưa phù hợp và bấm "xin gặp nhân viên", yêu cầu hỗ trợ đi kèm khối kết
quả đối chiếu họ vừa nhìn thấy. Nhân viên đọc nó trước khi gọi điện là biết ngay
khách vướng ở đâu, thay vì bắt một người vừa bị từ chối kể lại từ đầu.

Bản trước **nhận khối ấy từ thân yêu cầu và lưu nguyên văn**. Trình duyệt gửi gì
thì máy chủ tin nấy — nên khách sửa được trước khi gửi, và nhân viên đọc một bản
"kết quả đối chiếu" không phải do bộ đối chiếu sinh ra. Đúng cùng một loại sai với
việc tin mã phiên do trình duyệt tự đặt, mà chỗ ấy đã sửa từ 22/09.

Nay máy chủ tự dựng lại từ nhật ký giới thiệu. Thân yêu cầu không còn trường nào
nhận chữ ấy, nên không ai lỡ tay tin vào nó được nữa.

## Vì sao dựng lại từ nhật ký, không đối chiếu lại

Đối chiếu lại tại thời điểm gửi yêu cầu sẽ cho ra kết quả của **lúc này**, còn thứ
nhân viên cần là thứ **khách đã nhìn thấy lúc bấm nút**. Hai cái lệch nhau khi đơn
vừa hết hạn hoặc khách vừa sửa hồ sơ — và lúc ấy nhân viên gọi điện bàn về một
kết quả khách chưa từng thấy.

Nhật ký giới thiệu chính là ảnh chụp ấy, có sẵn, và có `profile_version` để biết
nó chụp hồ sơ ở trạng thái nào.
"""
from typing import Any

from app.db import candidate_profiles as profiles
from app.db import courses, job_orders
from app.db import recommendation_logs as logs


def dong_cua_don(log: dict[str, Any], code: str) -> dict[str, Any] | None:
    """Dòng nói về đúng đơn này trong nhật ký. `None` nếu nhật ký không có nó."""
    for row in log.get("items") or ():
        if row.get("code") == code:
            return row
    return None


def trinh_do(profile: dict[str, Any]) -> str | None:
    return ((profile.get("fields") or {}).get("japanese_level") or {}).get("value")


async def yeu_cau_tieng_nhat(code: str) -> str | None:
    """Mức tiếng Nhật đơn yêu cầu — để dựng lộ trình học.

    Phải tra lại bản ghi đơn vì nhật ký giới thiệu **không lưu** khối
    `requirements`: `MatchItem` chỉ giữ các dòng tiêu chí đã chấm, không giữ dữ
    liệu gốc của đơn. Đọc `requirement_text` của dòng tiếng Nhật rồi bóc chữ "N4"
    ra khỏi câu cũng được, nhưng đó là phân tích câu chữ hiển thị — đổi cách viết
    nhãn một lần là lộ trình học lặng lẽ sai.

    Đơn có thể đã đổi giữa lúc đối chiếu và lúc gọi hàm này. Khoảng lệch ấy tính
    bằng giây, và nếu đơn đổi thật thì dấu vân tay danh mục đổi theo nên lần đối
    chiếu kế tiếp tự chạy lại.
    """
    don = await job_orders.get_job_order(code, public=True)
    if don is None:
        return None
    return (don.get("requirements") or {}).get("japanese_required")


def thanh_match_item(row: dict[str, Any]):
    """Dựng lại `MatchItem` từ dòng nhật ký đã lưu.

    Nhật ký lưu dạng dict để tuần tự hóa được; `advice` và `explain` thì nhận
    `MatchItem`. Dựng lại ở đây thay vì để hai module kia nhận cả hai kiểu — nhận
    hai kiểu là chỗ sinh lỗi im lặng khi một bên đổi hình dạng.
    """
    from app.matching.engine import CriterionRow, MatchItem, SoftRow

    return MatchItem(
        code=row.get("code") or "",
        title=row.get("title") or "",
        employer_name=row.get("employer_name") or "",
        prefecture=row.get("prefecture") or "",
        region_group=row.get("region_group"),
        employer_type=row.get("employer_type") or "",
        program=row.get("program") or "",
        deadline=row.get("deadline") or "",
        eligible=bool(row.get("eligible")),
        score=int(row.get("score") or 0),
        rank=row.get("rank"),
        hard_rows=tuple(CriterionRow(**dong) for dong in row.get("hard_rows") or ()),
        soft_rows=tuple(SoftRow(**dong) for dong in row.get("soft_rows") or ()),
        gaps=tuple(row.get("gaps") or ()),
        missing_info=tuple(row.get("missing_info") or ()),
        labels=row.get("labels") or {},
    )


async def dung_tu_nhat_ky(session_id: str, job_order_code: str) -> str | None:
    """Khối chữ khách đã nhìn thấy về đơn này. `None` nếu chưa từng xem đơn.

    `None` là kết quả hợp lệ và hay gặp: khách gửi yêu cầu hỗ trợ từ ngoài luồng
    tư vấn theo đơn, hoặc gửi trước khi hồ sơ được đối chiếu. Lúc ấy yêu cầu vẫn
    đi vào hàng đợi, chỉ là không kèm kết quả đối chiếu — và màn hình quản trị nói
    rõ điều đó thay vì để một khoảng trống không ai hiểu.
    """
    from app.consultation import advice as advice_builder

    if not job_order_code:
        return None

    profile = await profiles.get_by_session(session_id)
    if profile is None:
        return None

    log = await logs.tim_don_da_gioi_thieu(
        profile_code=profile["code"],
        profile_version=int(profile.get("version", 1)),
        job_order_code=job_order_code,
    )
    if log is None:
        return None

    row = dong_cua_don(log, job_order_code)
    if row is None:
        return None

    ket_qua = advice_builder.build(
        thanh_match_item(row),
        required_japanese=await yeu_cau_tieng_nhat(job_order_code),
        profile_level=trinh_do(profile),
        courses=await courses.list_published(),
        profile_confirmed=profile.get("status") == profiles.STATUS_CONFIRMED,
    )
    return ket_qua.block
