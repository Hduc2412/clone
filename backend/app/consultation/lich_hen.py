"""Hẹn gặp nhân viên **từ hành trình tư vấn** — không qua khung chat.

## Khoảng trống này tồn tại từ đầu

Lần rà soát 01/10 lần ngược `create_appointment` và tìm ra đúng **một** nơi gọi:
`booking/booking_service.py`, tức khung chat ở góc màn hình. Hành trình chính
trên website — chọn đơn, gửi CV, đối chiếu, xin gặp mặt — không có đường nào tạo
ra một lịch hẹn.

Hệ quả cụ thể: khách bấm "Xin gặp mặt", yêu cầu vào hàng đợi hỗ trợ, nhân viên
đọc rồi phải **tự gọi điện hỏi lại giờ nào tiện** — trong khi khách vừa ngồi
trước màn hình và sẵn sàng chọn. Và màn hình `/admin/appointments` thì luôn trống
với ai chỉ đi theo hành trình mới; chính dòng chữ trên đó thừa nhận: *"chờ lịch
mới từ chatbot"*.

## Vì sao không sửa `booking_service.py` để dùng chung

Nó thuộc phần khung chat, và nó đang chạy đúng. Sửa một luồng đang chạy để lấy
chỗ dùng chung là đánh đổi sai: cái giá là rủi ro làm gãy luồng của bên kia, cái
được chỉ là bớt một bản sao quy tắc.

Nên quy tắc giờ được khai lại ở đây, **và có ca kiểm thử bắt hai bên lệch nhau**
(`tests/test_lich_hen.py`). Bản sao có người canh thì an toàn; bản sao không ai
canh mới là nợ.

## Chặn đúng khoảng nghỉ trưa

`consultation/lien_he.GIO_LIEN_HE` ghi "8h đến 17h" — cố ý gọn, vì đó là giờ
**trả lời tin nhắn** và bắt khách nhớ hai khoảng rời nhau chỉ để gửi một câu hỏi
là rào cản không cần thiết.

Đặt lịch thì khác: giờ phải chính xác, vì có người thật phải có mặt. Nên ở đây
chặn đúng hai khoảng, và khoảng nghỉ trưa bị từ chối.
"""
import re
import secrets
from datetime import date, datetime, timedelta
from typing import Any

from app.core.timeutil import local_today


# Hai khoảng nhận lịch, tính theo phút từ nửa đêm.
KHUNG_SANG = (8 * 60, 11 * 60 + 30)
KHUNG_CHIEU = (13 * 60 + 30, 17 * 60)

#: Chủ Nhật không nhận lịch. `date.weekday()` trả 6 cho Chủ Nhật.
NGAY_NGHI = (6,)

#: Hẹn xa nhất bao nhiêu ngày. Xa hơn thì đơn có thể đã hết hạn hoặc đủ người,
#: và một cái hẹn ba tháng sau thì đến lúc gọi cả hai bên đều quên mất vì sao hẹn.
TOI_DA_NGAY = 30

# Nới ở **định dạng**, siết ở **quy tắc nghiệp vụ**.
#
# `<input type="time">` luôn gửi `HH:MM`, nên bản chặt hai chữ số phút cũng chạy
# được với giao diện hiện tại. Nhưng ai gọi API trực tiếp — hay một giao diện
# khác sau này — có thể gửi `9:5`, và từ chối nó là từ chối một ý định rõ ràng vì
# một chuyện hình thức. Phút một chữ số được nhận rồi tự đệm 0.
#
# Giờ ngoài khoảng làm việc thì vẫn bị từ chối như cũ: đó mới là quy tắc.
_GIO = re.compile(r"^([01]?\d|2[0-3]):([0-5]?\d)$")


class GioKhongHopLe(ValueError):
    """Giờ hoặc ngày nằm ngoài khoảng nhận lịch. Lời nhắn đọc được cho khách."""


def kiem_gio(gio: str) -> str:
    """Chuẩn hóa `"8:0"` thành `"08:00"`, từ chối giờ ngoài khoảng.

    Ném `GioKhongHopLe` kèm câu nói rõ hai khoảng, không phải "giá trị không hợp
    lệ" — khách cần biết chọn lại giờ nào, không cần biết mình vừa sai cú pháp.
    """
    khop = _GIO.match((gio or "").strip())
    if not khop:
        raise GioKhongHopLe(
            "Giờ cần viết theo dạng 09:30. Nhận lịch 08:00–11:30 hoặc 13:30–17:00."
        )
    phut = int(khop.group(1)) * 60 + int(khop.group(2))
    trong_khung = (
        KHUNG_SANG[0] <= phut <= KHUNG_SANG[1]
        or KHUNG_CHIEU[0] <= phut <= KHUNG_CHIEU[1]
    )
    if not trong_khung:
        raise GioKhongHopLe(
            "Giờ nhận lịch là 08:00–11:30 hoặc 13:30–17:00, "
            "từ thứ Hai đến thứ Bảy. Bạn chọn lại giúp mình nhé."
        )
    # Đệm 0 cho cả giờ và phút: "9:5" ra "09:05".
    return f"{int(khop.group(1)):02d}:{int(khop.group(2)):02d}"


def kiem_ngay(ngay: str) -> str:
    """Ngày phải trong tương lai gần và không phải Chủ Nhật."""
    try:
        d = date.fromisoformat((ngay or "").strip())
    except ValueError:
        raise GioKhongHopLe("Ngày cần viết theo dạng 2026-10-20.") from None

    hom_nay = local_today()
    if d < hom_nay:
        raise GioKhongHopLe("Ngày hẹn đã qua. Bạn chọn một ngày sắp tới nhé.")
    if d > hom_nay + timedelta(days=TOI_DA_NGAY):
        raise GioKhongHopLe(
            f"Mình nhận lịch trong {TOI_DA_NGAY} ngày tới. Xa hơn thì bạn để lại "
            "tin nhắn, nhân viên sẽ hẹn lại cho đúng thời điểm."
        )
    if d.weekday() in NGAY_NGHI:
        raise GioKhongHopLe(
            "Chủ Nhật bên mình không nhận lịch. Bạn chọn từ thứ Hai đến thứ Bảy nhé."
        )
    return d.isoformat()


def sinh_ma(ngay: str) -> str:
    """Mã lịch hẹn. Cùng khuôn với mã khung chat sinh ra, để hai nguồn đọc như một."""
    return f"TV-{ngay.replace('-', '')}-{secrets.token_hex(2).upper()}"


def dung_ban_ghi(
    *,
    session_id: str,
    full_name: str,
    phone: str,
    ngay: str,
    gio: str,
    job_order_code: str | None = None,
    support_code: str | None = None,
    hinh_thuc: str = "truc_tuyen",
) -> dict[str, Any]:
    """Bản ghi lịch hẹn, hình dạng y như khung chat tạo ra.

    `booking_key` giữ nguyên công thức `điện thoại|ngày|giờ` vì collection có
    **index duy nhất** trên nó: bấm hai lần, hay vừa hẹn qua chat vừa hẹn qua
    hành trình tư vấn, thì chỉ một lịch được tạo. Nhân viên không gọi hai lần cho
    cùng một người vào cùng một giờ.

    `source` và `support_code` là hai trường mới, chỉ để truy nguồn — nhìn một
    lịch là biết nó đến từ khung chat hay từ hành trình tư vấn, và nếu từ hành
    trình thì gắn với yêu cầu hỗ trợ nào.
    """
    return {
        "appointment_code": sinh_ma(ngay),
        "booking_key": f"{phone}|{ngay}|{gio}",
        "customer_name": full_name.strip(),
        "phone": phone,
        "appointment_date": ngay,
        "appointment_time": gio,
        "conversation_id": session_id,
        "job_order_code": job_order_code,
        "support_code": support_code,
        "meeting_kind": hinh_thuc,
        "source": "tu_van",
    }


def mo_ta(lich: dict[str, Any]) -> str:
    """Một dòng đọc được, dùng cho bản bàn giao và màn hình khách."""
    ngay = lich.get("appointment_date") or ""
    try:
        ngay_viet = datetime.strptime(ngay, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        ngay_viet = ngay
    hinh = {
        "truc_tiep": "gặp trực tiếp",
        "truc_tuyen": "gặp trực tuyến",
    }.get(lich.get("meeting_kind") or "", "")
    phan = [f"{lich.get('appointment_time')} ngày {ngay_viet}"]
    if hinh:
        phan.append(hinh)
    if lich.get("job_order_code"):
        phan.append(f"về đơn {lich['job_order_code']}")
    return " · ".join(phan)
