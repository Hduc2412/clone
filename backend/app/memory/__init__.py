"""Bộ nhớ dùng chung giữa hai hệ trả lời — **mang câu hỏi, không mang câu trả lời**.

Hệ thống có hai chỗ biết nói chuyện, và chúng cố ý tách nhau:

- **Engine tư vấn** (`app/advisor`) — hệ chính. Trả lời theo đúng một đơn, đọc hồ
  sơ và kết quả đối chiếu.
- **Khung chat hỏi đáp** (`app/llm`, `app/rag`) — phụ trợ. Trả lời câu chung từ
  kho tri thức, không biết đơn nào đang được xem.

Hai bên đã dùng chung mã phiên và chung bảng `candidate_profiles`, nên **sự thật
về ứng viên** thì đã chảy qua lại được. Thứ chưa chảy là **diễn tiến cuộc trò
chuyện**: con tư vấn không biết khách vừa hỏi khung chat ba lần về chi phí, khung
chat không biết khách đang xem đơn nào, và không bên nào biết bên kia đã giải
thích gì — nên cả hai cùng lặp lại từ đầu.

Gói này lấp đúng chỗ đó.

## Luật cứng: câu trả lời không bao giờ đi qua đây

Chỉ hai loại thứ được phép chảy giữa hai bên:

1. **Điều ứng viên tự nói ra** — lưu nguyên văn, có ngoặc kép.
2. **Điều hệ thống tự tính ra** — mã đơn đang xét, nhãn chủ đề do luật từ khóa
   trong `topics.py` gán, không có mô hình nào tham gia.

**Không bao giờ là câu do một con bot sinh ra.**

Đây không phải sự thận trọng thừa. Nếu câu trả lời của khung chat lọt sang làm
dữ liệu đầu vào cho con tư vấn, thì một câu bịa ở bên phụ trợ sẽ được bên chính
đọc như sự thật, rồi nhắc lại với giọng chắc chắn hơn — và tới lượt thứ ba thì
không ai còn truy được nó bắt nguồn từ đâu. Một lần bịa sẽ tự bồi thành hồ sơ.

Nên bộ nhớ này chỉ chở **chủ đề đã bàn**, không chở nội dung đã nói. Bên nhận
biết "khách đã hỏi về chi phí, phía kia đã giải thích rồi", và nó phải **tự dựng
lại câu trả lời từ nguồn của chính mình**. Biết là đã bàn thì đủ để không hỏi lại
và không lặp; còn nội dung thì mỗi bên tự chịu trách nhiệm, truy được về nguồn
của bên ấy.

## Gói này không phụ thuộc bên nào

`app/memory` không import `app.advisor`, cũng không import `app.llm`/`app.rag`/
`app.conversation`. Nó nằm dưới cả hai. Ngược lại thì nó thành cây cầu nối hai bờ
đúng theo nghĩa xấu: sửa một bên là gãy bên kia, và cái ranh giới mà
`tests/test_advisor_boundary.py` canh giữ sẽ bị đi vòng qua chính chỗ này.

Có ca kiểm thử canh điều đó trong `tests/test_memory_chung.py`.
"""
