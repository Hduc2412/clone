"""Cách gặp người thật — và vì sao nó phải nằm trong tầm biết của bot.

## Lỗ hổng bộ đo tìm ra

Ngày 29/09, ca `GIO-01` hỏi *"Em muốn gặp nhân viên thì liên hệ giờ nào?"*. Bot trả
lời "mình chưa có thông tin" — **đúng thiết kế nhưng sai thực tế**: công ty có giờ
liên hệ rõ ràng, chỉ là giờ đó khai trong `app/api/support.py` và không nằm trong
các khối dữ liệu đưa vào bot.

Bot chịu nói không biết là hành vi đúng và đáng giữ. Nhưng "không biết" ở đây không
phải vì dữ liệu không tồn tại, mà vì **không ai đưa nó tới nơi cần**. Hai chuyện
khác nhau hẳn, và chỉ có chuyện thứ hai là lỗi.

## Vì sao tách khỏi `eligibility.py`

Giờ liên hệ **không phải điều kiện xét tuyển**. Nhét nó vào khối điều kiện mức nền
là mời mô hình coi nó như một tiêu chí — rồi một lúc nào đó nó sẽ nói với ứng viên
rằng "bạn cần liên hệ trong giờ hành chính để đủ điều kiện". Nghe vô lý khi viết ra
đây, nhưng mô hình đọc một danh sách gạch đầu dòng mang tiêu đề "ĐIỀU KIỆN" thì nó
hiểu mọi dòng trong đó là điều kiện.

## Vì sao AI trực suốt còn người thì không

Đây là điểm bán thật của đề tài, và nó phải nói cho đúng cả hai nửa. Ứng viên tìm
hiểu lúc mười một giờ đêm — thời điểm phần lớn người đi làm mới rảnh — thì bot trả
lời ngay. Nhưng quyết định về tiền và về giấy tờ thì phải có người, và người thì
làm giờ hành chính.

Nói rõ cả hai nửa là tôn trọng người đọc. Hứa "hỗ trợ 24/7" rồi để họ nhắn lúc nửa
đêm và chờ tới sáng là một lời hứa tự phá.
"""

# Giờ nhân viên trả lời. Cố ý gọn hơn giờ làm việc chính thức có nghỉ trưa: bắt
# khách nhớ hai khoảng giờ rời nhau để gửi một câu hỏi là dựng một rào cản không
# cần thiết. Phần đặt lịch hẹn vẫn chặn đúng khoảng nghỉ, vì ở đó giờ phải chính xác.
GIO_LIEN_HE = "8h đến 17h"

NGAY_LAM_VIEC = "thứ Hai đến thứ Bảy"


def render() -> str:
    """Khối chữ về cách gặp người thật, đưa vào ngữ cảnh của bot tư vấn.

    Có tiêu đề riêng và nói thẳng "không phải điều kiện" — cùng một cách phòng như
    khối thông tin tham khảo của đơn hàng, vì mô hình đọc danh sách gạch đầu dòng
    thì rất dễ hiểu mọi dòng là ràng buộc.
    """
    return "\n".join(
        [
            "CÁCH GẶP NGƯỜI THẬT — không phải điều kiện, chỉ là thông tin liên hệ:",
            f"- Nhân viên tư vấn trả lời trong khoảng {GIO_LIEN_HE}, {NGAY_LAM_VIEC}",
            "- Ngoài giờ đó khách vẫn để lại yêu cầu được, nhân viên trả lời vào "
            "buổi làm việc kế tiếp",
            "- Khách có thể xin gặp trực tiếp hoặc gặp trực tuyến",
            "- Trợ lý này trả lời được suốt ngày đêm, nhưng việc chốt hồ sơ và chốt "
            "chi phí là của nhân viên",
        ]
    )
