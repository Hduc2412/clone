"""Tiếp nhận và bóc tách hồ sơ ứng viên tải lên.

Ba module, ba trách nhiệm tách bạch — cố ý, để phần nào cũng kiểm thử được một
mình:

- `reader`   : bytes → chữ. Thuần, không mạng, không database.
- `extractor`: chữ → trường dữ liệu có nguồn. Phần gọi mô hình và phần ánh xạ kết
  quả nằm ở hai hàm khác nhau, nên ánh xạ kiểm thử được mà không cần khóa API.
- `storage`  : ghi bản gốc xuống đĩa, không bao giờ ghi đè.
"""
