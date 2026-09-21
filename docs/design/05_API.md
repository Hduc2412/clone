# 05 — Đặc tả REST API

Base URL: `/api/v1`. Toàn bộ response lỗi theo định dạng thống nhất:

```json
{ "error": { "code": "RAG_UNAVAILABLE", "message": "...", "request_id": "..." } }
```

Quy ước: `PUBLIC` = không cần token; `AUTH` = cần JWT; role ghi trong ngoặc.

---

## 1. Authentication — `/api/v1/auth`

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| POST | `/auth/login` | PUBLIC | Đăng nhập, trả access token |
| POST | `/auth/logout` | AUTH | Hủy phiên |
| GET | `/auth/me` | AUTH | Thông tin người dùng hiện tại |
| POST | `/auth/change-password` | AUTH | Đổi mật khẩu |

**POST /auth/login**
```jsonc
// Request
{ "email": "admin@company.vn", "password": "..." }
// Response 200
{ "access_token": "eyJ...", "token_type": "bearer", "expires_in": 28800,
  "user": { "id": "...", "name": "...", "email": "...", "role": "admin" } }
// 401: { "error": { "code": "INVALID_CREDENTIALS", ... } }
```
Rate limit: 5 lần/phút/IP. Sai 5 lần liên tiếp khóa tài khoản 15 phút.

---

## 2. Chat — `/api/v1/chat`

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| POST | `/chat/message` | PUBLIC | Gửi tin nhắn, nhận trả lời AI |
| GET | `/chat/history/{session_id}` | PUBLIC | Lịch sử hội thoại của phiên |
| POST | `/chat/session` | PUBLIC | Khởi tạo phiên mới |
| GET | `/chat/analysis/{session_id}` | PUBLIC | Profile + đề xuất sơ bộ của phiên |

**POST /chat/message**
```jsonc
// Request
{ "session_id": "sess_abc", "message": "Chi phi di Nhat dieu duong bao nhieu?" }
// Response 200
{
  "reply": "Chi phi chuong trinh hien tai gom...",
  "intent": "CHI_PHI",
  "confidence": 0.88,
  "entities": { "full_name": null, "phone": null,
                "japanese_level": null, "desired_location": null },
  "suggested_actions": [
    { "type": "quick_reply", "label": "Dieu kien tham gia", "payload": "DIEU_KIEN" },
    { "type": "upload_cv",   "label": "Gui CV de duoc tu van ky hon" }
  ],
  "sources": [ { "title": "Bang chi phi 2026", "section": "Tong chi phi", "score": 0.81 } ],
  "is_fallback": false,
  "message_id": "..."
}
```

Ràng buộc: `message` 1–2000 ký tự. Rate limit 20 tin/phút/session.
Khi `is_fallback = true`, `sources` rỗng và hệ thống tự tạo Lead `NEED_CONTACT`.

---

## 3. Documents / CV — `/api/v1/documents`

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| POST | `/documents/upload` | PUBLIC | Upload CV, trả về ngay, xử lý nền |
| GET | `/documents/{id}` | PUBLIC | Trạng thái và tiến trình xử lý |
| GET | `/documents/{id}/profile` | PUBLIC | Candidate Profile sinh từ CV |
| PATCH | `/documents/{id}/profile` | PUBLIC | Ứng viên sửa lại thông tin AI trích sai |
| GET | `/documents` | AUTH (all) | Danh sách CV, lọc theo ứng viên |
| GET | `/documents/{id}/download` | AUTH (all) | Tải file gốc |
| DELETE | `/documents/{id}` | AUTH (admin) | Xóa CV và dữ liệu liên quan |

**POST /documents/upload** — `multipart/form-data`: `file`, `session_id`, `doc_type`.
```jsonc
// Response 202
{ "document_id": "...", "status": "UPLOADED", "progress": 0 }
// 413 nếu > 10MB, 415 nếu sai định dạng
```

**GET /documents/{id}**
```jsonc
{ "document_id": "...", "status": "ANALYZING", "progress": 60,
  "original_filename": "CV.pdf", "error_message": null }
```

---

## 4. Candidates — `/api/v1/candidates`

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| GET | `/candidates` | AUTH (all) | Danh sách, phân trang, tìm kiếm, lọc |
| GET | `/candidates/{id}` | AUTH (all) | Thông tin cơ bản |
| GET | `/candidates/{id}/overview` | AUTH (all) | Hồ sơ 360 độ, gộp 1 request |
| PATCH | `/candidates/{id}` | AUTH (manager, admin) | Sửa thông tin cơ bản |
| GET | `/candidates/{id}/profile` | AUTH (all) | Candidate Profile |
| PATCH | `/candidates/{id}/profile` | AUTH (all) | Nhân viên sửa/bổ sung field |
| POST | `/candidates/{id}/analyze` | AUTH (all) | Chạy lại phân tích AI |
| GET | `/candidates/{id}/timeline` | AUTH (all) | Dòng thời gian sự kiện |
| POST | `/candidates/{id}/notes` | AUTH (all) | Thêm ghi chú |

Query của `GET /candidates`: `page`, `page_size` (≤100), `q` (tên/SĐT),
`stage`, `assigned_to`, `has_cv`, `japanese_level`, `sort`.

**GET /candidates/{id}/overview** trả về:
```jsonc
{
  "candidate": { ... },
  "profile": { ... },
  "consultation_profile": { ... },
  "documents": [ ... ],
  "recommendations": [ ... ],
  "leads": [ ... ],
  "appointments": [ ... ],
  "summary": { ... },
  "sessions": [ { "session_id": "...", "message_count": 14, "started_at": "..." } ]
}
```
Consultant chỉ nhận được ứng viên có `assigned_to` là chính mình, ngược lại 403.

---

## 5. Analysis & Matching — `/api/v1/analysis`

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| POST | `/analysis/candidate-profile` | AUTH (all) | Sinh Candidate Profile từ CV + chat |
| POST | `/analysis/consultation-profile` | AUTH (all) | Sinh Consultation Profile |
| POST | `/analysis/match` | AUTH (all) | Matching với đơn hàng đang mở |
| POST | `/analysis/summary` | AUTH (all) | Sinh Phiếu tổng hợp tư vấn |

**POST /analysis/match**
```jsonc
// Request
{ "candidate_id": "...", "top_k": 3, "include_closed": false }
// Response
{ "candidate_id": "...", "matched_at": "...",
  "results": [
    { "job_order_id": "...", "order_code": "DH-2026-018",
      "title": "Dieu duong vien duong lao Tokyo",
      "score": 0.87, "level": "CAO",
      "breakdown": { "industry": 1.0, "japanese": 1.0, "experience": 0.8,
                     "education": 1.0, "location": 1.0, "age": 1.0 },
      "matched_reasons": ["..."], "gaps": ["..."],
      "explanation": "..." }
  ] }
```
Nếu Candidate Profile chưa có → 409 `PROFILE_NOT_READY`.

---

## 6. Recommendations — `/api/v1/recommendations`

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| GET | `/recommendations` | AUTH (all) | Danh sách, lọc theo ứng viên/đơn hàng/trạng thái |
| PATCH | `/recommendations/{id}` | AUTH (all) | Duyệt hoặc bác bỏ, kèm `review_note` |

---

## 7. Job Orders — `/api/v1/job-orders`

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| GET | `/job-orders` | PUBLIC (chỉ `OPEN`) / AUTH (đầy đủ) | Danh sách đơn hàng |
| GET | `/job-orders/{id}` | PUBLIC / AUTH | Chi tiết |
| POST | `/job-orders` | AUTH (manager, admin) | Tạo mới |
| PUT | `/job-orders/{id}` | AUTH (manager, admin) | Cập nhật |
| PATCH | `/job-orders/{id}/status` | AUTH (manager, admin) | Đổi trạng thái |
| DELETE | `/job-orders/{id}` | AUTH (admin) | Xóa (chỉ khi `DRAFT`) |

Endpoint public lọc bỏ các trường nội bộ (`created_by`, phí đối tác).

---

## 8. Leads — `/api/v1/leads`

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| POST | `/leads/capture` | PUBLIC | Tạo/cập nhật Lead từ chat hoặc form |
| GET | `/leads` | AUTH (all) | Danh sách, lọc theo `status`, `assigned_to`, khoảng ngày |
| GET | `/leads/{id}` | AUTH (all) | Chi tiết |
| PATCH | `/leads/{id}/status` | AUTH (all) | Đổi trạng thái, bắt buộc `reason` khi lùi trạng thái |
| PATCH | `/leads/{id}/assign` | AUTH (manager, admin) | Phân công consultant |
| POST | `/leads/{id}/notes` | AUTH (all) | Ghi chú kết quả liên hệ |

**POST /leads/capture**
```jsonc
// Request
{ "session_id": "sess_abc", "full_name": "Nguyen Van A", "phone": "0912345678",
  "japanese_level": "N4", "desired_location": "Tokyo",
  "source": "chat_widget", "trigger_reason": "user_requested_consultant" }
// Response 201
{ "lead_id": "...", "lead_code": "LEAD-20260903-0007",
  "candidate_id": "...", "status": "NEED_CONTACT", "is_new_candidate": false }
```
Idempotent theo `(session_id, phone)`: gọi lại chỉ cập nhật, không tạo bản ghi trùng.

---

## 9. Appointments — `/api/v1/appointments`

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| GET | `/appointments/slots` | PUBLIC | Khung giờ còn trống theo ngày |
| POST | `/appointments` | PUBLIC | Đặt lịch |
| GET | `/appointments` | AUTH (all) | Danh sách, lọc ngày/trạng thái/nhân viên |
| PATCH | `/appointments/{id}/status` | AUTH (all) | Xác nhận, hoàn thành, hủy, không liên hệ được |
| PATCH | `/appointments/{id}/reschedule` | AUTH (all) | Đổi lịch, lưu lịch sử |
| PATCH | `/appointments/{id}/assign` | AUTH (manager, admin) | Phân công |

Ràng buộc: T2–T7, `08:00–11:30` và `13:30–17:00`; chặn trùng bằng unique index
`booking_key`; đặt lịch cùng khung giờ trả 409 `SLOT_TAKEN`.

---

## 10. Knowledge Base — `/api/v1/knowledge`

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| POST | `/knowledge/upload` | AUTH (admin) | Upload PDF/DOCX, xử lý nền |
| GET | `/knowledge/documents` | AUTH (all) | Danh sách tài liệu + trạng thái vector |
| GET | `/knowledge/documents/{id}` | AUTH (all) | Chi tiết, tiến trình |
| PATCH | `/knowledge/documents/{id}` | AUTH (admin) | Sửa metadata (topic, tiêu đề) |
| POST | `/knowledge/documents/{id}/reindex` | AUTH (admin) | Vector hóa lại |
| DELETE | `/knowledge/documents/{id}` | AUTH (admin) | Xóa tài liệu và point Qdrant |
| GET | `/knowledge/faq` | AUTH (all) | Danh sách FAQ |
| POST | `/knowledge/faq` | AUTH (admin) | Thêm FAQ |
| PUT | `/knowledge/faq/{id}` | AUTH (admin) | Sửa FAQ |
| DELETE | `/knowledge/faq/{id}` | AUTH (admin) | Xóa FAQ |
| POST | `/knowledge/search` | AUTH (admin) | Test truy vấn RAG, xem chunk và score |

`POST /knowledge/search` là công cụ debug quan trọng: trả về đúng những chunk
retriever lấy được kèm score, giúp chỉnh ngưỡng mà không phải đọc log.

---

## 11. Analytics — `/api/v1/analytics`

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| GET | `/analytics/overview` | AUTH (manager, admin) | Số liệu tổng quan |
| GET | `/analytics/intents` | AUTH (manager, admin) | Phân bổ intent theo ngày |
| GET | `/analytics/funnel` | AUTH (manager, admin) | Phễu chuyển đổi |
| GET | `/analytics/consultants` | AUTH (manager, admin) | Hiệu suất nhân viên |

**GET /analytics/overview?from=&to=**
```jsonc
{
  "total_sessions": 1240, "total_messages": 8931,
  "total_candidates": 312, "total_leads": 198,
  "total_cv_uploaded": 87, "total_appointments": 64,
  "fallback_rate": 0.11, "avg_confidence": 0.82,
  "intent_distribution": { "CHI_PHI": 320, "DIEU_KIEN": 210, "...": 0 },
  "leads_by_status": { "NEW": 40, "NEED_CONTACT": 52, "CONTACTED": 96, "URGENT": 10 },
  "daily": [ { "date": "2026-09-01", "sessions": 45, "leads": 8, "cv": 3 } ]
}
```

**GET /analytics/funnel**
```
Phiên chat → Có SĐT → Nộp CV → Có đề xuất → Đặt lịch → Đã tư vấn
```

---

## 12. Users & Audit

| Method | Path | Quyền |
|---|---|---|
| GET / POST | `/users` | AUTH (admin) |
| PATCH | `/users/{id}` | AUTH (admin) |
| PATCH | `/users/{id}/status` | AUTH (admin) |
| GET | `/audit-logs` | AUTH (admin) |
| GET | `/notifications` | AUTH (all) |
| PATCH | `/notifications/{id}/read` | AUTH (all) |

---

## 13. Mã lỗi chuẩn

| Code | HTTP | Ý nghĩa |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Dữ liệu vào sai schema |
| `INVALID_CREDENTIALS` | 401 | Sai email/mật khẩu |
| `FORBIDDEN` | 403 | Không đủ quyền |
| `NOT_FOUND` | 404 | Không tìm thấy tài nguyên |
| `SLOT_TAKEN` | 409 | Khung giờ đã kín |
| `PROFILE_NOT_READY` | 409 | Chưa có Candidate Profile để matching |
| `DUPLICATE_PHONE` | 409 | SĐT đã tồn tại |
| `FILE_TOO_LARGE` | 413 | File > 10MB |
| `UNSUPPORTED_MEDIA` | 415 | Sai định dạng file |
| `RATE_LIMITED` | 429 | Vượt giới hạn |
| `LLM_UNAVAILABLE` | 503 | Gemini lỗi sau 3 lần retry |
| `RAG_UNAVAILABLE` | 503 | Qdrant không phản hồi |

Riêng `/chat/message`: **không bao giờ trả 5xx**. Khi LLM hoặc Qdrant chết,
endpoint vẫn trả 200 với `is_fallback = true` và câu trả lời dự phòng, đồng thời
ghi log ERROR. Lý do: widget phía ứng viên không được vỡ trải nghiệm.
