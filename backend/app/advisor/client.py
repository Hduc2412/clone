"""Client gọi mô hình của riêng engine tư vấn.

Viết riêng thay vì dùng `app/llm/gemini.py`: file đó phục vụ khung chat, dùng
`requests` đồng bộ với `time.sleep` để thử lại. Gọi nó từ một endpoint bất đồng
bộ sẽ **đóng băng cả event loop** trong lúc chờ — một người hỏi chat chậm là mọi
người khác cũng đứng.

Ở đây dùng `httpx` bất đồng bộ, một lần gọi, không thử lại. Không thử lại là có
chủ ý: phần này là trang trí, hỏng thì đã có bản ghép sẵn dùng được ngay, không
có lý do gì bắt ứng viên chờ thêm mấy nhịp.
"""
import logging
from typing import Any

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)

# Vì sao một lượt gọi không cho ra chữ. Phân biệt được ba thứ này là bắt buộc,
# không phải chi tiết kỹ thuật: "mô hình từ chối trả lời" và "không gọi được mô
# hình" nhìn từ phía ứng viên thì giống hệt nhau — cùng một câu ghép sẵn — nhưng
# với người đọc số liệu thì đó là hai kết luận trái ngược.
LY_DO_OK = "ok"
LY_DO_TAT = "tat"                       # engine tắt, hoặc chưa khai khóa
LY_DO_KHONG_GOI_DUOC = "khong_goi_duoc"  # mạng hỏng, hết hạn mức, mô hình báo lỗi
LY_DO_BI_CAT = "bi_cat"                  # có trả lời nhưng chưa viết xong

_da_canh_bao_dung_chung = False


def api_key() -> str:
    """Khóa của engine tư vấn, quay về khóa chung nếu chưa khai riêng.

    Cảnh báo đúng một lần. Dùng chung khóa là dùng chung hạn mức, và hậu quả chỉ
    lộ ra vào đúng lúc tệ nhất — giữa buổi demo, khi chat vừa ngốn hết quota.
    """
    global _da_canh_bao_dung_chung
    if settings.advisor_api_key:
        return settings.advisor_api_key
    if not _da_canh_bao_dung_chung:
        logger.warning(
            "ADVISOR_API_KEY chưa khai — engine tư vấn đang dùng chung khóa và "
            "hạn mức với khung chat. Chat hết hạn mức thì tư vấn chết theo."
        )
        _da_canh_bao_dung_chung = True
    return settings.gemini_api_key


def dung_chung_khoa() -> bool:
    """Engine tư vấn đang dùng chung khóa với khung chat hay không."""
    return not settings.advisor_api_key


def bao_cau_hinh() -> None:
    """Ghi tình trạng khóa lúc khởi động.

    Trước đây chỉ cảnh báo ở lần gọi mô hình đầu tiên — nghĩa là có thể chạy cả
    buổi mà không ai thấy dòng ấy, rồi đúng lúc demo thì chat ngốn hết hạn mức và
    phần tư vấn lặng lẽ rơi về câu ghép sẵn. Ghi ngay lúc khởi động để tình trạng
    này nằm ở dòng log đầu tiên, không phải nằm chờ một sự cố mới lộ ra.
    """
    if not settings.advisor_enabled:
        logger.info("Engine tư vấn: TẮT. Mọi màn hình dùng câu ghép sẵn.")
        return
    if dung_chung_khoa():
        logger.warning(
            "Engine tư vấn: dùng CHUNG khóa và hạn mức với khung chat. "
            "Chat hết hạn mức thì tư vấn chết theo. Khai ADVISOR_API_KEY trong "
            "backend/.env để tách — và khóa đó phải thuộc một dự án Google khác, "
            "vì hạn mức tính theo dự án chứ không theo khóa."
        )
    else:
        logger.info("Engine tư vấn: dùng khóa riêng, model %s.", settings.advisor_model)


def san_sang() -> bool:
    return settings.advisor_enabled and bool(api_key())


async def sinh_van_ban(
    prompt: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 1200,
) -> tuple[str | None, str]:
    """Gọi mô hình, trả `(đoạn chữ, lý do)`. Chữ là `None` nghĩa là không dùng được.

    Không bao giờ ném lỗi ra ngoài: một sự cố mạng không được làm gãy cả màn hình
    tư vấn. Mọi đường thất bại đều dẫn tới `None`, và nơi gọi dùng bản ghép sẵn.

    Nhưng phải nói rõ **vì sao** thất bại. Trước đây hàm này chỉ trả `None`, nên
    nơi gọi không phân biệt được "mô hình đã trả lời và bị chốt hậu kiểm loại"
    với "không gọi được mô hình". Hai thứ đó dồn chung vào một ô thống kê, và ô
    ấy lại chính là con số dùng để chứng minh bot không bịa — nghĩa là **hệ thống
    càng hỏng thì chỉ số trung thực trông càng đẹp**. Đo trên máy thật ngày
    28/09: hạn mức cạn giữa lượt nghiệm thu, mười câu không tới được mô hình, và
    bảng kết quả ghi nhận chúng như thể bot đã cân nhắc rồi chịu không đoán.
    """
    if not san_sang():
        return None, LY_DO_TAT

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.advisor_model}:generateContent"
    )
    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            # Tắt suy luận nội bộ. Bắt buộc, không phải tối ưu: token suy luận
            # **tính vào `maxOutputTokens`**, nên với hạn mức nhỏ thì mô hình
            # tiêu gần hết vào suy luận rồi câu trả lời bị cắt giữa chữ. Đo trên
            # máy thật với 600 token: trả về đúng tám mươi ký tự, đứt ở giữa mã
            # đơn. Mà đây là việc viết lại một khối chữ đã có sẵn — không có gì
            # để suy luận.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    try:
        async with httpx.AsyncClient(timeout=settings.advisor_timeout_seconds) as client:
            response = await client.post(
                url, json=payload, headers={"x-goog-api-key": api_key()}
            )
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Engine tư vấn không gọi được mô hình: %s", exc)
        return None, LY_DO_KHONG_GOI_DUOC

    if "error" in data:
        logger.warning("Engine tư vấn: mô hình báo lỗi: %s", data["error"])
        return None, LY_DO_KHONG_GOI_DUOC

    try:
        ung_vien = data["candidates"][0]
        van_ban = ung_vien["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        logger.warning("Engine tư vấn: mô hình trả về dạng lạ.")
        return None, LY_DO_KHONG_GOI_DUOC

    # Câu bị cắt giữa chữ vẫn là chuỗi hợp lệ, nên phải bắt riêng. Không bắt ở
    # đây thì chốt hậu kiểm vẫn loại được nó, nhưng báo một lý do vô nghĩa
    # ("số lạ: ['0']" từ mã đơn bị đứt) và lần sau mất cả buổi đi tìm.
    ly_do_dung = ung_vien.get("finishReason")
    if ly_do_dung not in (None, "STOP"):
        logger.warning("Engine tư vấn: câu trả lời chưa viết xong (%s).", ly_do_dung)
        return None, LY_DO_BI_CAT

    return van_ban, LY_DO_OK
