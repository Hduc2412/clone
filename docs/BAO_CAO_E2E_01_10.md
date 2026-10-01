# Chạy thử toàn hành trình trên giao diện — 01/10/2026

Chạy bằng trình duyệt thật, năm dịch vụ cùng lúc (MongoDB 27017, Qdrant 6333,
backend 8020, website 3100, hệ quản trị 3101). Không mô phỏng, không mock: mỗi
bước dưới đây là một lần bấm chuột và một bản ghi thật trong database.

Hồ sơ dùng để chạy: `backend/tests/fixtures/cv/07_tran_thi_thu_ha.pdf` — ca mẫu
có đáp án, chọn vì nó khớp đơn `DH-0001` (Tokyo, N4, Cao đẳng).

Mã sinh ra trong lượt chạy này: hồ sơ ứng viên `UV-CAE8F3`, hồ sơ tuyển dụng
`HS-F3F3FA`, tệp CV `CV-7C77FE`, yêu cầu hỗ trợ `HT-CD2DA3`.

---

## 1. Từng chặng, và chặng nào thật sự chạy

| # | Chặng | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Chọn đơn từ danh sách công khai | **Chạy** | 16 đơn công khai; đơn `draft`/tạm dừng/quá hạn không lọt ra |
| 2 | Mở phòng tư vấn theo đơn | **Chạy** | `/tu-van/don/DH-0001`, phiên mới ở trạng thái "chưa có hồ sơ" |
| 3 | Gửi CV | **Chạy** | PDF → `storage/cv/2026/10/CV-7C77FE.pdf`, gọi Gemini một lần |
| 4 | Trích xuất thành hồ sơ | **Chạy** | 8 trường, mỗi trường có `source: cv` + trích dẫn nguyên văn |
| 5 | Sửa và xác nhận hồ sơ | **Chạy** | Biểu mẫu `/tu-van` điền sẵn từ CV; bấm gửi là xác nhận |
| 6 | Đối chiếu với đơn | **Chạy** | `DH-0001` 95/100 hạng 1; 11 đơn đủ điều kiện trên 18 đơn đã xét |
| 7 | Hỏi trợ lý tư vấn | **Chạy, suy giảm đúng cách** | Hết hạn mức Gemini → nói "trợ lý đang bận", không bịa (mục 3) |
| 8 | Đổi đơn | **Chạy** | Danh sách xếp hạng cho chọn đơn khác; `DH-0004` 80/100, `DH-0011` 55/100 |
| 9 | Nhánh tư vấn học | **Chạy** (không áp dụng cho ca này) | Có đường "Tư vấn việc học"; ứng viên đã N4 nên không cần lộ trình |
| 10 | Đăng ký đơn | **Chạy** | Có bước xác nhận riêng; sinh `HS-F3F3FA` |
| 11 | Nhân viên nhận phiếu tóm tắt | **Chạy** | Phiếu đủ 7 dòng điều kiện cứng + 4 dòng mềm, mỗi dòng truy được nguồn |
| 12 | Nhận xử lý hồ sơ | **Chạy** | Hồ sơ rời tab "Chưa ai nhận"; sổ điểm +2 và +3 |
| 13 | Cập nhật trạng thái | **Chạy** | `draft → collecting_documents → screening`, mỗi bước chỉ cho chuyển hợp luật |
| 14 | Ghi kết quả sơ tuyển | **Chạy** | `POST /applications/{code}/so-tuyen` — chốt trình độ + chứng cứ + trạng thái trong một lời gọi |
| 15 | Cấp tài khoản cho ứng viên | **Chạy** | Mật khẩu 10 ký tự, không có `0 O 1 l 5 S 2 Z` — đọc qua điện thoại không nhầm |
| 16 | Ứng viên tự theo dõi trạng thái | **Chạy** | Bắt đổi mật khẩu trước, rồi hiện đúng bước nhân viên vừa đặt |
| 17 | **Lịch hẹn** | **Chưa chạy** | Xem mục 2 |

---

## 2. Khoảng trống duy nhất: lịch hẹn

Hành trình trên website **không có đường nào tạo ra một lịch hẹn**. Đây không
phải suy đoán từ việc tìm không thấy, mà kiểm được bằng cách lần ngược:

```
create_appointment
  └── booking/booking_service.py:196
        └── services/chat_service.py:27  (process_booking_message)
```

Đúng một nơi gọi, và nơi ấy là **khung chat** — phần phụ trợ, không phải hành
trình chính. Ba chỗ lẽ ra nối vào thì đều không nối:

- `RegisterRequest` chỉ có `job_order_code` và `confirmed`. Không có khung giờ,
  nên bước đăng ký không sinh lịch hẹn. (Bản thiết kế có ghi "tạo lịch hẹn nếu
  chọn khung giờ" — phần ấy chưa làm.)
- "Xin gặp mặt" vào `support_requests` rồi đóng lại bằng một ghi chú. Không có
  nút nào chuyển nó thành lịch hẹn, dù đây đúng là loại yêu cầu cần một buổi gặp.
- `app/api/appointments.py` có liệt kê, đổi trạng thái, phân công, đổi giờ, xem
  lịch sử — nhưng **không có đường tạo**.

Hệ quả thật: với người chỉ đi theo hành trình mới, màn hình `/admin/appointments`
luôn trống. Chính dòng chữ trên màn hình đó đã thừa nhận: *"Thử thay đổi bộ lọc
hoặc chờ lịch mới từ chatbot."*

Phần ghi kết quả buổi gặp thì **có**, chỉ gắn chỗ khác: nó nằm trên hồ sơ tuyển
dụng (`POST /applications/{code}/so-tuyen`), hiện ra khi hồ sơ ở trạng thái
`screening`. Một lời gọi ghi cả trình độ tiếng Nhật, cách đối chứng
(`ban_goc` / `tra_cuu_truc_tuyen` / `khong_xuat_trinh`), hình thức gặp
(`truc_tiep` / `truc_tuyen`) và trạng thái kế tiếp — nên hai thứ không lệch nhau.

Nói cách khác: **ghi kết quả buổi gặp thì làm được, còn hẹn buổi gặp thì chưa.**

---

## 3. Hết hạn mức Gemini — và vì sao đây là tin tốt

Lượt chạy rơi đúng lúc hạn mức gói miễn phí của engine tư vấn đã cạn
(`limit: 20, model: gemini-3.8-flash`, `RESOURCE_EXHAUSTED`). Model dự phòng
`gemini-3.7-flash` cũng cạn theo.

Hệ thống xử sự đúng như thiết kế, và đây là ca khó dựng lại bằng kiểm thử mock:

- Trả về nguồn `khong_goi_duoc`, không phải một câu trả lời trông có vẻ hợp lý.
- Giao diện nói **"Phần trợ lý tư vấn đang bận"** và mời để lại tin nhắn cho
  nhân viên — không bịa, không im lặng.
- Có thử model dự phòng trước khi bỏ, và ghi rõ trong log là đã chuyển.
- **Mọi chặng nghiệp vụ còn lại vẫn chạy**: đối chiếu, đăng ký, phiếu tóm tắt,
  sổ điểm, trạng thái. Vì điểm số do Python tính, mô hình chỉ diễn đạt.

Đổi lại, nó cho thấy một giới hạn phải nói rõ khi bảo vệ: **20 lượt mỗi ngày
mỗi model**, dùng chung giữa phần đo chất lượng và phần chạy thử. Hết hạn mức
thì phần trợ lý nghỉ, phần còn lại vẫn làm việc.

---

## 4. Lỗi tìm được và đã sửa

### Badge "Lịch hẹn" hiện số thông báo chưa đọc

Mục *Lịch hẹn* ở thanh bên hiện `10`. Bấm vào thì `appointments_total = 0` và
màn hình trống. Nguyên nhân: badge đọc `notifications_unread`.

Hai con số không liên quan gì nhau. Kiểm 11 thông báo đang có: tất cả là
`application` (hồ sơ mới đăng ký) hoặc `support_request` (tin nhắn khách để lại).
Không có cái nào là lịch hẹn.

Loại lỗi này không làm sập gì, không có ngoại lệ nào để bắt, và `npm run build`
không thấy gì sai — cả hai đều là `number`. Chỉ người đọc màn hình mới phát hiện.

**Đã sửa** (`components/admin/AdminShell.tsx`): badge mục Lịch hẹn đọc
`appointments_pending`; badge *Thông báo* ở đầu trang giữ `notifications_unread`
nhưng trỏ về hàng đợi hồ sơ. Ba ca kiểm thử mới trong
`admin-frontend/tests/adminShellBadge.test.cjs`, soi cấu trúc bằng chính bộ phân
tích của TypeScript chứ không tìm chuỗi. Cả 5 đột biến đều bị bắt.

---

## 5. Việc còn dở, chưa sửa

| Việc | Vì sao đáng sửa |
|---|---|
| **Phòng tư vấn theo đơn nhắc xác nhận hồ sơ nhưng không có đường đi tới** | Trang nói "Bạn xác nhận hồ sơ trước khi đăng ký nhé" rồi để đó. Người dùng phải tự mò qua "Xem toàn bộ đơn phù hợp". Một câu nhắc không kèm đường đi là một ngõ cụt. |
| **Câu hỏi gợi ý không đổi theo kết quả** | Hồ sơ đã ĐẠT mà chip vẫn là *"Vì sao em chưa đạt đơn này?"* — mời người dùng hỏi một câu sai tiền đề, rồi bắt trợ lý gỡ. |
| **"5/100 điểm phù hợp" cạnh "đạt các điều kiện bắt buộc"** | Khi chưa khai nguyện vọng nào, điểm mềm gần 0. Hồ sơ đạt đủ bảy điều kiện cứng mà hiện 5/100 thì đọc như "chỉ hợp 5%". Chưa đủ dữ liệu để xếp hạng thì nên nói thế, đừng cho một con số. |
| **Trang đăng ký hứa "theo dõi tại Hồ sơ của tôi" ngay sau khi đăng ký** | Lúc ấy chưa có tài khoản nào: tài khoản do nhân viên cấp sau khi tiếp nhận. Người vừa đăng ký bấm vào chỉ thấy ô đăng nhập. |
| **Biểu mẫu "Nói chuyện với nhân viên" không điền sẵn tên và số điện thoại** | Hồ sơ đã xác nhận có cả hai. Bắt gõ lại là chỗ dễ gõ sai số. |
| **Phòng tư vấn theo đơn không biết hồ sơ đã đăng ký đơn đó** | Vẫn hiện "Đăng ký đơn này" trong khi `/tu-van` đã hiện "Đã đăng ký". |
| **Phiếu tóm tắt gắn nhãn `[ứng viên xác nhận]` cho mọi trường, kể cả trường máy đọc từ CV** | Gửi biểu mẫu đã điền sẵn khiến mọi trường `cv` thành `user_confirmed`. Phiếu mất đúng cái phân biệt mà thiết kế hứa: máy đọc được gì, và người thật kiểm lại cái gì. |
| **`/notifications` không màn hình nào đọc** | API có đủ danh sách và nút đánh dấu đã đọc, nhưng chưa có chỗ dùng. Nên con số thông báo chỉ giảm khi nhân viên mở hồ sơ bằng đường khác. |
| **Không có trang chi tiết một hồ sơ tuyển dụng** | `/admin/applications/{code}` trả 404. Bản thiết kế có mô tả màn hình "hồ sơ tập trung một chỗ"; hiện chỉ có danh sách. |

---

## 6. Hai thứ tưởng là lỗi mà không phải

Ghi lại để lần sau không mất công kiểm lại.

**Hotline và địa chỉ văn phòng vẫn hiện trên trang.** Đúng thiết kế: chúng nằm
trong `frontend/.env.local` — tệp không vào kho mã. Kho mã chỉ có số giả
`0000.000.000` và câu "Liên hệ hotline để biết địa chỉ". Máy này có giá trị thật
nên trang hiện giá trị thật.

**Biểu mẫu `/tu-van` trông như trống sau khi gửi CV.** Không trống: `innerText`
không đọc được giá trị của ô `input`. Đọc đúng thì thấy cả 8 trường đã điền sẵn
từ CV, kèm trích dẫn căn cứ từng trường.

---

## 7. Cách chạy lại

```bash
# 1. Dịch vụ nền
docker compose up -d qdrant            # MongoDB chạy như service của Windows

# 2. Backend
cd backend && ./venv/Scripts/python.exe -m uvicorn main:app --port 8020

# 3. Hai app Next (node không có trên PATH của Git Bash — chạy từ PowerShell)
cd frontend && npm run dev             # 3100
cd admin-frontend && npm run dev       # 3101
```

Phiên tư vấn nằm trong cookie đã ký, `httponly` — JavaScript không xoá được.
Muốn chạy lại từ hồ sơ trắng thì gọi `POST /public/phien/moi`, đúng đường mà nút
"Khai lại từ đầu" trên giao diện dùng.
