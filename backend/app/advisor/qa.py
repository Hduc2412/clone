"""Bot tư vấn: trả lời câu hỏi của ứng viên về **hồ sơ của họ và đơn họ đang xem**.

## Khác gì khung chat hỏi đáp

Khung chat trả lời câu hỏi chung về chương trình, dựa trên kho tài liệu của công
ty. Nó không biết người đang hỏi là ai.

Bot này thì ngược lại: nó **không có kho tài liệu nào**, nhưng nó biết hồ sơ của
người đang hỏi, biết đơn họ đang xem, và biết kết quả đối chiếu giữa hai thứ đó.
Nên nó trả lời được những câu mà khung chat không trả lời nổi — *"tôi còn thiếu
gì"*, *"tôi học bao lâu thì đủ"*, *"vì sao tôi chưa đạt"*.

Hai bên không thay thế nhau, và cố ý không gộp: gộp thì phải cho bot này đọc kho
tài liệu, mà kho ấy đang còn rác nhận dạng ảnh ở hai mươi bốn trên ba mươi hai
đoạn — đủ để một câu trả lời về chi phí nói sai con số.

## Ranh giới: biết gì thì nói nấy, không biết thì nói không biết

Bot chỉ được đọc bốn khối chữ, tất cả đều do quy tắc dựng ra:

1. Hồ sơ ứng viên (`consultation/context_builder`)
2. Đơn đang xét (`consultation/order_context`)
3. Kết quả đối chiếu, gồm cả lộ trình học nếu có (`consultation/advice`)
4. Điều kiện mức nền của chương trình (`consultation/eligibility`)

Câu hỏi nằm ngoài bốn khối ấy — *"công ty thành lập năm nào"*, *"ký túc xá có
điều hòa không"* — thì bot **nói thẳng là chưa có thông tin** và chỉ sang khung
chat hoặc nhân viên. Đây là tính năng, không phải giới hạn: một câu trả lời bịa
về chi phí sẽ được đọc như lời của công ty.

## Vì sao không cho bot nhớ cả cuộc trò chuyện dài

Chỉ đưa vào vài lượt gần nhất. Lịch sử dài làm câu lệnh phình ra, và quan trọng
hơn: mỗi lượt đều phải kiểm lại được bằng bốn khối kia. Một câu trả lời sai ở
lượt thứ hai mà được mang theo tới lượt thứ mười thì nó thành "sự thật" trong mắt
mô hình, và chốt chặn không còn chỗ bám.
"""
import logging
import re
from typing import Any, Sequence

from app.advisor import client, phrasing


logger = logging.getLogger(__name__)

# Số lượt gần nhất mang theo. Đủ để hiểu "còn cái kia thì sao", không đủ để một
# câu sai sống sót thành sự thật.
SO_LUOT_NHO = 3

# Câu bot dùng khi câu hỏi nằm ngoài những gì nó được biết. Viết sẵn thay vì để
# mô hình tự nghĩ — chính lúc thiếu thông tin là lúc mô hình dễ bịa nhất.
CAU_KHONG_BIET = (
    "Câu này mình chưa có thông tin trong hồ sơ và đơn đang xem, nên mình không "
    "đoán. Bạn hỏi khung chat ở góc phải màn hình, hoặc để lại tin nhắn cho nhân "
    "viên tư vấn nhé."
)

# Câu dùng khi **không gọi được mô hình**: mất mạng, hết hạn mức, dịch vụ quá
# tải. Phải khác câu trên, vì hai tình huống này khác nhau đối với ứng viên. Nói
# "mình chưa có thông tin" trong lúc dịch vụ đang chết là nói sai: ứng viên sẽ
# tưởng công ty không có dữ liệu và thôi không hỏi nữa, trong khi thứ họ cần chỉ
# là hỏi lại sau mười phút.
CAU_KHONG_GOI_DUOC = (
    "Phần trợ lý tư vấn đang bận, mình chưa trả lời được câu này. Bạn thử lại sau "
    "ít phút giúp mình, hoặc để lại tin nhắn cho nhân viên tư vấn nhé."
)

# Ba giá trị của cột nguồn. Tách `khong_goi_duoc` ra khỏi `khong_biet` là bắt
# buộc: `db/advisor_turns.thong_ke()` đếm `khong_biet` để trả lời câu "làm sao
# biết bot không bịa". Dồn chung thì mỗi lần hết hạn mức là một lần chỉ số ấy
# đẹp lên, và nó đẹp lên đúng vào lúc hệ thống hỏng nhất.
NGUON_MO_HINH = "mo_hinh"
NGUON_KHONG_BIET = "khong_biet"
NGUON_KHONG_GOI_DUOC = "khong_goi_duoc"

# Dấu hiệu mô hình tự nhận là không biết. Nhận ra thì thay bằng câu chuẩn ở trên,
# để lời từ chối luôn kèm đúng đường đi tiếp thay vì cụt lủn.
_TU_CHOI = re.compile(
    r"không có thông tin|chưa có thông tin|không tìm thấy|ngoài phạm vi|"
    r"mình không biết|tôi không biết|không nằm trong",
    re.IGNORECASE,
)

PROMPT = """Bạn là trợ lý tư vấn của một công ty tuyển dụng lao động điều dưỡng đi Nhật Bản.
Bạn đang nói chuyện với một ứng viên về đúng một đơn tuyển dụng mà họ đang xem.

Trả lời câu hỏi của họ bằng 2–4 câu tiếng Việt, tự nhiên, dễ hiểu.

QUY TẮC BẮT BUỘC:
- CHỈ dùng thông tin trong bốn khối dưới. Không thêm bất kỳ con số nào không có ở đó.
- Câu hỏi nằm ngoài bốn khối đó thì trả lời đúng một câu: "Câu này mình chưa có
  thông tin." Không đoán, không suy ra, không nói chung chung cho có.
- Không tự kết luận ứng viên đạt hay không đạt. Kết quả đối chiếu đã có sẵn.
- Không hứa hẹn, không cam kết thay công ty về bước tiếp theo.
- "Chưa học" là một câu trả lời đã có, khác hẳn "chưa rõ" là chưa ai hỏi tới.
- Khách hỏi về điều kiện CHUNG (tuổi, bằng cấp, sức khỏe, kinh nghiệm) thì nêu CẢ
  mức nền của chương trình LẪN mức riêng hẹp hơn của đơn đang xét, và nói rõ đâu
  là của chương trình, đâu là của đơn này. Chỉ nêu mức của đơn là để người ngoài
  khoảng đó tưởng cả chương trình đóng với họ, trong khi còn đơn khác.
- Nếu nói tới học phí thì phải nói kèm tổng chi phí chương trình.
- Giọng bình tĩnh, tôn trọng. Không dấu chấm than. Không bán hàng.
- Trả về đúng đoạn văn, không tiêu đề, không gạch đầu dòng, không markdown.

{ho_so}

{don}

[Kết quả đối chiếu hồ sơ này với đơn này]
{doi_chieu}

{dieu_kien_nen}
{bo_nho}{lich_su}
CÂU HỎI CỦA ỨNG VIÊN:
{cau_hoi}
"""


def _lich_su(luot: Sequence[dict[str, str]]) -> str:
    gan_nhat = list(luot)[-SO_LUOT_NHO:]
    if not gan_nhat:
        return ""
    dong = ["[Vài lượt gần nhất trong cuộc trò chuyện này]"]
    for l in gan_nhat:
        dong.append(f"Ứng viên: {l.get('question', '')}")
        dong.append(f"Trợ lý: {l.get('answer', '')}")
    return "\n".join(dong) + "\n"


def kiem_tra(cau_tra_loi: str, khoi_cho_phep: str) -> str | None:
    """Hậu kiểm. Trả lý do loại, hoặc `None` nếu dùng được.

    Dùng lại đúng bộ chốt chặn của phần diễn đạt — chốt số, chốt cụm hứa hẹn,
    chốt cam kết thay công ty. Viết bộ thứ hai là mở đường cho hai bộ lệch nhau,
    và lệch ở đây nghĩa là một trong hai chỗ đang để lọt.

    Khác một điểm: bỏ chốt "nói thiếu thông tin khi khối không có mục chưa rõ".
    Ở đây bot **được phép** nói chưa có thông tin — đó chính là hành vi mong muốn
    khi câu hỏi nằm ngoài những gì nó biết.
    """
    sach = cau_tra_loi.strip()
    if not sach:
        return "câu trả lời rỗng"
    if len(sach) > 1500:
        return "câu trả lời quá dài"

    thap = sach.lower()
    for cum in phrasing.CUM_TU_CAM:
        if cum in thap:
            return f"chứa cụm hứa hẹn: {cum!r}"
    for cum in phrasing.CUM_TU_CAM_KET:
        if cum in thap:
            return f"cam kết thay công ty về bước tiếp theo: {cum!r}"

    la = phrasing.so_trong(sach) - phrasing.so_trong(khoi_cho_phep)
    if la:
        return f"có số không nằm trong dữ liệu được đọc: {sorted(la)}"

    if _gop_hai_so_tien(sach, khoi_cho_phep):
        return "nói một khoản tiền nằm trong khoản tiền khác, trong khi dữ liệu không nói thế"
    return None


# Cụm chỉ quan hệ bao hàm giữa hai khoản tiền.
_BAO_HAM = re.compile(r"trong đó|bao gồm|đã gồm|đã bao gồm|nằm trong|kể cả", re.IGNORECASE)

# Khoản tiền viết theo lối người Việt: từ sáu chữ số trở lên, hoặc kèm "triệu".
_SO_TIEN = re.compile(r"\d{1,3}(?:[.,]\d{3}){2,}|\d+(?:[.,]\d+)?\s*triệu", re.IGNORECASE)


def _gop_hai_so_tien(cau: str, khoi_cho_phep: str) -> bool:
    """Câu có hai khoản tiền khác nhau **và** một cụm chỉ quan hệ bao hàm.

    Chốt số không bắt được lỗi này vì cả hai con số đều có thật trong dữ liệu —
    nó kiểm số có tồn tại, không kiểm quan hệ giữa các số.

    Đo trên máy thật: ứng viên hỏi tổng tiền phải chuẩn bị, bot trả lời *"tổng
    chi phí chương trình là 110.000.000đ, **trong đó** học phí tiếng Nhật là
    35.000.000đ"*. 110 triệu là chi phí ước tính của riêng một đơn, 35 triệu
    thuộc gói 90 triệu của bảng khóa học — hai nguồn khác nhau, và không ai biết
    con số này có bao gồm con số kia.

    Với người đang tính chuyện vay tiền đi nước ngoài, chữ "trong đó" ấy là khác
    biệt giữa chuẩn bị 110 triệu và chuẩn bị 145 triệu.

    ## Cho qua khi chính dữ liệu nói ra quan hệ ấy

    Bản chốt đầu tiên chặn mọi câu có hai khoản tiền kèm cụm bao hàm — và nó
    chặn luôn câu **đúng**: *"học phí 35 triệu, là một chặng trong tổng 90
    triệu"*, thứ dữ liệu nói thẳng ra. Bot im lặng quay về "chưa có thông tin"
    ngay cả khi nó có đủ thông tin.

    Nên điều kiện thật là: có **một dòng trong dữ liệu** chứa cả những khoản
    tiền ấy hay không. Có thì quan hệ do nguồn nói, cho qua. Không có thì hai
    con số đến từ hai chỗ khác nhau và bot đang tự nối chúng lại.

    Đó cũng là lý do `advice.render_block` viết học phí và tổng gói trên **cùng
    một dòng** thay vì hai dòng liền nhau.
    """
    if not _BAO_HAM.search(cau):
        return False
    khoan = {_chuan(k) for k in _SO_TIEN.findall(cau)}
    if len(khoan) < 2:
        return False
    # Dữ liệu có nói ra quan hệ này không: tìm một dòng chứa đủ các khoản ấy.
    for dong in khoi_cho_phep.splitlines():
        if khoan <= {_chuan(k) for k in _SO_TIEN.findall(dong)}:
            return False
    return True


def _chuan(khoan: str) -> str:
    """Đưa một khoản tiền về dạng so sánh được.

    `35.000.000` và `35 triệu` là cùng một số tiền viết hai cách. Không quy về
    một dạng thì chốt chặn so hai chuỗi khác nhau rồi kết luận sai.
    """
    sach = khoan.strip().lower()
    if "triệu" in sach:
        so = sach.replace("triệu", "").replace(".", "").replace(",", ".").strip()
        try:
            return str(int(float(so) * 1_000_000))
        except ValueError:
            return sach
    return sach.replace(".", "").replace(",", "")


async def tra_loi(
    *,
    cau_hoi: str,
    ho_so: str,
    don: str,
    doi_chieu: str,
    dieu_kien_nen: str,
    bo_nho: str = "",
    lich_su: Sequence[dict[str, str]] = (),
) -> tuple[str, str]:
    """Trả `(câu trả lời, nguồn)`. Nguồn là một trong ba giá trị `NGUON_*`.

    Không bao giờ ném lỗi: mọi đường thất bại đều dẫn tới câu "chưa có thông tin"
    kèm đường đi tiếp. Im lặng hoặc báo lỗi kỹ thuật ở đây là để ứng viên đứng
    giữa chừng một cuộc trò chuyện mà không biết làm gì.
    """
    # `bo_nho` CỐ Ý không nằm trong khối cho phép. Nó chở chủ đề đã bàn và câu
    # hỏi nguyên văn của khách, không chở dữ liệu để trả lời — nên một con số
    # lọt vào đó cũng không được phép đi ra ngoài. Xem `app/memory/__init__.py`.
    khoi_cho_phep = "\n".join((ho_so, don, doi_chieu, dieu_kien_nen))

    prompt = PROMPT.format(
        ho_so=ho_so or "[Chưa biết gì về ứng viên này]",
        don=don or "[Chưa chọn đơn nào]",
        doi_chieu=doi_chieu or "(chưa đối chiếu)",
        dieu_kien_nen=dieu_kien_nen,
        bo_nho=f"{bo_nho}\n" if bo_nho.strip() else "",
        lich_su=_lich_su(lich_su),
        cau_hoi=cau_hoi.strip(),
    )

    cau, ly_do_goi = await client.sinh_van_ban(prompt, temperature=0.3, max_tokens=900)
    if cau is None:
        # Không gọi được mô hình. Đây KHÔNG phải là bot chịu không đoán — nó chưa
        # hề được hỏi. Ghi đúng như vậy, xem `NGUON_KHONG_GOI_DUOC`.
        logger.warning("Bot tư vấn: không có câu trả lời (%s).", ly_do_goi)
        return CAU_KHONG_GOI_DUOC, NGUON_KHONG_GOI_DUOC

    ly_do = kiem_tra(cau, khoi_cho_phep)
    if ly_do is not None:
        logger.warning("Bot tư vấn: loại câu trả lời (%s).", ly_do)
        return CAU_KHONG_BIET, NGUON_KHONG_BIET

    sach = cau.strip()
    # Mô hình tự nhận không biết thì thay bằng câu chuẩn: lời từ chối phải kèm
    # đúng đường đi tiếp, không để ứng viên cụt ở đó.
    if _TU_CHOI.search(sach) and len(sach) < 200:
        return CAU_KHONG_BIET, NGUON_KHONG_BIET

    return sach, NGUON_MO_HINH
