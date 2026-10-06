r"""Agent điều phối tư vấn ứng viên — lớp nằm **trên** cả hai hệ AI.

## Vì sao là gói riêng, không nhét vào `app/advisor/`

`app/advisor/` có một ràng buộc được cưỡng chế bằng ca kiểm thử quét AST
(`tests/test_advisor_boundary.py`): nó **không được import gì từ phía chat**.
Ràng buộc ấy có lý do thật — hai hệ dùng hai khóa, hai hạn mức, và phải hỏng độc
lập với nhau.

Agent điều phối thì cần biết **cả hai bên đã nói gì** để không hỏi lại thứ khách
vừa trả lời ở bên kia. Nếu đặt nó trong `app/advisor/` thì hoặc phải nới ràng
buộc kia, hoặc phải viết một đường dây lách qua nó — cả hai đều làm mất đúng thứ
ranh giới ấy đang bảo vệ.

Nên Agent nằm ở tầng trên, và nó là nơi **duy nhất** được nhìn cả hai hệ:

```
                app/agent/            ← điều phối, biết cả hai bên
               /          \
    app/advisor/            app/llm + app/rag
    (engine tư vấn)         (khung chat phụ trợ)
               \          /
                app/memory/           ← bộ nhớ chung, chở câu hỏi không chở câu trả lời
```

## Ba thứ Agent KHÔNG được làm

**Không tự khai trạng thái.** Giai đoạn của ứng viên suy ra từ dữ liệu thật —
hồ sơ có chưa, đã xác nhận chưa, đã đối chiếu chưa, đang mở yêu cầu hỗ trợ nào.
`state.py` làm việc đó bằng quy tắc thuần. Bản thiết kế ban đầu để mô hình tự
khai `current_stage`, và đó là chỗ phải sửa: mô hình khai lệch một lần là giao
diện nhảy bước, mà không có cách nào biết nó lệch.

**Không quyết đạt hay không đạt.** Việc ấy của `app/matching/engine.py`, thuần
và tất định. Agent chỉ đọc kết quả rồi diễn đạt.

**Không tự ghi vào hồ sơ.** Mô hình được *đề xuất* dưới dạng có cấu trúc; backend
kiểm trường, kiểm kiểu, ép nguồn thành `chat`, và chỉ ghi khi **người dùng bấm
xác nhận**. Xem `contract.py`.

## Template trước, mô hình sau

Mọi lượt Agent chủ động nói đều dựng được bằng template từ dữ liệu có cấu trúc.
Mô hình chỉ diễn đạt lại cho dễ đọc, và **được phép thất bại** — khi ấy màn hình
vẫn đủ chữ.

Đây không phải cẩn thận chung chung. Hạn mức gói miễn phí là 20 lượt mỗi ngày
mỗi model, và nó đã cạn giữa một lượt đo thật ngày 01/10. Một Agent bắt buộc gọi
mô hình mỗi lượt thì buổi bảo vệ có thể trống màn hình đúng lúc đang trình bày.
"""
