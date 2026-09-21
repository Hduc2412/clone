# 14 — Nghiệp vụ và giá trị hệ thống

> Tài liệu viết cho **người ngoài ngành đọc**: không code, không thuật toán, không số liệu.
> Trả lời đúng ba câu: *Vấn đề là gì? Hệ thống làm gì? Ai được lợi và lợi ở đâu?*

---

## 1. Câu chuyện có thật của một ứng viên

**Lan, 23 tuổi, tốt nghiệp Cao đẳng Điều dưỡng, vừa thi được chứng chỉ tiếng Nhật N4.**

Mười giờ rưỡi tối, Lan vào website công ty phái cử, gửi file CV và nhắn:

> *"Em muốn làm ở viện dưỡng lão khu vực Tokyo vì có người quen ở đó. Tổng chi phí hết bao nhiêu và có đơn nào bay sớm không ạ?"*

### Hiện nay chuyện gì xảy ra

| Thời điểm | Diễn biến |
|---|---|
| Tối | Hết giờ làm. Tin nhắn nằm im. |
| Sáng hôm sau | Nhân viên mở máy, đọc CV từng trang, nhắn hỏi lại bằng cấp và chứng chỉ. |
| Trong ngày | Mở file đơn hàng, dò tìm xem cơ sở nào ở Tokyo nhận trình độ N4. |
| Kết quả | Mất khá nhiều thời gian cho một người. Trong lúc đó Lan có thể đã nhắn cho trung tâm khác và nhận được trả lời trước. |

### Bốn điểm nghẽn

1. **Câu hỏi lặp đi lặp lại.** Phần lớn câu hỏi chỉ xoay quanh vài nhóm cố định: chi phí, điều kiện, quy trình, hồ sơ, đơn hàng, lương. Nhân viên trả lời lại từ đầu mỗi lần.
2. **Ngoài giờ là khoảng trống.** Đúng lúc ứng viên rảnh để hỏi thì không ai trực.
3. **Đọc hồ sơ thủ công.** Mỗi CV một kiểu trình bày, phải đọc và ghi lại bằng tay.
4. **Dò đơn hàng bằng mắt.** Danh sách đơn nằm trong file rời, đối chiếu điều kiện thủ công nên dễ sót và dễ nhầm.

---

## 2. Hệ thống làm gì

Hệ thống đóng vai một **trợ lý sơ tuyển trực đêm**. Nó không thay nhân viên, nó dọn sẵn việc cho nhân viên.

### 2.1. Với ứng viên — trả lời ngay trong đêm

- Đọc câu hỏi và trả lời dựa trên **tài liệu chính thức của công ty**, không nói theo cảm tính.
- Đọc file CV ứng viên gửi, tóm lại thành một thẻ thông tin gọn gàng và **hỏi lại để xác nhận** cho chắc.
- Đối chiếu hồ sơ với các đơn hàng đang tuyển, giới thiệu vài đơn phù hợp nhất và **nói rõ vì sao**.
- Mời ứng viên chọn khung giờ để nhân viên gọi lại.
- Khi không đủ căn cứ để trả lời, nói thẳng là chưa có thông tin và mời gặp nhân viên.

### 2.2. Với nhân viên — sáng ra là có việc sẵn

Nhân viên vào ca, mở **hàng đợi hồ sơ** trên màn hình quản lý, nhận một hồ sơ về mình rồi thấy ngay một **Phiếu tóm tắt tư vấn**:

```text
PHIẾU TÓM TẮT TƯ VẤN
  Ứng viên     : Lan · 23 tuổi
  Bằng cấp     : Cao đẳng Điều dưỡng
  Tiếng Nhật   : N4
  Nguyện vọng  : viện dưỡng lão · khu vực Tokyo · có người quen ở đó
  Điểm mạnh    : đúng chuyên ngành, đúng khu vực đang có đơn
  Còn thiếu    : chưa có kinh nghiệm chăm sóc người cao tuổi
  Đã giới thiệu: các đơn khu vực Tokyo, kèm lý do từng đơn
  Đơn đã chọn  : đơn ứng viên tự chọn và đã xác nhận
  Đã hỏi về    : chi phí, thời gian bay
  Hẹn gọi lại  : sáng thứ Ba
```

Nhân viên **không phải đọc lại cuộc hội thoại dài**. Chỉ cần nhấc máy và gọi đúng giờ.

### 2.3. Với quản lý — nhìn được toàn cảnh

- Biết có bao nhiêu khách mới, ai đang chờ gọi, ai đã gọi rồi.
- Cập nhật chính sách và danh mục đơn hàng ở một chỗ, website và phần tư vấn dùng chung.
- Xem lại hệ thống đã giới thiệu gì cho ai và vì sao — để kiểm soát chất lượng tư vấn.
- Theo dõi khối lượng công việc và hiệu suất từng nhân viên; điểm được lưu **theo từng
  sự kiện** kèm lý do, nên luôn truy ngược được vì sao điểm thay đổi.
- Biết ai đã thao tác gì trên hệ thống.

---

## 3. Luồng đi của một ứng viên

```text
   ỨNG VIÊN                    HỆ THỐNG                       NHÂN VIÊN
      │                            │                              │
      │  nhắn tin + gửi CV         │                              │
      ├───────────────────────────►│                              │
      │                            │ đọc CV, lập hồ sơ            │
      │  thẻ hồ sơ để xác nhận     │                              │
      │◄───────────────────────────┤                              │
      │  xác nhận / sửa lại        │                              │
      ├───────────────────────────►│                              │
      │                            │ đối chiếu danh mục đơn hàng  │
      │  đơn phù hợp + lý do       │                              │
      │◄───────────────────────────┤                              │
      │  hỏi thêm về chi phí       │                              │
      ├───────────────────────────►│ tra tài liệu chính thức      │
      │  trả lời kèm nguồn         │                              │
      │◄───────────────────────────┤                              │
      │  chọn đơn muốn đăng ký     │                              │
      ├───────────────────────────►│                              │
      │  câu hỏi xác nhận rõ ràng  │                              │
      │◄───────────────────────────┤                              │
      │  xác nhận + chọn giờ hẹn   │                              │
      ├───────────────────────────►│ tạo đăng ký sơ bộ            │
      │                            │ tạo Phiếu tóm tắt tư vấn     │
      │                            ├─────────────────────────────►│
      │                            │                    hàng đợi hồ sơ
      │                            │                              │ nhận xử lý,
      │                            │                              │ gọi và chốt
      │◄──────────────────────────────────────────────────────────┤
```

**Chốt chặn quan trọng:** hệ thống giới thiệu nhiều đơn kèm lý do, nhưng **chỉ ứng viên
mới chọn đơn muốn đăng ký**. Chatbot phải hỏi lại bằng một câu xác nhận rõ ràng trước
khi tạo hồ sơ. Hệ thống **không tạo đăng ký từ suy đoán của mình**.

Điểm đáng chú ý: **ứng viên không phải chờ đến sáng hôm sau**, còn nhân viên **không phải bắt đầu từ con số không**.

---

## 4. Ba tình huống điển hình

| Ứng viên hỏi gì | Hệ thống làm gì | Kết quả |
|---|---|---|
| **Hỏi thông tin thuần túy** — "Điều dưỡng ở Nhật lương khoảng bao nhiêu?" | Tra tài liệu chính thức, trả lời kèm nguồn | Ứng viên được giải đáp ngay, không cần nhân viên |
| **Gửi CV tìm việc** — "Em có N4, muốn làm ở Tokyo" | Đọc CV, lập hồ sơ, đối chiếu đơn hàng, giới thiệu kèm lý do, mời đặt lịch | Sinh ra một khách tiềm năng kèm phiếu tóm tắt |
| **Hỏi ngoài phạm vi** — câu hỏi chưa có trong tài liệu, hoặc yêu cầu gặp người thật | Nói rõ chưa có thông tin, chuyển sang đặt lịch gặp nhân viên | Không trả lời bừa; vẫn giữ được khách |

Ba tình huống này phủ hết các nhánh: **trả lời được**, **thu được khách**, và **phải chuyển cho người thật**.

---

## 5. Nguyên tắc làm nên độ tin cậy

Đây là phần trả lời câu hỏi *"sao không dùng thẳng một trợ lý AI có sẵn cho nhanh?"*

| Nguyên tắc | Nghĩa là gì |
|---|---|
| **Chỉ nói điều có trong tài liệu công ty** | Hệ thống không trả lời theo hiểu biết chung chung. Không tìm được căn cứ thì nói là chưa có thông tin. |
| **Điều kiện đơn hàng do luật quyết, không do AI đoán** | Yêu cầu trình độ tiếng, bằng cấp, độ tuổi là điều kiện cứng, được đối chiếu bằng quy tắc rõ ràng. Cùng một hồ sơ luôn cho cùng một kết quả. |
| **Mọi giới thiệu đều giải thích được** | Từng tiêu chí đạt hay không đạt đều ghi lại. Mở ra xem được bất cứ lúc nào. |
| **Không suy diễn về con người** | Hệ thống ghi lại điều có trên giấy tờ, không nhận xét tính cách hay thái độ ứng viên. |
| **Người quyết định cuối là nhân viên** | Hệ thống sơ tuyển và đề xuất. Nhận hay loại là quyền của nhân viên. |
| **Chatbot không chạm vào dữ liệu nội bộ** | Phần công khai và phần quản trị tách hẳn nhau. |

---

## 6. Hệ thống mang lại gì

### Cho ứng viên
- Được trả lời ngay, kể cả nửa đêm.
- Biết mình hợp với đơn nào và vì sao, thay vì nghe một câu chung chung.
- Không phải kể lại thông tin của mình nhiều lần.

### Cho nhân viên tư vấn
- Không phải trả lời lại những câu hỏi giống nhau mỗi ngày.
- Nhận được hồ sơ đã gọn gàng thay vì một cuộc hội thoại dài.
- Biết gọi cho ai trước, gọi lúc nào.

### Cho doanh nghiệp
- Không mất khách chỉ vì trả lời chậm.
- Thông tin tư vấn thống nhất, không mỗi người nói một kiểu.
- Toàn bộ quá trình tư vấn được lưu lại và xem lại được.
- Chính sách và đơn hàng cập nhật một chỗ, áp dụng cho toàn hệ thống.

---

## 7. Điều hệ thống không hứa

Nói rõ để tránh kỳ vọng sai:

- Không cam kết ứng viên sẽ trúng tuyển.
- Không thay thế buổi tư vấn trực tiếp với nhân viên.
- Không đánh giá con người, chỉ đối chiếu điều kiện trên giấy tờ.
- Không thay thế hợp đồng hay hồ sơ pháp lý chính thức.
