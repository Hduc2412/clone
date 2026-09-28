"""Tư vấn lộ trình học tiếng Nhật.

Cùng nguyên tắc với `app/consultation/` và `app/matching/`: các module ở đây
**không gọi mô hình ngôn ngữ**. Chúng đọc danh mục khóa học có thật rồi cộng trừ
bằng quy tắc. Nhờ vậy con số đưa cho ứng viên luôn truy được về một dòng trong
bảng, và chạy lại bao nhiêu lần cũng ra một kết quả.

Thiếu dữ liệu thì trả rỗng, để nơi gọi nói định tính — tuyệt đối không nội suy
số tháng hay học phí.
"""
