# 10 — Đối chiếu thiết kế với code hiện có

Mục đích: chỉ rõ phần nào **giữ nguyên**, phần nào **sửa**, phần nào **viết mới**,
để không viết lại thứ đã chạy được và không bỏ sót thứ còn thiếu.

Cơ sở đối chiếu: repo `xkld-chatbot` tại thời điểm 2026-09-03.

## 1. Backend

| Module hiện có | Trạng thái | Hành động |
|---|---|---|
| `app/api/chat.py` | Chạy được | **Sửa**: thêm `sources`, `is_fallback`, chuẩn hóa response schema |
| `app/api/auth.py` + `app/auth/security.py` | Đủ dùng | **Giữ** |
| `app/api/analytics.py` | Cơ bản | **Mở rộng**: thêm funnel, chỉ số CV/recommendation |
| `app/api/appointments.py` | Đầy đủ | **Sửa nhẹ**: thêm `candidate_id` |
| `app/api/management.py` | Đang gom nhiều thứ | **Tách** thành `candidates.py`, `leads.py`, `job_orders.py` |
| `app/api/applications.py`, `customer_journey.py`, `audit.py` | Chạy được | **Giữ**, liên kết `candidate_id` |
| `app/conversation/intent_classifier.py` | 11 nhóm khác spec | **Sửa**: đổi sang 10 nhóm chuẩn |
| `app/conversation/entity_extractor.py` | Có sẵn | **Mở rộng**: thêm `desired_location`, `birth_year` |
| `app/conversation/reference_resolver.py` | Có sẵn | **Giữ** |
| `app/conversation/response_validator.py` | Có sẵn | **Sửa**: áp công thức confidence 3 thành phần, chặn số liệu bịa |
| `app/conversation/session_manager.py` | Có sẵn | **Sửa**: liên kết `candidate_id` |
| `app/rag/retriever.py` | Chạy được, `TOP_K = 5` | **Sửa**: `TOP_K = 4`, thêm retry lần 2 bỏ filter topic |
| `app/rag/prompt_builder.py` | Có sẵn | **Sửa**: đưa prompt ra file `.txt` |
| `app/rag/taxonomy.py` | Taxonomy cũ | **Viết lại** theo 10 intent |
| `app/llm/gemini.py` | Có retry đúng ý tưởng nhưng dùng `requests` sync | **Sửa lớn**: chuyển `httpx.AsyncClient`, `MAX_RETRIES = 3`, thêm circuit breaker |
| `app/db/database.py` | Đầy đủ index | **Mở rộng**: collection và index mới |
| `app/db/qdrant.py` | 13 dòng, quá mỏng | **Mở rộng**: quản lý collection, upsert theo batch, xóa theo `document_id` |
| `app/core/config.py` | `dataclass` thuần | **Sửa**: chuyển `pydantic_settings.BaseSettings` |
| `app/core/phone.py` | Chuẩn hóa SĐT VN | **Giữ** |
| `app/core/rate_limit.py` | Có sẵn | **Giữ**, áp thêm cho endpoint mới |
| `app/services/chat_service.py` | 118 dòng | **Sửa**: gọi qua `rag_service` facade |
| `app/services/analytics_service.py`, `audit_service.py`, `customer_journey_service.py` | Chạy được | **Giữ** |
| `app/booking/booking_service.py` | Đầy đủ | **Giữ**, chuyển sang `services/` cho đúng phân tầng |
| `app/lead/` | Gần như rỗng | **Viết mới** thành `services/lead_service.py` |
| `app/handoff/` | Rỗng | **Viết mới** hoặc gộp vào `lead_service` |
| `ingestion/crawler.py`, `embedder.py`, `image_reader.py` | Chạy được | **Tái sử dụng** cho `knowledge_worker` và OCR CV |
| `tests/` 15 file | Có giá trị | **Giữ**, phải pass sau mỗi lần refactor |

### Viết hoàn toàn mới

`api/documents.py`, `api/candidates.py`, `api/analysis.py`,
`api/recommendations.py`, `api/job_orders.py`, `api/knowledge.py`,
toàn bộ `schemas/`, `repositories/`, `workers/`,
`engines/matching_engine.py`, `engines/document_parser.py`, `engines/chunker.py`,
`services/{rag,document,candidate,analysis,matching,summary,knowledge}_service.py`,
`core/{logging,exceptions}.py`.

## 2. Frontend

| Hiện có | Hành động |
|---|---|
| `frontend/` Chat Widget | **Mở rộng**: upload CV, thẻ hồ sơ, thẻ đơn hàng, form đặt lịch |
| `frontend/` trang `/` là trang mẫu | **Viết mới**: landing page đầy đủ + các trang nội dung |
| `admin-frontend/` các trang leads, conversations, knowledge, appointments, users, audit-logs, applications | **Giữ và hoàn thiện** |
| `admin-frontend/` | **Viết mới**: `candidates/[id]` (360 độ), `documents`, `recommendations`, `job-orders`, `analytics` đầy đủ |

## 3. Hạ tầng

Chưa có gì: không có `Dockerfile`, `docker-compose.yml`, `nginx.conf`.
Toàn bộ phải viết mới trong tuần 1.

## 4. Vệ sinh repo

| Vấn đề | Ảnh hưởng | Xử lý |
|---|---|---|
| `backend/venv/` đang nằm trong repo | Repo phình hàng nghìn file, clone chậm, review nhiễu | `git rm -r --cached backend/venv` + thêm vào `.gitignore` |
| `admin-frontend/.next/` đang nằm trong repo | Artifact build không nên commit | Tương tự |
| Chưa có `.env.example` | Người khác không dựng lại được | Viết mới |
| `check_qdrant.py` ở gốc `backend/` | Sai vị trí | Chuyển vào `scripts/` |

## 5. Ba thay đổi phá vỡ tương thích cần cân nhắc kỹ

### 5.1 Đổi taxonomy intent (M4) — rủi ro cao nhất

Taxonomy hiện tại và taxonomy theo spec không phải quan hệ một-một:

| Hiện có | Theo spec |
|---|---|
| `chi_phi` | → `CHI_PHI` |
| `quy_trinh` | → `QUY_TRINH` |
| `dieu_kien` | → `DIEU_KIEN` |
| `luong_thuong` | → `LUONG` |
| `cong_viec` | → `DON_HANG` (không khớp hoàn toàn) |
| `phong_van` | → gộp vào `QUY_TRINH` |
| `thoi_gian` | → gộp vào `QUY_TRINH` |
| `hoc_tap` | → `TIENG_NHAT` |
| `ky_tuc_xa` | → không có tương ứng, gộp `DON_HANG` |
| — | `HO_SO` (mới) |
| — | `VISA` (mới) |
| — | `DIA_DIEM` (mới) |
| — | `DANG_KY` (mới) |

Hệ quả: payload `topic` của toàn bộ point trong Qdrant sai, filter theo topic sẽ
trả kết quả lệch. **Bắt buộc re-embed lại 32 bài đã crawl.** Ước tính:
khoảng 400–600 chunk, mỗi chunk một lần gọi embedding — nằm trong quota free
nếu chạy theo batch và có nghỉ giữa các lô.

Khuyến nghị: làm dứt điểm ở **tuần 5**, không để trễ hơn. Càng thêm dữ liệu KB
thì chi phí re-embed càng lớn.

### 5.2 `managed_leads` → `candidates` (M1)

Đổi tên kèm đổi ý nghĩa: `managed_leads` hiện vừa là khách hàng vừa là lead.
Thiết kế mới tách đôi: `candidates` là con người, `leads` là **nhu cầu cần liên hệ**
tại một thời điểm. Một candidate có thể sinh nhiều lead theo thời gian.

Cách làm an toàn: viết script tạo `candidates` từ `managed_leads`, giữ collection
cũ ở chế độ chỉ đọc một tuần, đối chiếu số lượng bản ghi rồi mới xóa.

### 5.3 Gemini sync → async

`app/llm/gemini.py` dùng `requests` + `time.sleep`. Trong FastAPI async, mỗi lần
retry `time.sleep(10)` sẽ **chặn toàn bộ event loop**, làm mọi request khác của
server treo theo. Với 3 lần retry, một request lỗi có thể đóng băng server 17 giây.

Đây là lỗi thật, cần sửa ở tuần 1 trước khi xây thêm tính năng lên trên.

## 6. Ước lượng khối lượng

| Nhóm | Giữ nguyên | Sửa | Viết mới |
|---|:--:|:--:|:--:|
| Backend | ~35% | ~30% | ~35% |
| Frontend ứng viên | ~20% | ~20% | ~60% |
| Admin Dashboard | ~50% | ~20% | ~30% |
| Hạ tầng | 0% | 0% | 100% |

Kết luận: repo hiện tại tiết kiệm được khoảng **4–5 tuần** so với làm lại từ đầu.
Phần mới của đề tài (CV → Profile → Matching → Recommendation → Summary) chiếm
phần lớn khối lượng còn lại, và cũng chính là phần tạo nên giá trị học thuật
của đồ án.
