"""Engine tư vấn — hệ chính của đề tài, chạy độc lập với khung chat.

## Ranh giới, và vì sao nó phải là ranh giới thật

Khung chat hỏi đáp là **phần phụ trợ**: nó trả lời câu hỏi chung về chương trình
dựa trên tài liệu của công ty. Engine tư vấn là **hệ chính**: nó đối chiếu hồ sơ
một người với điều kiện một đơn rồi nói rõ đạt hay chưa đạt ở từng mục, còn thiếu
gì, học bao lâu thì đủ.

Hai việc khác nhau, và chúng phải hỏng độc lập với nhau. Trước khi tách, hai bên
dùng chung một khóa Gemini — nghĩa là dùng chung hạn mức. Khách hỏi chat nhiều
tới mức hết hạn mức thì phần tư vấn chết theo, dù hai nhánh code chẳng liên quan
gì nhau. Mà tư vấn mới là thứ không được chết: nó đang trả lời câu *"tôi có đi
được không"*.

## Ba điều gói này tự ràng buộc

1. **Không import gì từ phía chat.** Không `app.llm`, không `app.rag`, không
   `app.conversation`, không `chat_service`. Có ca kiểm thử quét mã nguồn để
   cưỡng chế — `tests/test_advisor_boundary.py`.

2. **Không quyết định nghiệp vụ.** Đạt hay không đạt, mấy điểm, học mấy tháng,
   hết bao nhiêu tiền — tất cả do quy tắc thuần tính (`app/matching/engine.py`,
   `app/learning/path.py`, `app/consultation/advice.py`). Gói này chỉ **viết lại
   cho dễ đọc**, và mọi câu nó viết đều bị hậu kiểm bằng mã nguồn.

3. **Tắt được mà hệ thống vẫn chạy đủ.** `ADVISOR_ENABLED=false` thì mọi màn hình
   dùng bản ghép sẵn. Điểm số không đổi một ly. Đây là câu trả lời khi bị hỏi
   *"hết hạn mức thì hệ thống còn gì"*.

## Địa chỉ API

Các đường của engine này nằm dưới `/tu-van/v1/*`, tách hẳn khỏi `/public/*` —
nhìn danh sách đường là biết ngay đâu là hệ chính, đâu là phụ trợ. Có số phiên
bản để sau này đổi hình dạng dữ liệu mà không làm gãy bản đang chạy.

Mã phiên thì vẫn dùng chung với phần hành trình công khai, và đó là chủ ý: khách
chat xong bấm sang tư vấn phải là **cùng một người**, không phải khai lại từ đầu.
Tách cả phiên là tách luôn khách ra làm hai.
"""
