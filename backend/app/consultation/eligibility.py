"""Điều kiện mức nền của chương trình, và cách nói chuyện sức khỏe.

## Hai tầng điều kiện

Mỗi đơn tuyển dụng có điều kiện riêng — đó là bảy tiêu chí bắt buộc mà bộ đối
chiếu chấm. Nhưng còn một tầng **trên cả đơn**: điều kiện của cả chương trình,
áp cho mọi đơn. Tầng này không nằm trong bản ghi đơn nào, nên phải khai ở đây.

Nguồn: trang điều kiện chính thức của công ty
`xklddieuduong.vn/?product=dieu-kien-di-nhat-o-don-hang-dieu-duong`, đọc từ kho
tri thức ngày 24/09/2026.

## Vì sao module này không chấm đạt/không đạt cho sức khỏe

Kết luận sức khỏe là của **buổi khám tại bệnh viện được chỉ định**, bước 2 trong
quy trình — sau khi khách đã đóng 10 triệu đặt cọc. Chấm "đạt sức khỏe" dựa trên
lời khai rồi để khách trượt ở phòng khám thì tệ hơn là không chấm gì: khách mất
tiền và mất niềm tin cùng lúc.

Thêm nữa, chính nguồn cũng không cho phép chấm: nó ghi *"các bệnh truyền nhiễm
**như**: Viêm gan B, HIV, bệnh lao"*. Chữ *như* nghĩa là danh sách chưa đầy đủ.
Chấm đạt theo một danh sách thiếu là hứa với khách một điều mà buổi khám có thể
lật lại.

## Hệ thống không lưu bất kỳ dữ liệu sức khỏe nào

Đây là quyết định có chủ ý, không phải thiếu tính năng.

Thứ duy nhất được lưu là **việc khách đã được thông báo điều kiện** — một dấu
thời gian. Không lưu khách có bệnh gì, cũng không lưu khách tự khai là có hay
không. Nếu khách thấy mình có thể không đủ điều kiện, hệ thống mở một yêu cầu
hỗ trợ để nhân viên gọi lại, và **yêu cầu đó cũng không ghi bệnh gì**.

Lý do: chẩn đoán bệnh theo người ta đi rất xa nếu lộ ra, và giá trị nghiệp vụ
của việc lưu nó bằng không — vì buổi khám mới là chỗ kết luận. Giữ ít dữ liệu
nhạy cảm thì ít chỗ để mất.

## Giá trị thật của module này

Khách tìm hiểu lúc mười một giờ đêm biết được điều kiện sức khỏe **trước khi
đóng đồng nào**. Trước đây họ chỉ biết sau khi đặt cọc và đi khám.
"""
from dataclasses import dataclass
from typing import Any


NGUON = "https://xklddieuduong.vn/?product=dieu-kien-di-nhat-o-don-hang-dieu-duong"


@dataclass(frozen=True)
class DieuKien:
    """Một dòng điều kiện mức nền, kèm chỗ nó lấy ra."""

    tieu_chi: str
    yeu_cau: str
    ghi_chu: str = ""


# Đúng năm dòng trên trang điều kiện của công ty, không thêm không bớt.
MUC_NEN: tuple[DieuKien, ...] = (
    DieuKien("Độ tuổi", "18 đến 40 tuổi, cả nam và nữ",
             "Từng đơn hàng có khoảng tuổi riêng hẹp hơn"),
    DieuKien("Sức khỏe", "Khỏe mạnh, không nhiễm bệnh truyền nhiễm",
             "Khám tại bệnh viện được chỉ định mới có kết luận"),
    DieuKien("Kinh nghiệm", "Không yêu cầu kinh nghiệm"),
    DieuKien("Bằng cấp", "Không yêu cầu bằng cấp",
             "Có bằng y, điều dưỡng hoặc dược là một lợi thế"),
    DieuKien("Ngoại hình", "Không yêu cầu chiều cao, cân nặng",
             "Mắt cận đeo kính vẫn đi được"),
)

# Ba bệnh nguồn nêu tên. Danh sách **chưa đầy đủ** — nguồn dùng chữ "như" — nên
# mọi chỗ hiển thị đều phải kèm câu nhắc ở `LOI_NHAC`.
BENH_LOAI_TRU: tuple[str, ...] = ("Viêm gan B", "HIV", "Bệnh lao")

LOI_NHAC = (
    "Đây là những bệnh công ty nêu tên. Danh sách có thể còn bệnh khác, và "
    "kết luận cuối cùng là của buổi khám tại bệnh viện được chỉ định."
)

# Câu hỏi đặt cho khách. Chỉ một câu, và nó không hỏi khách có bệnh gì.
CAU_HOI_XAC_NHAN = (
    "Bạn đã đọc điều kiện sức khỏe ở trên chưa? Nếu thấy mình có thể không đủ "
    "điều kiện, bạn cứ nói để nhân viên gọi lại trao đổi riêng."
)


def render_suc_khoe() -> str:
    """Khối chữ về điều kiện sức khỏe, đưa vào kết quả tư vấn.

    Luôn có câu nhắc `LOI_NHAC`. Nêu ba bệnh trơ trọi mà không nói danh sách
    chưa đầy đủ là để khách hiểu rằng không có ba bệnh ấy thì chắc chắn đạt.
    """
    dong = [
        "ĐIỀU KIỆN SỨC KHỎE — CÒN MỘT BƯỚC KHÁM:",
        f"- Không nhiễm bệnh truyền nhiễm: {', '.join(BENH_LOAI_TRU)}",
        f"- {LOI_NHAC}",
        # Thiếu dòng này, bot trả lời câu "khám có mất tiền không" bằng suy đoán:
        # đo trên máy thật ngày 28/09, nó nói "chi phí khám sẽ được thanh toán
        # tại bệnh viện được chỉ định" — ngụ ý khách phải trả, trong khi công ty
        # ghi rõ ngược lại. Bot không đọc trang web; thứ gì muốn nó biết thì phải
        # nằm trong bốn khối dữ liệu này.
        "- Công ty đưa đi khám tại bệnh viện được chỉ định, KHÔNG mất tiền",
        "- Có kết quả khám mới nộp hồ sơ vào đơn",
    ]
    return "\n".join(dong)


def render_muc_nen() -> str:
    """Khối chữ điều kiện mức nền, cho phần giới thiệu chung."""
    dong = ["ĐIỀU KIỆN MỨC NỀN CỦA CHƯƠNG TRÌNH:"]
    for dk in MUC_NEN:
        ghi = f" ({dk.ghi_chu})" if dk.ghi_chu else ""
        dong.append(f"- {dk.tieu_chi}: {dk.yeu_cau}{ghi}")
    return "\n".join(dong)


def as_dict() -> dict[str, Any]:
    """Hình dạng trả cho giao diện."""
    return {
        "muc_nen": [
            {"tieu_chi": dk.tieu_chi, "yeu_cau": dk.yeu_cau, "ghi_chu": dk.ghi_chu}
            for dk in MUC_NEN
        ],
        "benh_loai_tru": list(BENH_LOAI_TRU),
        "loi_nhac": LOI_NHAC,
        "cau_hoi_xac_nhan": CAU_HOI_XAC_NHAN,
        "source_url": NGUON,
    }
