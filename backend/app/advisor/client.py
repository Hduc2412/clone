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

    du_phong = settings.advisor_model_du_phong.strip()
    if du_phong and du_phong != settings.advisor_model:
        logger.info(
            "Engine tư vấn: có model dự phòng %s (thêm một hạn mức 20 lượt/ngày). "
            "Chỉ dùng khi model chính không trả lời được, không bao giờ dùng vì "
            "chốt hậu kiểm loại câu.",
            du_phong,
        )
    else:
        logger.info(
            "Engine tư vấn: KHÔNG có model dự phòng. Model chính hết hạn mức là "
            "mọi màn hình rơi về bản ghép sẵn. Khai ADVISOR_MODEL_DU_PHONG trong "
            "backend/.env để thêm một hạn mức nữa trên cùng khóa."
        )


def san_sang() -> bool:
    return settings.advisor_enabled and bool(api_key())


async def _goi_mot_lan(
    model: str,
    prompt: str,
    *,
    temperature: float,
    max_tokens: int,
    timeout: float | None = None,
) -> tuple[str | None, str]:
    """Đúng một lượt gọi tới đúng một model. Trả `(đoạn chữ, lý do)`.

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
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
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
        # Ngưỡng chờ cho phép nơi gọi nới riêng.
        #
        # Agent điều phối xin một khối JSON có `reply` cùng bốn trường nữa bên
        # trong, nên lượt sinh dài hơn hẳn một câu trả lời thuần — và với ngưỡng
        # chung 12 giây thì nó timeout thường xuyên. Đo thật ngày 02/10: hai lượt
        # liền trả `ReadTimeout`, mà lúc đó còn hạn mức.
        #
        # Không nâng ngưỡng chung: 12 giây là đúng cho phòng tư vấn theo đơn, và
        # nâng nó lên là bắt ứng viên ở đường ấy ngồi chờ lâu hơn mà chẳng được gì.
        async with httpx.AsyncClient(
            timeout=timeout or settings.advisor_timeout_seconds
        ) as client:
            response = await client.post(
                url, json=payload, headers={"x-goog-api-key": api_key()}
            )
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        # Ghi cả **tên loại ngoại lệ**, không chỉ lời của nó.
        #
        # `str()` của `httpx.ReadTimeout` và `ConnectTimeout` là chuỗi rỗng, nên
        # dòng log cũ in ra đúng `"không gọi được gemini-3.8-flash: "` và hết.
        # Timeout lại là lỗi truyền hay gặp nhất — tức là chỗ im lặng nhất của
        # log lại rơi đúng vào chỗ cần đọc nhất.
        #
        # Gặp thật ngày 02/10 khi đo Agent trên mô hình thật: hai lượt liền trả
        # về lý do rỗng, và không có cách nào biết đó là hết hạn mức, mất mạng,
        # hay quá thời gian chờ — ba việc cần ba cách xử lý khác nhau.
        logger.warning(
            "Engine tư vấn: không gọi được %s: %s",
            model,
            f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__,
        )
        return None, LY_DO_KHONG_GOI_DUOC

    if "error" in data:
        logger.warning("Engine tư vấn: %s báo lỗi: %s", model, data["error"])
        return None, LY_DO_KHONG_GOI_DUOC

    try:
        ung_vien = data["candidates"][0]
        # Nối TẤT CẢ các phần, không chỉ phần đầu.
        #
        # Mô hình được phép chia câu trả lời thành nhiều `part`, và bản trước chỉ
        # lấy `parts[0]` — nên mọi thứ sau phần đầu biến mất trong im lặng. Triệu
        # chứng rất khó lần: câu trả lời cụt giữa chừng nhưng `finishReason` vẫn là
        # `STOP`, nên chốt "chưa viết xong" không bắt, và chốt hậu kiểm cũng không
        # bắt vì phần còn lại là một câu hợp lệ, chỉ là cụt.
        #
        # Đo trên máy thật ngày 29/09: hỏi về viêm gan B, bot đáp đúng tám chữ
        # "Về điều kiện sức khỏe của chương trình" rồi hết. Bộ đọc CV
        # (`app/documents/extractor.py`) nối đúng từ đầu; chỗ này thì không — hai
        # client do cùng một người viết, một đúng một sai.
        phan = ung_vien["content"]["parts"]
        van_ban = "".join(p.get("text", "") for p in phan)
        if not van_ban.strip():
            raise KeyError("mọi phần đều rỗng")
    except (KeyError, IndexError, TypeError):
        logger.warning("Engine tư vấn: %s trả về dạng lạ.", model)
        return None, LY_DO_KHONG_GOI_DUOC

    # Câu bị cắt giữa chữ vẫn là chuỗi hợp lệ, nên phải bắt riêng. Không bắt ở
    # đây thì chốt hậu kiểm vẫn loại được nó, nhưng báo một lý do vô nghĩa
    # ("số lạ: ['0']" từ mã đơn bị đứt) và lần sau mất cả buổi đi tìm.
    ly_do_dung = ung_vien.get("finishReason")
    if ly_do_dung not in (None, "STOP"):
        logger.warning("Engine tư vấn: %s chưa viết xong câu trả lời (%s).", model, ly_do_dung)
        return None, LY_DO_BI_CAT

    return van_ban, LY_DO_OK


# Chỉ hai lý do này được phép chuyển sang model dự phòng. Cả hai đều có nghĩa là
# **chưa hề nhận được một câu trả lời trọn vẹn**.
LY_DO_DUOC_CHUYEN = (LY_DO_KHONG_GOI_DUOC, LY_DO_BI_CAT)


async def sinh_van_ban(
    prompt: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 1200,
    timeout: float | None = None,
) -> tuple[str | None, str, str]:
    """Gọi mô hình, trả `(đoạn chữ, lý do, model đã trả lời)`.

    Không bao giờ ném lỗi ra ngoài: một sự cố mạng không được làm gãy cả màn hình
    tư vấn. Mọi đường thất bại đều dẫn tới `None`, và nơi gọi dùng bản ghép sẵn.

    Nhưng phải nói rõ **vì sao** thất bại. Trước đây hàm này chỉ trả `None`, nên
    nơi gọi không phân biệt được "mô hình đã trả lời và bị chốt hậu kiểm loại"
    với "không gọi được mô hình". Hai thứ đó dồn chung vào một ô thống kê, và ô
    ấy lại chính là con số dùng để chứng minh bot không bịa — nghĩa là **hệ thống
    càng hỏng thì chỉ số trung thực trông càng đẹp**. Đo trên máy thật ngày
    28/09: hạn mức cạn giữa lượt nghiệm thu, mười câu không tới được mô hình, và
    bảng kết quả ghi nhận chúng như thể bot đã cân nhắc rồi chịu không đoán.

    ## Model dự phòng, và giới hạn rất hẹp của nó

    Hạn mức gói miễn phí là 20 lượt mỗi ngày cho mỗi (dự án, model). Một buổi bảo
    vệ mà hội đồng hỏi vài chục câu là cạn, và lúc ấy toàn bộ phần tư vấn lặng lẽ
    rơi về bản ghép sẵn. Nên có `ADVISOR_MODEL_DU_PHONG`: một model khác trên cùng
    khóa, tức thêm một hạn mức 20 lượt nữa mà không phải mượn của khung chat hay
    của bộ đọc CV.

    **Chỉ chuyển khi chưa nhận được câu trả lời trọn vẹn** — hết hạn mức, dịch vụ
    quá tải, mạng hỏng, hoặc câu bị cắt giữa chừng. Xem `LY_DO_DUOC_CHUYEN`.

    ## Vì sao KHÔNG BAO GIỜ chuyển khi chốt hậu kiểm loại câu trả lời

    Đây là chỗ dễ làm sai nhất, và làm sai thì hỏng đúng thứ hệ thống này tồn tại
    để bảo vệ.

    Nếu chốt hậu kiểm loại câu của model A rồi ta đi hỏi model B, ta không làm hệ
    thống đáng tin hơn — ta đang **lọc theo mẫu cho tới khi có câu lọt qua chốt**.
    Việc ấy chọn lọc đúng những lời bịa mà chốt chặn tình cờ không bắt được, và số
    liệu "tỉ lệ bot không đoán" sẽ đẹp lên trong khi chất lượng thật đi xuống.
    Một câu bị loại là một kết quả ĐÚNG, không phải một lần thử thất bại.

    Điều đó không cưỡng chế bằng lời dặn mà bằng **thứ tự các tầng**: dự phòng
    nằm ở đây, trong tầng truyền; chốt hậu kiểm nằm ở `qa.tra_loi`, trên tầng nội
    dung. Chốt chạy sau khi hàm này đã trả về, nên phán quyết của nó không có
    đường nào gọi lại được xuống đây. Sai lầm ấy thành không thể xảy ra, chứ không
    phải chỉ bị cấm.

    ## Model dự phòng phải được đo trước khi tin

    Nó trả lời ứng viên bằng chính giọng của hệ thống, nên không thể khai một model
    chưa đo rồi coi như xong. `scripts/nghiem_thu_tu_van.py --model=<tên>` đo được
    từng model riêng, và bảng kết quả ghi tên model vào từng dòng. Mỗi lần dự phòng
    được dùng thật, hàm này ghi một dòng log mức WARNING — để trong nhật ký máy chủ
    thấy rõ câu trả lời ấy không đến từ model chính.
    """
    if not san_sang():
        return None, LY_DO_TAT, ""

    chinh = settings.advisor_model
    van_ban, ly_do = await _goi_mot_lan(
        chinh, prompt, temperature=temperature, max_tokens=max_tokens, timeout=timeout
    )
    if van_ban is not None:
        return van_ban, ly_do, chinh

    du_phong = settings.advisor_model_du_phong.strip()
    if not du_phong or du_phong == chinh or ly_do not in LY_DO_DUOC_CHUYEN:
        return None, ly_do, chinh

    logger.warning(
        "Engine tư vấn: %s không trả lời được (%s) — chuyển sang model dự phòng %s.",
        chinh,
        ly_do,
        du_phong,
    )
    van_ban, ly_do_2 = await _goi_mot_lan(
        du_phong, prompt, temperature=temperature, max_tokens=max_tokens, timeout=timeout
    )
    if van_ban is None:
        # Cả hai đều không trả lời được. Báo lý do của lượt sau, vì đó là trạng
        # thái cuối cùng ta thật sự quan sát được.
        return None, ly_do_2, du_phong
    logger.warning(
        "Engine tư vấn: câu trả lời này do model DỰ PHÒNG %s viết, không phải %s.",
        du_phong,
        chinh,
    )
    return van_ban, ly_do_2, du_phong
