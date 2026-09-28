"""Dựng khối chữ bộ nhớ chung để đưa vào prompt của mỗi bên.

Thuần: không chạm database, không gọi mô hình. Nhận bản ghi đã đọc sẵn.

## Hai bên nhận hai khối khác nhau

Không phải để giấu nhau, mà vì hai bên làm hai việc khác nhau nên thứ hữu ích
cũng khác:

- **Khung chat** cần biết **đơn nào đang được xem** — trước đó nó phải dò tên
  tỉnh trong câu hỏi để đoán. Và cần biết chủ đề nào engine tư vấn đã giải thích,
  để đừng trả lời lại bằng kiến thức chung chung rồi mâu thuẫn với câu đã nói.
- **Engine tư vấn** cần biết **khách đã hỏi khung chat những gì**, nhất là chủ đề
  hỏi đi hỏi lại — đó là mối lo thật của họ, và nó thường không trùng với câu
  vừa gõ.

## Khối này luôn kèm một câu dặn

Mô hình đọc được "đã giải thích về chi phí" rất dễ suy thành "vậy thì chi phí là
X" rồi nói tiếp một con số nó tự nghĩ ra. Nên mỗi khối kết thúc bằng một câu nói
rõ: chỗ này chỉ ghi **đã bàn tới đâu**, không chứa nội dung đã nói, và muốn trả
lời thì phải lấy từ khối dữ liệu của chính mình.

Câu dặn ấy không thay được chốt hậu kiểm. `advisor/qa.kiem_tra` vẫn loại mọi con
số không có trong khối dữ liệu cho phép, và bộ nhớ này **cố ý không nằm trong
khối cho phép ấy** — nghĩa là một con số lọt vào đây cũng không thể đi ra ngoài.
"""
from typing import Any

from app.memory import topics


# Hỏi tới ngần này lần thì đó không còn là một câu hỏi, đó là một nỗi lo chưa
# được gỡ. Đánh dấu riêng để bên nhận đổi cách trả lời thay vì lặp lại.
NGUONG_LO_LANG = 2

_DAN_DO = (
    "(Phần trên chỉ ghi ĐÃ BÀN TỚI ĐÂU, không chứa nội dung đã trả lời. "
    "Đừng suy ra câu trả lời từ đây — muốn trả lời thì lấy từ các khối dữ liệu "
    "ở trên. Cũng đừng đọc lại danh sách này cho khách nghe.)"
)


def _sap_xep(moi_quan_tam: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Hỏi nhiều lần lên trước, rồi tới hỏi gần đây nhất.

    Sắp xếp tất định: thêm `chu_de` làm chốt cuối để hai lượt chạy không bao giờ
    ra hai thứ tự khác nhau khi số lần và thời điểm bằng nhau.
    """
    return sorted(
        moi_quan_tam,
        key=lambda m: (-m.get("so_lan", 0), _khoa_thoi_gian(m), m.get("chu_de", "")),
    )


def _khoa_thoi_gian(m: dict[str, Any]) -> str:
    luc = m.get("lan_cuoi")
    # Đảo dấu không làm được với chuỗi thời gian, nên dùng chuỗi rỗng cho bản ghi
    # thiếu mốc — chúng xuống cuối, đúng chỗ của dữ liệu không rõ.
    return "" if luc is None else str(luc)


def render(bo_nho: dict[str, Any] | None, *, cho: str) -> str:
    """Khối chữ cho bên `cho` (`"chat"` hoặc `"tu_van"`). Rỗng nghĩa là chưa có gì.

    Trả chuỗi rỗng chứ không trả một khối trống có tiêu đề: một tiêu đề không có
    nội dung dưới nó chỉ tốn chỗ trong prompt và mời mô hình tự điền vào.
    """
    if not bo_nho:
        return ""

    dong: list[str] = []
    ma_don = bo_nho.get("job_order_code")
    quan_tam = _sap_xep(list(bo_nho.get("moi_quan_tam") or []))
    da_giai_thich = list(bo_nho.get("da_giai_thich") or [])

    if cho == "chat":
        # Đơn đang xét là thứ giá trị nhất chảy sang phía này.
        if ma_don:
            dong.append(f"Khách đang xem đơn {ma_don} trên website.")
            dong.append(
                "Khách hỏi trống không 'đơn này…' là đang hỏi về đơn đó. Nếu bạn "
                "không có dữ liệu của chính đơn ấy thì mời khách hỏi ở phòng tư "
                "vấn theo đơn, ĐỪNG lấy số của một đơn khác ra trả lời."
            )
        boi = [g for g in da_giai_thich if g.get("ben") == "tu_van"]
        if boi:
            ten = ", ".join(topics.nhan_cua(g["chu_de"]) for g in boi)
            dong.append(f"Phòng tư vấn theo đơn đã giải thích với khách về: {ten}.")
    else:
        lo = [m for m in quan_tam if m.get("so_lan", 0) >= NGUONG_LO_LANG]
        if lo:
            dong.append("Khách hỏi đi hỏi lại về những việc sau — đây là mối lo chính:")
            for m in lo:
                dong.append(
                    f"- {topics.nhan_cua(m['chu_de'])}: {m['so_lan']} lần"
                    + (f", gần nhất: “{m['cau_gan_nhat']}”" if m.get("cau_gan_nhat") else "")
                )
            dong.append(
                "Đã hỏi lại nghĩa là lần trước trả lời chưa làm khách yên tâm. "
                "Nói cụ thể hơn, đừng lặp lại y nguyên."
            )
        khac = [m for m in quan_tam if m.get("so_lan", 0) < NGUONG_LO_LANG]
        if khac:
            ten = ", ".join(topics.nhan_cua(m["chu_de"]) for m in khac)
            dong.append(f"Khách cũng đã hỏi qua về: {ten}.")
        boi_chat = [g for g in da_giai_thich if g.get("ben") == "chat"]
        if boi_chat:
            ten = ", ".join(topics.nhan_cua(g["chu_de"]) for g in boi_chat)
            dong.append(f"Khung chat hỏi đáp chung đã trả lời khách về: {ten}.")

    if not dong:
        return ""
    return "\n".join(["[Khách đã trao đổi những gì trước đó]", *dong, _DAN_DO])
