"""Viết lại kết quả đã tính thành câu người đọc được — và hậu kiểm nó.

## Ranh giới: mô hình được suy luận, không được biết thêm

Đầu vào duy nhất là khối chữ tất định do `consultation/advice.render_block` dựng.
Mô hình được phép diễn giải, sắp lại, chọn giọng phù hợp — nhưng mọi **sự kiện**
trong câu trả lời phải đã có trong khối đó.

Ranh giới ấy không giữ được bằng lời dặn trong câu lệnh. Dặn "đừng bịa số" là một
lời dặn, không phải một bảo đảm: mô hình vẫn sẽ bịa khi nó thấy câu trả lời nghe
thiếu thuyết phục. Nên có **ba chốt chặn bằng mã nguồn** sau khi mô hình trả lời,
và cả ba đều đến từ lỗi đo được trên máy thật:

1. **Chốt số** — mọi chuỗi số trong câu phải có trong khối đầu vào.
2. **Chốt nghĩa** — không được biến một câu trả lời đã có thành một khoảng trống.
3. **Chốt cam kết** — không hứa kết quả, và không hứa hành động thay công ty.

Bị loại thì quay về bản ghép sẵn của `matching/explain.py`, và ghi log lý do —
đó là số liệu thật về mức độ tin được của mô hình, thứ trả lời được câu *"làm sao
biết nó không bịa"*.
"""
import logging
import re

from app.advisor import client


logger = logging.getLogger(__name__)

# Cụm từ hứa **kết quả**. Kết luận là việc của quy tắc và của nhân viên; một câu
# hứa ở đây sẽ được đọc như lời của công ty.
CUM_TU_CAM: tuple[str, ...] = (
    "chắc chắn đi được",
    "chắc chắn trúng tuyển",
    "đảm bảo trúng tuyển",
    "đảm bảo đi được",
    "cam kết trúng tuyển",
    "chắc chắn đậu",
    "hoàn toàn phù hợp",
    "đủ điều kiện tuyệt đối",
)

# Cụm từ hứa **hành động** thay công ty. Tách khỏi nhóm trên vì đây là một loại
# vượt rào khác. Đo trên máy thật, ca ứng viên đã có N4: mô hình tự thêm câu cuối
# "Chúng tôi sẽ nộp hồ sơ của bạn vào đơn hàng sau khi có kết quả khám sức khỏe."
# Không có số nào nên chốt số cho qua.
#
# Vấn đề thật: ứng viên còn chưa bấm đăng ký. Đọc câu ấy họ tưởng việc đã xong
# rồi ngồi đợi, trong khi hệ thống chưa tạo hồ sơ nào và không ai gọi họ.
CUM_TU_CAM_KET: tuple[str, ...] = (
    "chúng tôi sẽ nộp",
    "công ty sẽ nộp",
    "sẽ nộp hồ sơ của bạn",
    "chúng tôi sẽ gửi",
    "công ty sẽ gửi đơn",
    "sẽ được nhận vào",
    "chúng tôi sẽ sắp xếp",
)

# Bắt số **đứng một mình**, kể cả số có dấu phân cách nghìn và số thập phân.
#
# Phần nhìn lui `(?<![A-Za-zÀ-ỹ-])` mới là chỗ quan trọng, và nó đến từ một lỗ
# đo được: `N4` trong khối dữ liệu từng sinh ra chữ số `4`, thế là mọi câu bịa
# chứa số 4 đều lọt — "ký túc xá có 4 phòng điều hòa" qua được chốt trong khi
# khối chẳng nói gì về ký túc xá. Mã đơn `DH-0001` cũng vậy, nó tặng thêm `0001`.
#
# Số dính liền chữ hoặc dấu gạch là **một phần của mã**, không phải một con số
# nghiệp vụ. Bỏ chúng ở cả hai vế: câu trả lời viết "yêu cầu N4" cũng không sinh
# ra `4`, nên câu đúng vẫn qua, còn câu bịa mất chỗ bám.
#
# Trong lớp nhìn lui phải có cả `0-9`. Thiếu nó thì `DH-0001` bị chặn ở chữ số
# đầu rồi regex bắt lại từ chữ số thứ hai và vẫn nhả ra `001` — chặn nửa vời còn
# khó lần ra hơn không chặn.
_SO = re.compile(r"(?<![A-Za-zÀ-ỹ0-9-])\d+(?:[.,]\d+)*")

# Cách nói "chưa có thông tin". Dùng để bắt một lỗi nghĩa mà chốt số không thấy:
# mô hình đọc "ứng viên Chưa học" rồi viết "chưa có thông tin về trình độ tiếng
# Nhật". Hai chuyện khác hẳn nhau — "chưa học" là câu trả lời đã có, "chưa rõ" là
# chưa ai hỏi tới — và lẫn hai cái này là lẫn đúng chỗ cả hệ thống dựa vào.
#
# Với ứng viên, hai câu dẫn tới hai hành động khác nhau: một là đi học, một là
# quay lại khai thêm rồi ngồi đợi.
_THIEU_THONG_TIN = re.compile(
    r"chưa có thông tin|thiếu thông tin|chưa rõ|không rõ|chưa cung cấp|chưa khai",
    re.IGNORECASE,
)

PROMPT = """Bạn là trợ lý tư vấn của một công ty tuyển dụng lao động điều dưỡng đi Nhật Bản.

Dưới đây là KẾT QUẢ ĐỐI CHIẾU đã được hệ thống tính xong bằng quy tắc. Việc của bạn
là viết lại nó thành 3–5 câu tiếng Việt tự nhiên, dễ đọc, nói với ứng viên.

QUY TẮC BẮT BUỘC:
- Chỉ dùng thông tin có trong khối dưới. Không thêm bất kỳ con số nào không có ở đó.
- Không tự kết luận ứng viên đạt hay không đạt. Kết quả đã ghi sẵn, bạn chỉ nói lại.
- Không hứa hẹn. Không viết "chắc chắn đi được", "đảm bảo trúng tuyển" hay tương tự.
- KHÔNG nói thay công ty về việc sẽ làm gì tiếp theo. Không viết "chúng tôi sẽ nộp
  hồ sơ", "công ty sẽ gửi đơn" hay bất cứ cam kết nào về bước sau. Ứng viên còn
  chưa đăng ký; quyết định nộp hồ sơ là của họ và của nhân viên tư vấn.
- Mục nào ghi "chưa rõ" thì nói là chưa có thông tin, KHÔNG nói là không đạt.
- Phân biệt hai chuyện khác nhau: "Chưa học" là một câu trả lời đã có (ứng viên
  đã khai rằng họ chưa học), còn "chưa rõ" là chưa ai hỏi tới. Viết "chưa có
  thông tin về trình độ tiếng Nhật" khi khối ghi "ứng viên Chưa học" là nói sai:
  thông tin đã có, và nó nằm ở phần CHƯA ĐẠT chứ không phải CHƯA RÕ.
- Nếu có học phí, phải nói kèm cả tổng chi phí chương trình.
- Giọng bình tĩnh, tôn trọng. Không dùng dấu chấm than. Không bán hàng.
- Trả về đúng đoạn văn, không tiêu đề, không gạch đầu dòng, không markdown.

KẾT QUẢ ĐỐI CHIẾU:
{block}
"""


# Đơn vị tiền viết bằng chữ. Mô hình rất hay viết "35 triệu" thay vì
# "35.000.000đ", và đó là cách người Việt nói chứ không phải lỗi.
_DON_VI = (("tỷ", 1_000_000_000), ("triệu", 1_000_000), ("nghìn", 1_000), ("ngàn", 1_000))
_KEM_DON_VI = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(tỷ|triệu|nghìn|ngàn)\b", re.IGNORECASE
)


def _khai_trien(text: str) -> str:
    """Đổi "35 triệu" thành "35000000" trước khi bóc số.

    Không quy đổi thì `35 triệu` cho ra chữ số `35`, không khớp `35.000.000`
    trong dữ liệu, và câu trả lời **đúng** bị loại — bản ghép sẵn sẽ xuất hiện
    gần như mọi lần. Nới lỏng chốt chặn để bù cũng không được: nới ra thì
    `35 tháng` cũng lọt.

    Quy đổi ở cả hai vế nên không nới gì cả, chỉ là hai cách viết cùng một số
    tiền được nhận ra là một.
    """

    def doi(khop: re.Match[str]) -> str:
        so = khop.group(1).replace(".", "").replace(",", ".")
        don_vi = khop.group(2).lower()
        he_so = next(h for t, h in _DON_VI if t == don_vi)
        try:
            return str(int(float(so) * he_so))
        except ValueError:
            return khop.group(0)

    return _KEM_DON_VI.sub(doi, text)


def so_trong(text: str) -> set[str]:
    """Các chuỗi số trong một đoạn, đã bỏ dấu phân cách nghìn và quy đổi đơn vị.

    `35.000.000`, `35000000` và `35 triệu` phải được coi là cùng một số, nếu
    không chốt chặn sẽ loại oan câu trả lời chỉ vì mô hình viết số theo cách
    khác — và bản ghép sẵn sẽ xuất hiện gần như mọi lần.
    """
    return {
        khop.replace(".", "").replace(",", "")
        for khop in _SO.findall(_khai_trien(text))
    }


def kiem_tra(cau_tra_loi: str, block: str) -> str | None:
    """Trả về lý do loại, hoặc `None` nếu câu trả lời dùng được.

    Trả lý do thay vì chỉ `True`/`False` để ghi được vào log: khi bản ghép sẵn
    xuất hiện thay cho câu mô hình viết, phải biết vì sao.
    """
    sach = cau_tra_loi.strip()
    if not sach:
        return "câu trả lời rỗng"
    if len(sach) > 1200:
        return "câu trả lời quá dài"

    thap = sach.lower()
    for cum in CUM_TU_CAM:
        if cum in thap:
            return f"chứa cụm hứa hẹn: {cum!r}"
    for cum in CUM_TU_CAM_KET:
        if cum in thap:
            return f"cam kết thay công ty về bước tiếp theo: {cum!r}"

    la = so_trong(sach) - so_trong(block)
    if la:
        return f"có số không nằm trong kết quả đối chiếu: {sorted(la)}"

    # Khối không có mục nào chưa rõ, mà câu trả lời lại nói thiếu thông tin →
    # mô hình đang biến một câu trả lời đã có thành một khoảng trống.
    if "CHƯA RÕ" not in block and _THIEU_THONG_TIN.search(sach):
        return "nói là thiếu thông tin trong khi kết quả đối chiếu không có mục nào chưa rõ"
    return None


async def rephrase(block: str) -> str | None:
    """Viết lại khối kết quả thành đoạn văn. `None` nghĩa là dùng bản ghép sẵn."""
    if not block.strip():
        return None

    # Ở đây không cần phân biệt lý do thất bại: màn hình này luôn có bản ghép
    # sẵn đầy đủ, và không có số liệu nào đếm lượt viết lại. Chỗ cần phân biệt là
    # `qa.tra_loi` — xem `app/advisor/client.sinh_van_ban`.
    cau, _ = await client.sinh_van_ban(PROMPT.format(block=block))
    if cau is None:
        return None

    ly_do = kiem_tra(cau, block)
    if ly_do is not None:
        logger.warning("Loại câu trả lời của mô hình (%s). Dùng bản ghép sẵn.", ly_do)
        return None

    return cau.strip()
