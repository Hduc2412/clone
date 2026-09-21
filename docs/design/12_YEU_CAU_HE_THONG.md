# 12 — Yêu cầu hệ thống

> Tài liệu mô tả **hệ thống cần làm được gì**, viết cho người đọc không cần biết code.
> Không chứa số liệu đo kiểm, không mô tả thuật toán.
> Xem kèm: [Kiến trúc tổng quan](11_KIEN_TRUC_TONG_QUAN.md) · [Phạm vi và trạng thái](13_PHAM_VI_VA_TRANG_THAI.md)

---

## 1. Ba nhóm người dùng

| Nhóm | Họ là ai | Điều họ cần |
|---|---|---|
| **Ứng viên** | Người muốn đi làm điều dưỡng tại Nhật. Truy cập ẩn danh, phần lớn vào ngoài giờ hành chính, chủ yếu bằng điện thoại. | Biết mình có đủ điều kiện không, tổng chi phí bao nhiêu, quy trình mấy bước, có đơn hàng nào hợp không, và nói chuyện được với người thật khi cần. |
| **Nhân viên tư vấn** | Người trực tiếp gọi điện và chốt ứng viên. | Biết ai đang thực sự quan tâm, họ đã hỏi gì, ca nào cần gọi gấp — mà không phải đọc lại cả cuộc hội thoại. |
| **Quản lý / Quản trị viên** | Người phụ trách đội tư vấn và nội dung hệ thống. | Nắm được tình hình chung, phân công công việc, cập nhật chính sách và danh mục đơn hàng, kiểm soát ai làm gì trên hệ thống. |

Ứng viên **không có tài khoản**. Nhân viên và quản lý **bắt buộc đăng nhập**.

---

## 2. Yêu cầu chức năng

### 2.1. Nhóm A — Kênh khách hàng

> **Đây là yêu cầu nghiệp vụ, không phải đặc tả giao diện.** Cấu trúc website, vị trí
> chatbot và UI/UX **chưa được thống nhất** trong giai đoạn này.

| Mã | Yêu cầu |
|---|---|
| A1 | Khách truy cập được mà không cần tài khoản |
| A2 | Trò chuyện tư vấn và gửi CV ngay trong kênh |
| A3 | Xem các đơn được hệ thống gợi ý, kèm lý do từng đơn |
| A4 | Tự chọn đơn muốn đăng ký và xác nhận lại rõ ràng |
| A5 | Đặt lịch hẹn để nhân viên gọi lại |
| A6 | Nếu kênh có danh mục đơn, chỉ hiển thị đơn đã được duyệt công khai và còn đang tuyển |

### 2.2. Nhóm B — Tư vấn tự động

| Mã | Yêu cầu |
|---|---|
| B1 | Trả lời câu hỏi thường gặp dựa trên tài liệu chính thức của công ty, hoạt động liên tục kể cả ngoài giờ |
| B2 | Hiểu được câu hỏi nối tiếp trong cùng cuộc trò chuyện, không bắt người dùng nhắc lại từ đầu |
| B3 | Khi không đủ căn cứ để trả lời, phải nói rõ là chưa có thông tin và mời gặp nhân viên — **không được đoán bừa** |
| B4 | Mọi câu trả lời liên quan đến chính sách, chi phí, điều kiện đều phải dẫn được về tài liệu gốc |
| B5 | Nhận được yêu cầu gặp người thật bất cứ lúc nào và chuyển tiếp ngay |

### 2.3. Nhóm C — Đọc hồ sơ ứng viên

| Mã | Yêu cầu |
|---|---|
| C1 | Nhận file CV do ứng viên tải lên trong kênh khách hàng |
| C2 | Đọc nội dung file và rút ra thông tin năng lực: họ tên, năm sinh, chuyên ngành, trình độ tiếng Nhật, kinh nghiệm |
| C3 | Ghi nhận riêng phần nguyện vọng do ứng viên nói: khu vực mong muốn, loại hình công việc, lý do |
| C4 | **Chỉ ghi nhận điều có trong hồ sơ hoặc lời ứng viên.** Không suy diễn, không tự thêm nhận xét cảm tính |
| C5 | Thông tin không chắc chắn thì hỏi lại ứng viên để xác nhận, không tự quyết |
| C6 | Cho ứng viên xem lại và sửa thông tin đã rút ra trước khi dùng |

### 2.4. Nhóm D — Giới thiệu đơn hàng phù hợp

| Mã | Yêu cầu |
|---|---|
| D1 | Đối chiếu hồ sơ ứng viên với danh mục đơn hàng đang tuyển |
| D2 | Loại bỏ đơn hàng mà ứng viên **chắc chắn không đủ điều kiện** (trình độ tiếng, bằng cấp, độ tuổi, hạn nộp) |
| D3 | Sắp xếp các đơn còn lại theo mức độ khớp với nguyện vọng |
| D4 | Với mỗi đơn được giới thiệu, phải nêu rõ **vì sao phù hợp** và **điểm nào còn thiếu** |
| D5 | Kết quả giới thiệu phải tái lập được: cùng một hồ sơ, cùng một danh mục thì cho cùng một kết quả |
| D6 | Không hứa hẹn chắc chắn đỗ; chỉ nêu mức độ phù hợp trên giấy tờ |

### 2.5. Nhóm E — Đặt lịch và bàn giao

| Mã | Yêu cầu |
|---|---|
| E1 | Sau khi tư vấn, chủ động mời ứng viên đặt lịch để nhân viên gọi lại |
| E2 | Thu đủ thông tin liên hệ và khung giờ mong muốn, có bước xác nhận lại trước khi lưu |
| E3 | Chỉ nhận lịch trong giờ làm việc thực tế của công ty |
| E4 | Tự động tạo **Phiếu tóm tắt tư vấn** gồm: thông tin ứng viên, điểm mạnh, điểm còn thiếu, đơn hàng đã giới thiệu, các câu đã hỏi, khung giờ hẹn |
| E5 | Đẩy phiếu và lịch hẹn vào hệ thống nội bộ ngay, không chờ nhân viên thao tác |
| E6 | Thông báo cho nhân viên khi có lịch hẹn mới |
| E7 | Chỉ tạo **đăng ký sơ bộ** khi đã có số điện thoại hợp lệ và ứng viên đã tải CV, đặt lịch hoặc nêu rõ nhu cầu |
| E8 | Tạo hoặc cập nhật khách hàng theo **số điện thoại đã chuẩn hóa**, không tạo trùng |

### 2.6. Nhóm F — Hệ thống nội bộ

| Mã | Yêu cầu |
|---|---|
| F1 | Màn hình tổng quan: khách mới, lịch hẹn hôm nay, việc cần xử lý |
| F2 | Hàng đợi khách tiềm năng, mở ra là thấy ngay Phiếu tóm tắt |
| F3 | Hồ sơ ứng viên tập trung: CV gốc, thông tin đã rút ra, hội thoại, đơn hàng đã giới thiệu, lịch hẹn, lịch sử thay đổi |
| F4 | Quản lý lịch hẹn: lọc, phân công, đổi lịch, ghi kết quả cuộc gọi |
| F5 | Quản lý danh mục đơn hàng: thêm, sửa, bật/tắt công khai, nhập hàng loạt từ file của công ty |
| F6 | Xem lại nhật ký giới thiệu: hệ thống đã gợi ý gì cho ai và vì sao |
| F7 | Quản lý tài liệu tri thức: thêm, cập nhật, theo dõi trạng thái |
| F8 | Quản lý người dùng nội bộ theo ba vai trò, kèm nhật ký thao tác |
| F9 | **Hàng đợi hồ sơ**: nhân viên nhận xử lý, phân công, chuyển người phụ trách. Một hồ sơ chỉ có một người phụ trách tại một thời điểm |
| F10 | **Vòng đời trạng thái** cho đơn tuyển dụng và hồ sơ đăng ký; mỗi lần chuyển trạng thái lưu người thao tác, thời điểm và ghi chú |
| F11 | **Quản lý nhân viên và hiệu suất**: khối lượng, thời gian phản hồi, điểm lưu **theo từng sự kiện** kèm nguồn và lý do, không chỉ một số tổng |

---

## 3. Yêu cầu phi chức năng

| Nhóm | Yêu cầu |
|---|---|
| **Tin cậy nội dung** | Thà trả lời "chưa có thông tin" còn hơn trả lời sai. Mọi khẳng định về chính sách phải truy được nguồn. |
| **Giải trình** | Mọi đề xuất đơn hàng phải giải thích được từng tiêu chí. Người ngoài đọc phải hiểu vì sao hệ thống chọn như vậy. |
| **Thẩm quyền** | Hệ thống chỉ sơ tuyển và đề xuất. Quyền nhận hay loại ứng viên thuộc về nhân viên. |
| **Bảo mật** | Kênh khách hàng không có đường truy cập trực tiếp vào dữ liệu nội bộ. Mọi thao tác nội bộ đều phải đăng nhập và được ghi nhật ký. |
| **Dữ liệu cá nhân** | CV và thông tin liên hệ chỉ dùng cho mục đích tư vấn. Có thể xóa dữ liệu phiên theo yêu cầu. |
| **Khả dụng** | Phần tư vấn phải hoạt động ngoài giờ hành chính — đó là lý do tồn tại của hệ thống. |
| **Trải nghiệm** | Chưa chốt UI/UX. Khi thiết kế cần kiểm tra khả năng sử dụng trên điện thoại, vì phần lớn ứng viên truy cập bằng điện thoại. |
| **Chi phí vận hành** | Giai đoạn đồ án ưu tiên phương án miễn phí, chạy được trên máy cá nhân. |

---

## 4. Những điều hệ thống **không** làm

Ghi rõ để tránh hiểu nhầm khi trình bày:

- Không thay nhân viên quyết định nhận hay loại ứng viên.
- Không cam kết ứng viên sẽ trúng tuyển hay xuất cảnh đúng hạn.
- Không tự huấn luyện mô hình ngôn ngữ riêng.
- Không đánh giá tính cách, thái độ hay tiềm năng của ứng viên.
- Không thay thế hợp đồng, tư vấn pháp lý hay hồ sơ chính thức.
- Không thu thập dữ liệu ngoài phạm vi phục vụ tư vấn.
