# Phạm vi công việc — phát triển web và hệ thống nghiệp vụ

**Đồ án:** Xây dựng hệ thống AI hỗ trợ tư vấn, định hướng hồ sơ và quản trị tuyển dụng điều dưỡng Nhật Bản
**Sinh viên:** Hoàng Minh Đức — 2200583 · **GVHD:** TS. Nguyễn Hồng Quân
**Thời gian còn lại:** 11/09/2026 → 25/10/2026 (6 tuần + 3 ngày đệm)
**Lập ngày:** 11/09/2026

Tài liệu này chốt *làm gì* và *không làm gì* trong giai đoạn còn lại. Nguồn căn cứ: Báo cáo tổng quan
hệ thống (09/2026) và `docs/design/11`–`14`.

---

## 1. Vì sao cần chốt phạm vi

Phần nền móng đã chạy được: chatbot tư vấn theo tài liệu công ty, đặt lịch qua chat, và hệ thống
quản trị nội bộ có đăng nhập, lịch hẹn, khách hàng, hội thoại, nhật ký thao tác.

Nhưng đó mới là một chatbot trả lời câu hỏi. Thứ làm nên giá trị của đề tài là **chuỗi chuyển đổi
từ dữ liệu phi cấu trúc sang quyết định nghiệp vụ có cấu trúc**, và chuỗi đó hiện chưa có dòng nào:

```
đơn tuyển dụng → đọc CV → hồ sơ có cấu trúc → đối chiếu có giải trình
  → ứng viên chọn đơn và xác nhận → đăng ký sơ bộ + phiếu tóm tắt
  → hàng đợi nhân viên → vòng đời trạng thái → điểm nhân viên
```

Thứ tự trên **không đảo được**, vì mỗi bước là đầu vào của bước sau. Không có danh mục đơn thì
bộ đối chiếu không có gì để so.

---

## 2. Ai làm gì

| Phần | Người phụ trách |
|---|---|
| Chat widget, pipeline RAG, intent, entity, Gemini, ingestion tri thức | **Bên khác** |
| Website khách hàng, toàn bộ nghiệp vụ đơn hàng / CV / đối chiếu / hồ sơ / hàng đợi / điểm, hệ thống quản trị, đóng gói Docker | **Phần việc của đồ án này** |

**Các file không được chạm** (thuộc bên widget): `backend/app/conversation/*`, `app/rag/*`,
`app/llm/gemini.py`, `app/services/chat_service.py`, `app/api/chat.py`, `ingestion/*`,
`frontend/components/Chat*`, `frontend/hooks/useChat.ts`, `frontend/lib/api.ts`.

**Luồng ứng viên là một web riêng, không đi qua khung chat.** Gửi CV, xác nhận hồ sơ, xem đơn phù
hợp, chọn đơn và đặt lịch đều diễn ra trên các trang của website, có giao diện từng bước rõ ràng.
Ứng viên tự nhập tên và số điện thoại, không cần mở chat. Khung chat vẫn nằm ở góc màn hình nhưng
chỉ làm việc hỏi đáp như hiện nay.

Luồng này **tự sinh mã phiên riêng**, không đọc ké phiên của widget, nên hai bên không phụ thuộc
nhau và bản demo không gãy khi bên kia sửa widget. Mọi endpoint phục vụ luồng nằm dưới tiền tố
`/public/`. Hợp đồng dữ liệu vẫn được viết thành tài liệu gửi họ, để sau này muốn đưa các thẻ này
vào trong khung chat thì làm được, nhưng đó là việc tùy chọn ngoài phạm vi bảo vệ.

---

## 3. Trong phạm vi

### 3.1 Danh mục đơn tuyển dụng

Quản lý đơn hàng đang tuyển, tách bạch **điều kiện bắt buộc** (tiếng Nhật, bằng cấp, kinh nghiệm,
độ tuổi, giới tính, hạn nộp) khỏi **thông tin tham khảo** (lương, phụ cấp, chi phí, ngày phỏng vấn).

Việc tách này ngay từ lúc nhập liệu là điều làm cho phần giới thiệu về sau giải trình được:
mỗi điều kiện bắt buộc sinh ra đúng một dòng "đạt" hoặc "không đạt".

Bao gồm: màn hình quản lý, vòng đời trạng thái (nháp, đang tuyển, tạm dừng, đủ số lượng, hết hạn,
đã đóng), cờ công khai, nhập hàng loạt từ file Excel có xem trước và báo lỗi từng dòng,
danh sách đơn công khai trên website.

### 3.2 Đọc hồ sơ CV

Ứng viên gửi file PDF hoặc Word ngay trong khung chat. Hệ thống đọc nội dung, rút ra thông tin
năng lực và nguyện vọng, rồi **cho ứng viên xem lại và sửa trước khi dùng**.

Nguyên tắc bắt buộc: chỉ ghi nhận điều có trong hồ sơ hoặc lời ứng viên. Mỗi thông tin rút ra
phải kèm trích dẫn nguyên văn làm căn cứ. Thông tin không có căn cứ thì để trống, không đoán.
Hệ thống không nhận xét tính cách, thái độ hay tiềm năng.

Việc kiểm tra căn cứ này làm **bằng code**, không chỉ dựa vào lời dặn trong prompt. Những giá trị
bị loại được lưu lại để chứng minh khi bảo vệ.

### 3.3 Đối chiếu và giới thiệu đơn hàng

Ba bước theo đúng thứ tự:

1. **Loại trừ** — bỏ đơn ứng viên chắc chắn không đủ điều kiện. Sai một điều kiện bắt buộc là loại.
2. **Sắp xếp** — các đơn còn lại xếp theo mức độ khớp nguyện vọng: khu vực, loại hình cơ sở, mức lương.
3. **Giải thích** — mỗi đơn ghi rõ tiêu chí nào đạt, tiêu chí nào chưa, ứng viên còn thiếu điểm gì.

Điểm số do quy tắc rõ ràng tính, trí tuệ nhân tạo chỉ diễn đạt kết quả cho dễ đọc. Nhờ vậy cùng
một hồ sơ và cùng một danh mục luôn cho ra cùng một kết quả, kiểm thử được và giải trình được.
Tắt phần trí tuệ nhân tạo đi hệ thống vẫn chạy đủ.

Mọi lần đối chiếu được ghi vào **nhật ký giới thiệu**, lưu cả những đơn bị loại kèm lý do.
Đây là màn hình để chứng minh hệ thống không bịa.

### 3.4 Đăng ký sơ bộ và bàn giao

Hệ thống gợi ý nhiều đơn, nhưng **chỉ ứng viên mới chọn đơn muốn đăng ký**, và phải xác nhận
bằng một câu rõ ràng trước khi hệ thống tạo hồ sơ. Không tạo đăng ký từ suy đoán.

Sau khi xác nhận: tạo hoặc cập nhật khách hàng theo số điện thoại đã chuẩn hóa, tạo hồ sơ đăng ký
sơ bộ, tạo lịch hẹn gọi lại, và sinh **Phiếu tóm tắt tư vấn** gồm thông tin ứng viên, điểm mạnh,
điểm còn thiếu, các đơn đã giới thiệu kèm lý do, đơn đã chọn, các câu đã hỏi, khung giờ hẹn,
liên kết tới CV và hội thoại gốc.

Vai trò của phiếu: nén một cuộc hội thoại dài thành thứ nhân viên đọc trong vài chục giây.

### 3.5 Hàng đợi và xử lý của nhân viên

Phiếu mới vào hàng đợi chung ở trạng thái chờ tiếp nhận. Nhân viên nhận hồ sơ về mình, và
**một hồ sơ chỉ có một người phụ trách tại một thời điểm** — hai người bấm cùng lúc thì chỉ một
người nhận được. Chuyển giao hồ sơ phải ghi lý do và lưu lịch sử.

Vòng đời trạng thái hồ sơ từ lúc vào hàng đợi đến kết quả cuối, mỗi lần chuyển lưu người thao tác,
thời điểm và ghi chú.

Màn hình hồ sơ ứng viên tập trung: phiếu tóm tắt, CV gốc, thông tin đã rút ra kèm nhãn nguồn,
hội thoại, đơn đã chọn, lịch hẹn và lịch sử trạng thái — tất cả trên một màn hình.

### 3.6 Điểm nhân viên

Điểm lưu **theo từng sự kiện** kèm nguồn và lý do, không lưu một con số tổng, để luôn truy ngược
được vì sao điểm thay đổi. Sự kiện hệ thống không trừ điểm; trừ điểm chỉ do quản lý và bắt buộc
ghi lý do vào nhật ký.

### 3.7 Website khách hàng

Trang chủ, giới thiệu chương trình, điều kiện tham gia, chi phí, quy trình, câu hỏi thường gặp,
danh sách và chi tiết đơn hàng công khai, liên hệ. Khung chat nhúng ở mọi trang.
Thiết kế ưu tiên điện thoại, vì phần lớn ứng viên truy cập bằng điện thoại.

### 3.8 Đóng gói và triển khai

Một lệnh dựng đủ cơ sở dữ liệu, kho vector, backend, hai ứng dụng web và máy chủ proxy trên
máy cá nhân. Kèm hướng dẫn chạy.

---

## 4. Ngoài phạm vi

Ghi rõ để tránh hiểu nhầm khi trình bày. Tất cả đưa vào phần hướng phát triển của báo cáo.

| Nội dung | Lý do |
|---|---|
| Quản lý tri thức: tải tài liệu lên và tạo vector từ màn hình quản trị | Thuộc bên widget/RAG. Ta viết tài liệu đặc tả gửi họ, màn hình quản trị chờ API của họ |
| Nhân viên tiếp quản chat trực tiếp lúc khách đang online | Cần người trực liên tục, là bài toán vận hành chứ không phải bài toán kỹ thuật |
| Tích hợp Facebook Messenger và Zalo OA | Phụ thuộc phê duyệt nền tảng và tài khoản doanh nghiệp thật |
| Nhắc lịch hẹn qua tin nhắn | Là dịch vụ trả phí |
| Chấm điểm phù hợp bằng học máy | Chưa có dữ liệu lịch sử để học, và mô hình học được sẽ không giải trình được — đi ngược yêu cầu cốt lõi |
| Ứng dụng di động riêng | Chưa cần thiết cho mục tiêu tư vấn và sơ tuyển |
| Tài khoản đăng nhập cho ứng viên | Ứng viên định danh bằng phiên trò chuyện và số điện thoại là đủ |
| Đồng bộ đơn hàng tự động từ đối tác Nhật Bản | Không có API đối tác |
| Đưa lên máy chủ công khai có tên miền | Chạy Docker trên máy cá nhân là đủ để chứng minh đóng gói được |

---

## 5. Sản phẩm bàn giao

| # | Sản phẩm |
|---|---|
| 1 | Website giới thiệu chương trình có khung chat tư vấn |
| 2 | Luồng tư vấn riêng trên website: gửi CV, xác nhận hồ sơ, xem đơn gợi ý kèm lý do, chọn đơn, đặt lịch |
| 3 | Hệ thống quản trị: đơn tuyển dụng, hàng đợi hồ sơ, hồ sơ ứng viên tập trung, nhật ký giới thiệu, nhân viên và hiệu suất, cùng các màn hình đã có |
| 4 | Backend với bộ đối chiếu tất định và bộ kiểm chứng căn cứ |
| 5 | File Excel chủ để doanh nghiệp nhập đơn hàng thật, kèm hướng dẫn |
| 6 | Tài liệu đặc tả gửi bên widget/RAG |
| 7 | Bản đề xuất vòng đời trạng thái hồ sơ để duyệt |
| 8 | Bộ kiểm thử tự động và cấu hình Docker |

---

## 6. Tiến độ

| Tuần | Ngày | Nội dung | Kết quả |
|---|---|---|---|
| 1 | 11–17/09 | Nền dùng chung; danh mục đơn tuyển dụng đầy đủ; file Excel chủ; 19 đơn mẫu | Có nguồn đơn chuẩn để công khai và đối chiếu |
| 2 | 18–24/09 | Nhận CV, đọc nội dung, lập hồ sơ có nguồn, ứng viên xác nhận | CV tạo được hồ sơ kiểm tra lại được với bản gốc |
| 3 | 25/09–01/10 | Bộ đối chiếu, giải thích từng tiêu chí, nhật ký giới thiệu | Kết quả tái lập được, giải trình được |
| 4 | 02–08/10 | Xác nhận chọn đơn, đăng ký sơ bộ, phiếu tóm tắt, hàng đợi, vòng đời trạng thái | Nhân viên nhận đủ bối cảnh mà không nhập lại |
| 5 | 09–15/10 | Điểm nhân viên theo sự kiện; đóng gói Docker | Theo dõi được hiệu suất; dựng được bằng một lệnh |
| 6 | 16–22/10 | Website khách hàng, kiểm thử toàn tuyến, dữ liệu demo | Hệ thống hoàn chỉnh, kịch bản demo chạy được |
| Đệm | 23–25/10 | Chốt mã nguồn, tập bảo vệ | |

Mốc gấp nhất là tuần 1: slide tiến độ đã hẹn xong danh mục đơn tuyển dụng trước 12/09.

---

## 7. Về phần đo kiểm

Giai đoạn này chưa đưa số liệu vào báo cáo, vì các phần trọng tâm chưa hoàn thành, đo bây giờ sẽ
phải đo lại và số liệu thay đổi làm giảm độ tin cậy.

Khi các phần đã chạy đủ, đo kiểm tập trung vào ba câu hỏi đúng/sai kiểm được bằng tay:

1. Hệ thống có trả lời khi không đủ căn cứ không?
2. Bộ điều kiện bắt buộc có bỏ sót hoặc loại nhầm đơn hàng nào không?
3. Thông tin rút ra từ CV có đúng với bản gốc không?

---

## 8. Việc cần bạn quyết hoặc cung cấp

| # | Việc | Khi nào cần |
|---|---|---|
| 1 | Điền đơn hàng thật vào file Excel chủ trong `Tailieu/DonHang/` | Trong tuần 1–2. Trước đó dùng 19 đơn mẫu |
| 2 | Duyệt bản đề xuất vòng đời trạng thái hồ sơ | Trước tuần 4 |
| 3 | Gửi tài liệu đặc tả cho bên widget/RAG | Cuối tuần 1 |
| 4 | Cung cấp vài CV mẫu thật (đã che thông tin cá nhân) để kiểm thử phần đọc hồ sơ | Đầu tuần 2 |
| 5 | Xác nhận nội dung các trang giới thiệu, điều kiện, chi phí, quy trình trên website | Trước tuần 6 |
