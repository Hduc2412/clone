# Workflow nghiệp vụ

## 1. Luồng tư vấn bằng AI

```mermaid
flowchart TD
    A["Khách gửi câu hỏi"] --> B["Phân loại ý định"]
    B --> C["Trích xuất thông tin"]
    C --> D["Truy xuất tài liệu liên quan từ Qdrant"]
    D --> E["Tạo prompt từ ý định, lịch sử và tri thức"]
    E --> F["Gemini tạo câu trả lời"]
    F --> G{"Kiểm tra phản hồi"}
    G -- "Đạt" --> H["Trả lời kèm nguồn"]
    G -- "Thiếu căn cứ / lỗi" --> I["Fallback an toàn"]
    H --> J["Lưu hội thoại và thống kê"]
    I --> J
```

Nguyên tắc:

- Chỉ trả lời theo cơ sở tri thức của doanh nghiệp.
- Ưu tiên đúng tiêu đề và đúng section của tài liệu.
- Không bịa thông tin khi kết quả truy xuất yếu.
- Giới hạn lịch sử đưa vào prompt để tiết kiệm hạn mức miễn phí.

## 2. Luồng chatbot đặt lịch

```mermaid
flowchart TD
    A["Khách yêu cầu đặt lịch"] --> B["Thu họ tên"]
    B --> C["Thu số điện thoại"]
    C --> D["Thu ngày mong muốn"]
    D --> E["Thu giờ mong muốn"]
    E --> F{"Ngày giờ hợp lệ?"}
    F -- "Không" --> D
    F -- "Có" --> G["Hiển thị thông tin xác nhận"]
    G --> H{"Khách xác nhận?"}
    H -- "Không / sửa" --> B
    H -- "Có" --> I["Tạo mã lịch và trạng thái pending"]
    I --> J["Tạo thông báo cho nhân viên"]
    J --> K["Nhân viên xác nhận và gọi khách"]
```

Trạng thái lịch:

```mermaid
stateDiagram-v2
    [*] --> pending
    pending --> confirmed
    pending --> cancelled
    confirmed --> completed
    confirmed --> unreachable
    confirmed --> rescheduled
    confirmed --> cancelled
    unreachable --> rescheduled
    unreachable --> cancelled
```

## 3. Luồng xử lý lịch của nhân viên

1. Nhân viên mở danh sách lịch mới.
2. Hệ thống hiển thị mã lịch, tên, số điện thoại, ngày và giờ.
3. Nhân viên kiểm tra và chuyển lịch sang `confirmed`.
4. Nhân viên gọi khách bằng số điện thoại đã thu.
5. Sau liên hệ, nhân viên cập nhật:
   - `completed`: đã tư vấn xong.
   - `unreachable`: chưa liên hệ được.
   - `rescheduled`: đã đổi lịch.
   - `cancelled`: lịch bị hủy.

## 4. Luồng quản lý khách hàng/lead

```mermaid
flowchart LR
    A["Nhân viên tạo lead"] --> B["Mới"]
    B --> C["Đang liên hệ"]
    C --> D["Đủ điều kiện"]
    C --> E["Chưa liên hệ được"]
    D --> F["Tạo hồ sơ/đơn tuyển dụng"]
    E --> C
    B --> G["Đóng"]
    C --> G
```

Lưu ý: lịch do chatbot tạo không tự biến thành lead. Nhân viên quyết định tạo lead sau khi xác nhận nhu cầu thực tế.

## 5. Luồng quản lý tri thức

```mermaid
flowchart TD
    A["Admin/Manager tải tài liệu"] --> B["Kiểm tra định dạng và virus"]
    B --> C["Đọc PDF, Word, FAQ hoặc ảnh"]
    C --> D["Tách section theo tiêu đề"]
    D --> E["Chunk có metadata"]
    E --> F["Embedding vào collection staging"]
    F --> G["Kiểm tra đủ nội dung và truy xuất thử"]
    G --> H{"Đạt nghiệm thu?"}
    H -- "Không" --> C
    H -- "Có" --> I["Tạo version và chuyển alias chính"]
    I --> J["Giữ collection cũ để rollback"]
```

## 6. Luồng người dùng và phân quyền dự kiến

```mermaid
flowchart TD
    A["Đăng nhập"] --> B{"Vai trò"}
    B --> C["Admin: toàn quyền"]
    B --> D["Manager: quản lý nghiệp vụ và báo cáo"]
    B --> E["Consultant: lịch, lead, hội thoại được phép xem"]
    C --> F["Ghi nhật ký thao tác"]
    D --> F
    E --> F
```

Phân quyền phải được kiểm tra tại backend; ẩn nút trên giao diện không được xem là bảo mật.

Nhật ký hệ thống:

- Ghi đăng nhập thành công/thất bại, đăng xuất và đổi mật khẩu.
- Ghi thao tác tạo/cập nhật tài khoản, khách hàng và lịch hẹn.
- Chỉ `admin` và `manager` được xem; `consultant` không có quyền truy cập API.
- Không lưu mật khẩu, token, nội dung ghi chú khách hàng hoặc giá trị dữ liệu nhạy cảm.
- Hỗ trợ lọc theo người thao tác, hành động, kết quả và khoảng ngày.

Quyền đối với lịch hẹn:

- `admin` và `manager` xem toàn bộ lịch, phân công hoặc chuyển người phụ trách.
- `consultant` chỉ xem và cập nhật lịch có `assigned_to` trùng email tài khoản của mình.
- Lịch chưa phân công chỉ hiển thị cho `admin` và `manager`.
- `consultant` không được tự nhận lịch hoặc xem lịch sử xử lý của lịch thuộc người khác.

## 7. Luồng tổng hợp Dashboard

Dashboard đọc dữ liệu từ MongoDB để hiển thị:

- Số khách hàng/lead.
- Số hội thoại.
- Lịch mới và lịch theo trạng thái.
- Ý định phổ biến.
- Câu hỏi/fallback phổ biến.
- Tỷ lệ chuyển đổi theo từng giai đoạn.
- Hiệu quả xử lý của nhân viên khi module phân công hoàn thiện.
