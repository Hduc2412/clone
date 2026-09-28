"""Lớp tư vấn: những gì biến hỏi–đáp thành một cuộc tư vấn.

Các module ở đây **không gọi mô hình ngôn ngữ**. Chúng đọc dữ liệu có thật (hồ sơ
ứng viên, danh mục đơn, kết quả đối chiếu) rồi dựng thành khối chữ để đưa vào ngữ
cảnh. Mô hình chỉ diễn đạt lại khối chữ ấy.

Đây là cùng một cách làm với `app/rag/job_lookup.py`, và là lý do prompt không
phải phình ra: thứ giúp bot tư vấn được không phải là thêm luật, mà là cho nó
biết nó đang nói với ai.
"""
