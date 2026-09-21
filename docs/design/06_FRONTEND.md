# 06 — Thiết kế Frontend

Hai ứng dụng Next.js 14 độc lập, dùng chung ngôn ngữ thiết kế:

| App | Port dev | Người dùng | Xác thực |
|---|---|---|---|
| `frontend/` | 3100 | Ứng viên | Không |
| `admin-frontend/` | 3101 | Nhân viên nội bộ | JWT, middleware chặn route |

Stack: Next.js 14 App Router, TypeScript, Tailwind CSS, Lucide Icons, Axios,
Recharts (biểu đồ), `react-markdown` (render trả lời AI).

---

## 1. Website ứng viên — Sitemap

```
/                       Landing page
├── /chuong-trinh       Giới thiệu chương trình điều dưỡng
├── /dieu-kien          Điều kiện tham gia
├── /chi-phi            Chi phí và hỗ trợ tài chính
├── /quy-trinh          Quy trình 7 bước
├── /don-hang           Danh sách đơn hàng đang tuyển
│   └── /don-hang/[code]  Chi tiết đơn hàng
├── /cau-hoi-thuong-gap FAQ
├── /dang-ky            Form đăng ký đầy đủ
└── /lien-he            Liên hệ
```

Chat Widget hiện trên **mọi trang**, cố định góc phải dưới.

### 1.1 Landing page — bố cục

| Section | Nội dung | Ghi chú |
|---|---|---|
| Hero | Tiêu đề, phụ đề, CTA "Tư vấn miễn phí" + "Gửi CV" | CTA mở thẳng widget |
| Vì sao chọn Nhật | 4 thẻ số liệu (lương, cơ hội, đào tạo, định cư) | |
| Điều kiện | Bảng checklist | Nội dung lấy từ CMS/KB |
| Chi phí | Bảng minh bạch các khoản | |
| Quy trình | Timeline 7 bước | |
| Đơn hàng tiêu biểu | 3 thẻ đơn hàng | `GET /job-orders?status=OPEN&limit=3` |
| Câu chuyện thực tế | Testimonial | |
| Form đăng ký | Họ tên, SĐT, trình độ tiếng Nhật, địa điểm | `POST /leads/capture` |
| Footer | Thông tin công ty | |

Yêu cầu: responsive từ 360px, điểm Lighthouse Performance ≥ 85,
ảnh dùng `next/image`, không chặn render bằng script bên thứ ba.

### 1.2 Chat Widget — đặc tả

```
┌──────────────────────────────┐
│ ● Tư vấn viên AI        — ✕ │  Header: trạng thái, thu nhỏ, đóng
├──────────────────────────────┤
│                              │
│  [bot] Chào anh/chị, em có   │  Bubble bot: nền xám, Markdown
│        thể giúp gì ạ?        │
│                              │
│        Chi phí bao nhiêu? [u]│  Bubble user: nền xanh, canh phải
│                              │
│  [bot] Chi phí gồm...        │
│    ┌────────────────────┐    │
│    │ Nguồn: Bảng chi phí│    │  Chip nguồn, bấm mở tài liệu
│    └────────────────────┘    │
│                              │
│  ( Điều kiện ) ( Quy trình ) │  Quick Reply
│                              │
│  ┌────────────────────────┐  │
│  │ Gửi CV để được tư vấn  │  │  Card upload CV
│  │ [ Chọn file ]          │  │
│  └────────────────────────┘  │
├──────────────────────────────┤
│ 📎 [Nhập tin nhắn...]    ➤  │  Kẹp giấy = upload CV
└──────────────────────────────┘
```

**Các loại tin nhắn cần render**

| Loại | Khi nào | Giao diện |
|---|---|---|
| `text` | Mặc định | Markdown: in đậm, danh sách, xuống dòng |
| `quick_replies` | AI gợi ý bước tiếp | Hàng nút bo tròn |
| `lead_form` | Thiếu SĐT hoặc handoff | Card 2 ô: tên + SĐT, nút Gửi |
| `cv_upload` | AI mời gửi CV | Card có nút chọn file |
| `cv_progress` | Đang xử lý CV | Thanh tiến trình + nhãn trạng thái |
| `profile_card` | CV phân tích xong | Thẻ tóm tắt hồ sơ, có nút Sửa |
| `job_cards` | Có đề xuất đơn hàng | Carousel tối đa 3 thẻ, nhãn mức phù hợp |
| `booking_form` | Intent DANG_KY | Chọn ngày, chọn khung giờ, xác nhận |
| `error` | LLM/Qdrant chết | Bubble cảnh báo nhẹ, nút "Thử lại" |

**Quản lý state**: hook `useChat` giữ `session_id` trong `localStorage`
(khóa `xkld_session_id`), TTL 7 ngày. Mất mạng → xếp hàng tin nhắn, thử lại
tối đa 2 lần rồi hiện nút "Gửi lại".

**Trạng thái chờ**: hiện typing indicator sau 300ms. Nếu quá 10s hiện thêm dòng
"Em đang tra cứu tài liệu, anh/chị đợi chút ạ" để tránh cảm giác treo.

**Khả năng tiếp cận**: điều hướng bằng bàn phím, `aria-live="polite"` cho vùng
tin nhắn, tương phản chữ đạt WCAG AA.

---

## 2. Admin Dashboard — Sitemap

```
/login
/admin
├── /admin                    Dashboard tổng quan
├── /admin/candidates         Danh sách ứng viên
│   └── /admin/candidates/[id]  Hồ sơ 360 độ
├── /admin/leads              Quản lý Lead
│   └── /admin/leads/[code]
├── /admin/conversations      Lịch sử hội thoại
│   └── /admin/conversations/[sessionId]
├── /admin/documents          Quản lý CV
├── /admin/recommendations    Đề xuất chờ duyệt
├── /admin/job-orders         Quản lý đơn hàng
│   └── /admin/job-orders/[id]
├── /admin/appointments       Lịch hẹn
├── /admin/knowledge          Knowledge Base + FAQ
├── /admin/analytics          Biểu đồ
├── /admin/users              Người dùng nội bộ (admin)
└── /admin/audit-logs         Nhật ký (admin)
```

Sidebar ẩn mục không thuộc quyền của vai trò; middleware chặn ở cả tầng route.

### 2.1 Dashboard tổng quan

| Khu vực | Nội dung |
|---|---|
| Hàng thẻ số liệu | Ứng viên mới hôm nay, Lead cần liên hệ, CV chờ xử lý, Lịch hẹn hôm nay |
| Cảnh báo | Lead `URGENT` chưa xử lý > 2 giờ, tài liệu KB `FAILED` |
| Biểu đồ đường | Lưu lượng chat 30 ngày |
| Biểu đồ tròn | Phân bổ intent |
| Bảng | 10 hoạt động gần nhất |

### 2.2 Danh sách ứng viên

- Bộ lọc: từ khóa (tên/SĐT), giai đoạn, người phụ trách, có CV hay chưa,
  trình độ tiếng Nhật, khoảng ngày.
- Cột: Mã, Họ tên, SĐT (che 3 số giữa với consultant), Tiếng Nhật, Có CV,
  Mức match cao nhất, Giai đoạn, Người phụ trách, Cập nhật.
- Thao tác hàng loạt: phân công, đổi giai đoạn.
- Phân trang phía server, mặc định 20 dòng.

### 2.3 Hồ sơ ứng viên 360 độ — màn hình quan trọng nhất

```
┌───────────────────────────────────────────────────────────────┐
│ Nguyễn Văn A · UV-20260903-0001 · 0912****78                  │
│ N4 · Cao đẳng Điều dưỡng · 2 năm KN · Phụ trách: Trần B       │
│ [Phân công] [Đổi trạng thái] [Tạo lại phân tích] [Đặt lịch]  │
├───────────────────────────────────────────────────────────────┤
│ Tổng quan │ Hồ sơ AI │ Nhu cầu │ CV │ Đề xuất │ Hội thoại │  │
│                                              Lịch hẹn │ Ghi chú│
└───────────────────────────────────────────────────────────────┘
```

| Tab | Nội dung |
|---|---|
| **Tổng quan** | Phiếu tổng hợp tư vấn do AI sinh + dòng thời gian sự kiện |
| **Hồ sơ AI** | Bảng field: giá trị, nhãn nguồn, độ tin cậy, nút xem `evidence`, nút sửa |
| **Nhu cầu** | Consultation Profile, các câu chat làm bằng chứng |
| **CV** | Danh sách file, xem trước, tải, xem text đã trích |
| **Đề xuất** | Thẻ đơn hàng kèm điểm thành phần, lý do, khoảng thiếu; nút Duyệt/Bác bỏ |
| **Hội thoại** | Toàn bộ tin nhắn theo phiên, hiện intent và confidence từng câu |
| **Lịch hẹn** | Danh sách, nút đổi lịch/ghi kết quả |
| **Ghi chú** | Ghi chú nội bộ, hiện người ghi và thời điểm |

**Quy tắc hiển thị bắt buộc**: mọi giá trị do AI sinh phải có nhãn nguồn
(`AI` / `Ứng viên xác nhận` / `Nhân viên nhập`) và tooltip chứa `evidence`.
Không hiển thị giá trị AI như thể là dữ liệu đã xác minh.

### 2.4 Quản lý Lead

- Hai chế độ xem: bảng và Kanban theo 4 trạng thái.
- Ưu tiên hiển thị: `URGENT` viền đỏ, `NEED_CONTACT` viền cam.
- Panel bên phải khi chọn Lead: phiếu tổng hợp, lịch sử trạng thái, ô ghi chú nhanh.
- Đổi trạng thái lùi (từ `CONTACTED` về trạng thái khác) bắt buộc nhập lý do.

### 2.5 Knowledge Base

- Vùng kéo thả upload, hiện thanh tiến trình theo `status` từ API.
- Bảng tài liệu: Tiêu đề, Loại, Topic, Số chunk, Trạng thái vector, Cập nhật.
- Trạng thái `FAILED` hiện nút "Thử lại" và tooltip lỗi.
- Tab FAQ: bảng CRUD, đánh dấu FAQ chưa đồng bộ vector.
- Hộp "Thử truy vấn": nhập câu hỏi, hiện các chunk trả về kèm score
  (dùng `POST /knowledge/search`) — để tinh chỉnh ngưỡng mà không cần đọc log.

### 2.6 Analytics

| Biểu đồ | Loại | Nguồn |
|---|---|---|
| Lưu lượng chat theo ngày | Đường | `/analytics/overview` |
| Phân bổ intent | Tròn | `/analytics/intents` |
| Lead theo trạng thái | Cột chồng | `/analytics/overview` |
| Phễu chuyển đổi | Funnel | `/analytics/funnel` |
| Tỷ lệ fallback theo ngày | Đường | `/analytics/overview` |
| Hiệu suất consultant | Cột ngang | `/analytics/consultants` |

Bộ lọc khoảng ngày dùng chung cho toàn trang; có nút xuất CSV.

---

## 3. Quy ước kỹ thuật frontend

**Cấu trúc thư mục** (áp dụng cho cả hai app):
```
app/            route và page
components/     component tái sử dụng
  ui/           nút, input, badge, modal
  chat/         thành phần widget
  admin/        thành phần dashboard
hooks/          useChat, useAuth, useCandidates
lib/
  api.ts        Axios instance, interceptor gắn token và bắt 401
  types.ts      type dùng chung, khớp với Pydantic schema
  format.ts     định dạng ngày, SĐT, tiền tệ
```

- Toàn bộ gọi API đi qua `lib/api.ts`; không gọi `fetch` rải rác trong component.
- Mỗi màn hình danh sách phải xử lý đủ 4 trạng thái: loading (skeleton),
  rỗng (hướng dẫn), lỗi (nút thử lại), có dữ liệu.
- Type ở `lib/types.ts` phải khớp Pydantic response model; khi API đổi thì sửa
  cả hai nơi trong cùng một commit.
- Không lưu JWT vào `localStorage` ở admin app — dùng httpOnly cookie
  (`auth_cookie_name` đã có sẵn trong config backend).
