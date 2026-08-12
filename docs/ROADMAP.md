# Kế hoạch triển khai

## Nguyên tắc thực hiện

- Làm theo từng giai đoạn, không chạy theo tiến độ gấp.
- Mỗi giai đoạn phải có tiêu chí hoàn thành và kiểm thử.
- Ưu tiên giải pháp miễn phí, chạy local trong giai đoạn đồ án.
- Chưa triển khai Zalo cho đến khi có yêu cầu mới.
- Không public hệ thống quản lý trước khi hoàn thành xác thực và phân quyền.

## Giai đoạn 0 — Nền tảng hiện tại

Trạng thái: **đã có MVP local**.

- [x] Chatbot RAG.
- [x] Phân loại ý định và trích xuất thông tin cơ bản.
- [x] Kiểm soát truy xuất, nguồn và fallback.
- [x] Đặt lịch qua chatbot.
- [x] Thông báo lịch mới cho nhân viên.
- [x] Dashboard quản lý local.
- [x] Trang lịch hẹn, lead, hội thoại, tri thức và người dùng.
- [x] API quản lý và dữ liệu MongoDB.
- [x] Kiểm thử backend và build frontend.

## Giai đoạn 1 — Xác thực và phân quyền

Trạng thái: **MVP và quyền sở hữu lịch hẹn đã hoàn thành, tiếp tục audit log**.

1. Chốt quyền chi tiết cho `admin`, `manager`, `consultant`.
2. Thiết kế tài khoản, mật khẩu băm, phiên đăng nhập và refresh token.
3. Làm API đăng nhập/đăng xuất/đổi mật khẩu.
4. Bảo vệ toàn bộ API `/management`, `/appointments`, `/notifications`.
5. Bảo vệ route `/admin` ở frontend.
6. Thêm nhật ký đăng nhập và thao tác quan trọng.
7. Kiểm thử quyền truy cập theo từng vai trò.

Tiêu chí hoàn thành:

- Người chưa đăng nhập không xem được dữ liệu quản lý.
- Mỗi vai trò chỉ thao tác đúng quyền.
- Không lưu mật khẩu dạng rõ.

## Giai đoạn 2 — Hoàn thiện lịch hẹn

- [x] Bộ lọc ngày, trạng thái và nhân viên phụ trách.
- [x] Phân công lịch cho nhân viên.
- [x] Đổi lịch có lưu lịch sử.
- [x] Ghi chú kết quả cuộc gọi.
- [x] Chặn lịch trùng và cảnh báo lịch sắp tới trong 24 giờ.
- [x] Nhật ký tạo lịch, phân công và thay đổi trạng thái.
- [x] Thống kê tỷ lệ xác nhận, hoàn thành, không liên hệ được và hủy lịch.

Tiêu chí hoàn thành:

- Mọi thay đổi lịch đều truy vết được.
- Không tạo lịch trùng ngoài ý muốn.
- Nhân viên nhìn thấy rõ lịch cần xử lý.

## Giai đoạn 3 — Khách hàng và hồ sơ tuyển dụng

1. Chốt mô hình một khách hàng có nhiều hồ sơ/đơn theo thời gian.
2. Mỗi khách chỉ có tối đa một hồ sơ đang hoạt động, nếu nghiệp vụ xác nhận quy tắc này.
3. Thêm thông tin hồ sơ, trạng thái, ghi chú và người phụ trách.
4. Liên kết khách hàng với lịch hẹn và hội thoại.
5. Lưu lịch sử thay đổi hồ sơ.
6. Tìm kiếm và lọc khách hàng.

Tiêu chí hoàn thành:

- Không trùng khách theo số điện thoại.
- Xem được toàn bộ hành trình của khách trên một màn hình.

## Giai đoạn 4 — Knowledge Management

1. Upload PDF, Word, FAQ và ảnh từ giao diện.
2. Xem trước nội dung và tiêu đề/section đã nhận diện.
3. Chỉnh sửa metadata trước khi tạo embedding.
4. Ingestion vào staging.
5. Bộ kiểm thử truy xuất trước khi xuất bản.
6. Version, publish và rollback collection.
7. Nhật ký tài liệu và người cập nhật.

Tiêu chí hoàn thành:

- Tài liệu mới không ảnh hưởng collection chính trước khi nghiệm thu.
- Câu trả lời truy xuất đúng title và section.
- Có thể rollback khi bản tri thức mới gặp lỗi.

## Giai đoạn 5 — Analytics và báo cáo

1. Chuẩn hóa sự kiện và số liệu.
2. Biểu đồ hội thoại, lịch, lead, intent và fallback.
3. FAQ phổ biến và câu hỏi chưa trả lời tốt.
4. Tỷ lệ chuyển đổi từ tư vấn đến lịch và hồ sơ.
5. Bộ lọc theo thời gian và nhân viên.
6. Xuất báo cáo khi thực sự cần.

## Giai đoạn 6 — Website người dùng cuối

1. Trang chủ.
2. Giới thiệu công ty.
3. Điều kiện tham gia.
4. Chi phí.
5. Quy trình.
6. FAQ.
7. Chat Widget hoàn thiện.
8. Trang liên hệ/đặt lịch.
9. Tối ưu responsive, accessibility và SEO.

## Giai đoạn 7 — Đóng gói và triển khai

Chỉ thực hiện sau khi local ổn định:

1. Docker hóa frontend, backend, MongoDB và Qdrant.
2. Cấu hình Nginx.
3. Quản lý secret và biến môi trường.
4. Backup/restore MongoDB và Qdrant.
5. Giới hạn CORS, rate limit và log.
6. HTTPS và Cloudflare.
7. Kiểm thử production và kế hoạch rollback.

## Backlog chưa ưu tiên

- Zalo.
- Email/SMS nhắc lịch trả phí.
- MongoDB kết hợp PostgreSQL nếu dữ liệu quan hệ phát triển lớn.
- Phân tích AI nâng cao.
- Ứng dụng di động.

## Thứ tự đề xuất ngay sau bản hiện tại

1. Hoàn thiện audit log xác thực và thao tác quản trị.
2. Thiết kế module hồ sơ tuyển dụng.
3. Liên kết khách hàng với lịch hẹn và hội thoại.
4. Làm upload và version hóa cơ sở tri thức.
