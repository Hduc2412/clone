"""Kiểm thử: nội dung khách nói không được đi ra log.

## Vì sao cần một lớp test riêng cho chuyện này

Log máy chủ là nơi **không có kiểm soát truy cập**. Nó thường được gom về một chỗ
tập trung, giữ lâu hơn mọi chính sách lưu trữ mà dự án tuyên bố, và ai vận hành
cũng đọc được. Câu của khách thì có thể chứa họ tên, số điện thoại, hay tình
trạng sức khoẻ — trong lĩnh vực này, đó đúng là những thứ người ta ngại nhất.

Đo được ngày 21/09/2026 khi chạy thử bộ nghiệm thu: `[ReferenceResolver]` in ra
nguyên câu hỏi kèm bốn dòng lịch sử vừa bồi vào, `[IntentClassifier]` in câu gốc,
`[EntityExtractor]` in cả tên lẫn số điện thoại vừa bóc được. Không ai cố ý làm
vậy — đó là `print` của lúc gỡ lỗi, để quên lại.

Kiểu hỏng này **không tự lộ ra**: hệ thống vẫn chạy đúng, test vẫn xanh, chỉ có
dữ liệu âm thầm chảy sang chỗ không nên. Nên phải có một lớp test canh nó, chứ
không thể trông vào việc nhớ.

Test kiểm hành vi ở mức quan sát được — chạy hàm rồi soi những gì chảy ra
stdout/stderr — nên nó bắt được cả `print` lẫn logger cấu hình sai, và không phụ
thuộc vào việc mã được viết thế nào bên trong.
"""
import io
import logging
import unittest
from contextlib import redirect_stderr, redirect_stdout

from app.conversation.entity_extractor import extract_lead_info
from app.conversation.intent_classifier import classify
from app.conversation.reference_resolver import resolve
from app.conversation.response_validator import validate

# Những mẩu tin phải không bao giờ thấy trong log.
HO_TEN = "Hoàng Thị Mai Anh"
SO_DIEN_THOAI = "0912345678"
BENH = "viêm gan B"


def chay_va_bat_log(ham, *args, **kwargs) -> str:
    """Chạy `ham` rồi trả về mọi thứ nó viết ra stdout, stderr và logging.

    Bắt cả ba đường vì đây là ba cách một dòng chữ có thể rời khỏi tiến trình:
    `print` đi stdout, logging mặc định đi stderr, còn handler do chỗ khác gắn
    vào thì phải bắt ở tầng logging.
    """
    out, err = io.StringIO(), io.StringIO()
    thu = io.StringIO()
    handler = logging.StreamHandler(thu)
    goc = logging.getLogger()
    muc_cu = goc.level
    goc.addHandler(handler)
    goc.setLevel(logging.DEBUG)
    try:
        with redirect_stdout(out), redirect_stderr(err):
            ham(*args, **kwargs)
    finally:
        goc.removeHandler(handler)
        goc.setLevel(muc_cu)
    return out.getvalue() + err.getvalue() + thu.getvalue()


class KhongGhiNoiDungKhachNoiTests(unittest.TestCase):
    def test_bồi_ngữ_cảnh_không_in_lịch_sử_hội_thoại(self):
        lich_su = (
            f"Khach: Em tên {HO_TEN}, em bị {BENH} thì có đi được không?\n"
            f"Bot: Điều kiện sức khoẻ do cơ sở y tế quyết định.\n"
        )
        log = chay_va_bat_log(resolve, "Thế cái đó có sao không?", lich_su)

        self.assertNotIn(HO_TEN, log)
        self.assertNotIn(BENH, log)

    def test_phân_loại_ý_định_không_in_câu_hỏi(self):
        cau = f"Em tên {HO_TEN}, chi phí đi Nhật hết bao nhiêu?"
        log = chay_va_bat_log(classify, cau)

        self.assertNotIn(HO_TEN, log)

    def test_bóc_thực_thể_không_in_tên_và_số_điện_thoại(self):
        # Đây là hàm chạm vào đúng hai thứ nhạy cảm nhất trong cả luồng chat.
        cau = f"Tôi tên {HO_TEN}, số điện thoại của tôi là {SO_DIEN_THOAI}"
        log = chay_va_bat_log(extract_lead_info, cau)

        self.assertNotIn(HO_TEN, log)
        self.assertNotIn(SO_DIEN_THOAI, log)

    def test_chặn_số_lạ_không_in_chính_con_số_đó(self):
        # Số bị chặn hoặc là số mô hình bịa, hoặc là số thật của một khách khác
        # lọt vào kho tri thức. Cả hai đều không nên được nhân bản sang log.
        so_la = "0987654321"
        log = chay_va_bat_log(
            validate,
            f"Bạn liên hệ {so_la} để được tư vấn thêm nhé, nhân viên sẽ gọi lại.",
            "chung",
        )

        self.assertNotIn(so_la, log)

    def test_vẫn_ghi_đủ_thứ_cần_để_chẩn_đoán(self):
        """Không phải cứ im lặng là đúng — log phải còn dùng được.

        Nếu bỏ hết thì lần sau có sự cố sẽ không lần ra được gì. Ranh giới ở
        đây: ghi *chuyện gì đã xảy ra*, không ghi *khách đã nói gì*.
        """
        log = chay_va_bat_log(classify, "Chi phí đi Nhật hết bao nhiêu tiền?")

        self.assertIn("chi_phi", log)


if __name__ == "__main__":
    unittest.main()
