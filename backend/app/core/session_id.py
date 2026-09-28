"""Hình dạng hợp lệ của mã phiên ẩn danh, khai báo đúng một nơi.

Luồng tư vấn công khai không có đăng nhập: trình duyệt tự sinh một mã phiên,
lưu vào `localStorage`, và mọi đường `/public/*` nhận diện người dùng bằng đúng
mã đó. Nghĩa là **mã phiên chính là mật khẩu** của hồ sơ ấy — biết mã là đọc
được hồ sơ, gửi được CV, xem được danh sách đơn đã giới thiệu.

Vì vậy độ dài tối thiểu ở đây không phải chuyện hình thức. Ràng buộc cũ cho
phép từ 8 ký tự, tức máy chủ vui vẻ nhận `12345678` làm mã phiên và tạo hồ sơ
dưới mã đó. Giao diện không bao giờ gửi chuỗi như vậy — nó luôn dùng
`crypto.randomUUID()` — nhưng giao diện không phải là hàng rào: ai cũng gọi
thẳng vào đường công khai được, và một kho hồ sơ đánh số bằng chuỗi tám ký tự
thì dò hết chỉ là chuyện thời gian.

Ngưỡng 32 ký tự là độ dài của UUID viết liền; bản có dấu gạch ngang dài 36. Cả
hai đều lọt, còn mọi chuỗi ngắn tự đặt thì không.
"""

# Chỉ chữ, số và dấu gạch ngang — đủ cho cả hai cách viết UUID. Bỏ dấu gạch
# dưới so với bản cũ vì không dạng nào của UUID dùng tới nó.
SESSION_PATTERN = r"^[A-Za-z0-9-]{32,64}$"
