# 01 — Phân tích yêu cầu

## 1. Bối cảnh nghiệp vụ

Doanh nghiệp XKLĐ điều dưỡng Nhật Bản hiện xử lý ứng viên thủ công:

| Vấn đề hiện tại | Hệ quả |
|---|---|
| Ứng viên hỏi lặp lại 9 nhóm câu hỏi (chi phí, điều kiện, quy trình...) | Nhân viên tốn thời gian trả lời trùng lặp |
| CV nhận qua Zalo/email, nhập tay vào Excel | Sai sót, mất dữ liệu, không tra cứu được |
| Nhân viên phải đọc toàn bộ lịch sử chat mới nắm được ứng viên | Chậm, bỏ sót thông tin |
| Ghép ứng viên với đơn hàng dựa vào trí nhớ nhân viên | Không nhất quán, bỏ lỡ cơ hội |
| Không đo được tỷ lệ chuyển đổi | Không cải tiến được quy trình |

## 2. Actor

| Actor | Mô tả | Kênh truy cập |
|---|---|---|
| **Ứng viên (Candidate)** | Người quan tâm chương trình, chưa cần tài khoản | Website public + Chat Widget |
| **Consultant** | Nhân viên tư vấn, xử lý ứng viên được giao | Admin Dashboard |
| **Manager** | Quản lý nghiệp vụ, phân công, duyệt đề xuất | Admin Dashboard |
| **Admin** | Quản trị hệ thống, người dùng, Knowledge Base | Admin Dashboard |
| **AI Engine** | Actor hệ thống: phân tích, đề xuất, tóm tắt | Nội bộ |

## 3. Yêu cầu chức năng (FR)

### Nhóm A — Kênh ứng viên

| ID | Yêu cầu | Ưu tiên |
|---|---|---|
| FR-A01 | Website public giới thiệu chương trình: điều kiện, chi phí, quy trình, đơn hàng tiêu biểu | Must |
| FR-A02 | Chat Widget nổi, giữ `session_id` qua nhiều lượt, render Markdown | Must |
| FR-A03 | Chatbot trả lời dựa trên Knowledge Base (RAG), có trích nguồn | Must |
| FR-A04 | Ứng viên upload CV (PDF/DOCX/ảnh, ≤ 10MB) ngay trong khung chat | Must |
| FR-A05 | Quick Reply buttons và Card Form thu số điện thoại nhanh | Must |
| FR-A06 | Ứng viên xem được kết quả phân tích sơ bộ và đơn hàng gợi ý | Should |
| FR-A07 | Ứng viên đặt lịch tư vấn ngay trong chat, xác nhận trước khi tạo | Must |
| FR-A08 | Khi AI không chắc chắn → phản hồi lịch sự + tạo `NEED_CONTACT` | Must |

### Nhóm B — Phân tích AI

| ID | Yêu cầu | Ưu tiên |
|---|---|---|
| FR-B01 | Phân loại ý định 10 nhóm: CHI_PHI, DIEU_KIEN, QUY_TRINH, DON_HANG, HO_SO, VISA, LUONG, DIA_DIEM, TIENG_NHAT, DANG_KY | Must |
| FR-B02 | Trích xuất entity: họ tên, SĐT (regex VN), trình độ tiếng Nhật (N1–N5/chưa học), địa điểm mong muốn | Must |
| FR-B03 | Parse CV (PDF/DOCX/ảnh) thành text, OCR ảnh khi cần | Must |
| FR-B04 | Sinh **Candidate Profile** có cấu trúc từ CV + lịch sử chat | Must |
| FR-B05 | Sinh **Consultation Profile** (nhu cầu, ưu tiên, địa điểm, lý do, trạng thái) từ hội thoại | Must |
| FR-B06 | Mỗi trường trong Profile phải kèm `evidence` (trích dẫn nguồn) và `confidence` | Must |
| FR-B07 | Đánh giá điểm mạnh dựa trên bằng chứng, **không** sinh tính từ cảm tính | Must |
| FR-B08 | Matching Candidate Profile ↔ Job Order, trả về điểm + **lý do bằng ngôn ngữ tự nhiên** | Must |
| FR-B09 | Sinh Phiếu tổng hợp tư vấn (Consultation Summary) cho nhân viên | Should |
| FR-B10 | Retry Gemini khi 429/500/503: 3 lần, delay 2s→5s→10s, timeout 30s | Must |
| FR-B11 | Fallback thân thiện khi Gemini/Qdrant lỗi hoặc timeout | Must |

### Nhóm C — Quản lý nghiệp vụ

| ID | Yêu cầu | Ưu tiên |
|---|---|---|
| FR-C01 | Quản lý Candidate: danh sách, tìm kiếm, lọc, trang chi tiết 360° | Must |
| FR-C02 | Quản lý Lead: 4 trạng thái NEW / NEED_CONTACT / CONTACTED / URGENT | Must |
| FR-C03 | Phân công consultant cho Lead/Appointment | Must |
| FR-C04 | Xem lại toàn bộ lịch sử hội thoại theo session và theo ứng viên | Must |
| FR-C05 | Quản lý tài liệu CV: xem, tải, xóa, xem text đã trích | Must |
| FR-C06 | Xem/duyệt/bác bỏ đề xuất đơn hàng của AI, ghi lý do | Should |
| FR-C07 | Quản lý lịch hẹn: tạo, đổi, hủy, ghi kết quả, chặn trùng | Must |
| FR-C08 | Knowledge Base: upload PDF/DOCX, theo dõi tiến trình vector hóa, CRUD FAQ | Must |
| FR-C09 | Quản lý Job Order (đơn hàng): CRUD, trạng thái tuyển | Must |
| FR-C10 | Analytics: phiên chat, lead, tỷ lệ fallback, phân bổ intent, phễu chuyển đổi | Should |
| FR-C11 | Đăng nhập JWT, RBAC 3 vai trò | Must |
| FR-C12 | Audit log các thao tác quan trọng | Should |

## 4. Yêu cầu phi chức năng (NFR)

| ID | Yêu cầu | Chỉ tiêu đo được |
|---|---|---|
| NFR-01 | Thời gian phản hồi chat | p95 ≤ 6s (bao gồm gọi LLM) |
| NFR-02 | Thời gian phân tích CV | ≤ 30s cho CV ≤ 5 trang, chạy nền, có trạng thái |
| NFR-03 | Truy vấn API quản lý | p95 ≤ 500ms |
| NFR-04 | Độ chính xác intent | ≥ 85% trên tập kiểm thử tự xây (≥ 200 câu) |
| NFR-05 | Ngưỡng RAG | cosine ≥ 0.65, Top-K = 4; dưới ngưỡng → fallback |
| NFR-06 | Bảo mật | Mật khẩu PBKDF2, JWT HS256, không log SĐT đầy đủ |
| NFR-07 | Quyền riêng tư | CV lưu trong volume nội bộ, không public URL; có API xóa dữ liệu ứng viên |
| NFR-08 | Chịu lỗi | External API chết → hệ thống vẫn trả lời fallback, không 500 |
| NFR-09 | Khả năng triển khai | `docker compose up` chạy được toàn bộ stack |
| NFR-10 | Kiểm thử | Pytest phủ service layer; mock toàn bộ external call |
| NFR-11 | Ngôn ngữ | Toàn bộ giao diện và phản hồi AI bằng tiếng Việt |

## 5. Phạm vi (MoSCoW)

**MUST** — Website, Chat Widget, CV Upload, Conversation History, CV Extraction,
Candidate Profile, Need Analysis, Intent/Entity, RAG, AI Recommendation,
Lead Management, Appointment, Admin Dashboard, MongoDB, Qdrant, API, Auth.

**SHOULD** — Human Handoff, Document Management, Matching Score,
AI Consultation Summary, Analytics, Docker, Nginx.

**COULD** — Xuất phiếu tư vấn ra PDF, gửi email thông báo.

**WON'T (giai đoạn này)** — Zalo OA, Messenger, Mobile App, Live Chat realtime,
push notification, scheduler tự động, reranking nâng cao, tự huấn luyện LLM.

## 6. Giả định và ràng buộc

- Không tự huấn luyện mô hình; dùng Gemini 2.5 Flash + `gemini-embedding-001`.
- Giai đoạn đồ án chạy local/Docker trên máy cá nhân, ưu tiên giải pháp miễn phí.
- Dữ liệu Knowledge Base ban đầu crawl từ `xklddieuduong.vn` (32 bài đã có).
- Dữ liệu Job Order do Admin nhập tay (chưa có API đối tác Nhật).
- Giờ đặt lịch: Thứ Hai–Thứ Bảy, `08:00–11:30` và `13:30–17:00`.
- Ứng viên không cần tài khoản; định danh bằng `session_id` + số điện thoại.
