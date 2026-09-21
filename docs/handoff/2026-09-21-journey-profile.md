# Nối hội thoại với hồ sơ ứng viên

## Phạm vi bản thay đổi

Code làm việc nằm trong `xkld-chatbot`, không sửa bản đóng gói `.push-web-xkld`. Không commit hoặc push. Giữ các thay đổi local có sẵn.

- Website dùng chung `journeySession` cho chat và CV. Giữ nguyên UUID dạng hex của CV cũ và UUID có dấu gạch của chat cũ.
- Khi hai phiên cũ khác nhau đã tồn tại, ưu tiên phiên CV cho hành trình mới. Không ghép dữ liệu trên server, không xóa lịch sử server của phiên cũ. Muốn hợp nhất dữ liệu cũ cần một quy trình xác minh riêng.
- Hội thoại tạo/cập nhật cùng Candidate Profile mà luồng CV đọc. Trích xuất quy tắc bước đầu chỉ nhận một số lời tự khai rõ ràng: tên, chứng chỉ tiếng Nhật, địa điểm mong muốn, số điện thoại.
- Consultation Profile là đối tượng nghiệp vụ **nhúng trong cùng document MongoDB**, không phải collection độc lập ở bước này. `consultation` lưu tối đa 20 phát biểu gần đây và 20 mâu thuẫn. API xuất `consultation_profile` gồm phần này và `preferences` hiện có. Matching tiếp tục đọc `preferences`; không tạo hai bản dữ liệu nguyện vọng có nguy cơ lệch nhau.
- Khóa phiên bản bảo vệ cập nhật đồng thời. Dữ liệu chat không ghi đè CV hoặc thông tin đã xác nhận. Thông tin máy mới thêm phải chờ xác nhận; xác nhận nâng nguồn trường thành `user_confirmed`.
- Trang `/admin/profiles/[code]` hiển thị phát biểu nguyên văn và mâu thuẫn. Report mới chụp thêm phần tư vấn, phân biệt lời nói chưa xác nhận với thông tin đã xác nhận.

## Kiểm thử

- Backend: 562 test thành công, gồm 12 test mới cho hồ sơ hành trình.
- Frontend: 5 test Node cho phiên dùng chung thành công.
- Cả hai frontend qua kiểm tra TypeScript. Build quản trị thành công.
- Test tích hợp dùng dịch vụ thật, tầng lưu hồ sơ thật, CV merge và HTTP TestClient; chỉ thay Mongo I/O bằng collection giả trong bộ nhớ. Không đánh đồng với kiểm thử MongoDB/Gemini/Qdrant thật.

## Thử thủ công khi bật đủ dịch vụ

1. Trong cùng trình duyệt, vào chat và gửi `Tôi tên Nam, tôi đã có N4, tôi muốn đi Osaka`.
2. Mở `/tu-van`. Hồ sơ phải có tên, N4 và Osaka, còn chờ xác nhận.
3. Gửi một CV có dữ liệu bổ sung, kiểm tra mã hồ sơ không đổi.
4. Kiểm tra và xác nhận các ô, sau đó trở lại chat gửi `Tôi đã có N1`.
5. Hồ sơ đã xác nhận vẫn giữ N4; nhân viên có quyền mở hồ sơ thấy đề xuất N1 dưới mục cần kiểm tra.
6. Đăng ký một đơn bằng luồng hiện có và kiểm tra report mới chứa trích lời khách cùng nhãn chưa xác nhận.
7. Bắt đầu hồ sơ mới: khung chat đang mở phải bỏ nội dung phiên cũ, không nhận câu trả lời đang chờ của phiên cũ vào phiên mới.

## Giới hạn và phần tiếp theo

- Đây là bước nối dữ liệu, không phải AI trích xuất mọi cách nói tự nhiên. Câu không khớp quy tắc chỉ lưu nguyên văn; không suy đoán năng lực hay mong muốn.
- Chưa thêm form liên hệ độc lập, chưa làm tự động Lead/Appointment mới trong bước này.
- Nếu phần lưu bổ sung hồ sơ thất bại, câu trả lời chat vẫn thành công và ghi cảnh báo. Tin nhắn gốc còn trong kho hội thoại; chưa có worker tự đồng bộ bù.
- Các phiên cũ chưa được backfill; report đã sinh trước đó không tự viết lại.
- Mã phiên dùng chung không thay thế xác thực quyền sở hữu. Cơ chế token/cookie cho hồ sơ công khai, phục hồi hành trình giữa các thiết bị và xử lý phiên hết hạn vẫn là công việc tiếp theo.
- Chưa xác nhận chạy E2E với dịch vụ thật. Không dùng số lượng unit test để tuyên bố sản phẩm đã sẵn sàng production.
