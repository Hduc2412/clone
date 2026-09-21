# 09 — Chia việc và tiến độ

Tổng thời gian: **11 tuần**. Điểm xuất phát không phải con số 0 — repo đã có
chatbot RAG, đặt lịch, dashboard quản lý, JWT và 15 file test. Kế hoạch dưới đây
tập trung phần **mới** của đề tài và phần **còn thiếu**.

## 1. Bảng tổng quan

| Tuần | Trọng tâm | Kết quả bàn giao |
|:--:|---|---|
| 1 | Nền tảng hạ tầng và refactor | Docker chạy được, tầng kiến trúc rõ ràng |
| 2 | Job Orders + Candidate | CRUD đơn hàng, model ứng viên thống nhất |
| 3 | CV Upload + Parser | Upload và đọc được PDF/DOCX/ảnh |
| 4 | Candidate Profile Extraction | Sinh hồ sơ có evidence từ CV |
| 5 | Need Analysis + Chat nâng cấp | Consultation Profile, intent 10 nhóm |
| 6 | Matching Engine | Chấm điểm và đề xuất đơn hàng |
| 7 | Consultation Summary + Lead | Phiếu tổng hợp, vòng đời Lead 4 trạng thái |
| 8 | Knowledge Management | Upload KB, FAQ, công cụ test truy vấn |
| 9 | Admin Dashboard hoàn thiện | Hồ sơ 360 độ, các màn hình mới |
| 10 | Website + Widget hoàn thiện | Landing page, upload CV trong chat |
| 11 | Kiểm thử, đo lường, tài liệu | Báo cáo, số liệu đánh giá, demo |

## 2. Chi tiết theo tuần

### Tuần 1 — Nền tảng

| # | Việc | Đầu ra |
|---|---|---|
| 1.1 | `.gitignore`: loại `venv/`, `.next/`, `node_modules/`, `storage/`, `.env` | Repo sạch |
| 1.2 | `docker-compose.yml` + 3 `Dockerfile` + `nginx.conf` | `docker compose up` chạy toàn stack |
| 1.3 | Chuyển `core/config.py` sang `pydantic_settings.BaseSettings` | Thiếu biến môi trường thì chết ngay lúc khởi động |
| 1.4 | `core/logging.py` + middleware `request_id` + che SĐT | Log JSON có `X-Request-ID` |
| 1.5 | `core/exceptions.py` + exception handler thống nhất | Mọi lỗi trả đúng format `{error: {code, message, request_id}}` |
| 1.6 | Chuyển `llm/gemini.py` sang `httpx.AsyncClient` + circuit breaker | Không còn chặn event loop |
| 1.7 | Tách `api/*.py` sang `schemas/*.py`, tạo `repositories/` | Đúng phân tầng ở [08](08_ARCHITECTURE.md) §2 |

*Tiêu chí hoàn thành*: `docker compose up` lên đủ 6 service, `/health` xanh,
toàn bộ test cũ vẫn pass.

### Tuần 2 — Job Orders và Candidate

| # | Việc |
|---|---|
| 2.1 | Schema + repository + service + router `job_orders` (CRUD đầy đủ) |
| 2.2 | Màn hình admin quản lý đơn hàng |
| 2.3 | Seed 15–20 đơn hàng mẫu sát thực tế |
| 2.4 | Migration M1: `managed_leads` → `candidates` |
| 2.5 | Migration M2: thêm `candidate_id` vào `sessions`, `messages`, `appointments` |
| 2.6 | API `candidates` (list, detail, overview, timeline, notes) |
| 2.7 | Test: dedup theo SĐT, phân quyền consultant chỉ thấy ứng viên được giao |

*Tiêu chí*: có dữ liệu đơn hàng thật để tuần 6 matching có cái để chấm.

### Tuần 3 — CV Upload và Parser

| # | Việc |
|---|---|
| 3.1 | `POST /documents/upload`: validate MIME + magic bytes, giới hạn 10MB, lưu volume |
| 3.2 | `engines/document_parser.py`: PDF (PyMuPDF), DOCX (python-docx) |
| 3.3 | Nhánh OCR: PDF scan và ảnh → Gemini Vision |
| 3.4 | `workers/document_worker.py`: BackgroundTask cập nhật `status`/`progress` |
| 3.5 | API tra trạng thái, tải file, xóa |
| 3.6 | Test với 10 CV mẫu đủ định dạng, gồm cả file hỏng |

*Rủi ro*: CV tiếng Việt scan chất lượng thấp. Giảm thiểu: luôn giữ `raw_text`
để nhân viên đọc tay khi AI thất bại; trạng thái `PARTIAL` thay vì `FAILED` cứng.

### Tuần 4 — Candidate Profile Extraction

| # | Việc |
|---|---|
| 4.1 | Prompt trích xuất + `response_schema` JSON |
| 4.2 | `analysis_service.extract_candidate_profile()` |
| 4.3 | **Evidence Validator**: loại field không có căn cứ trong `raw_text` |
| 4.4 | Merger theo thứ tự ưu tiên nguồn |
| 4.5 | Lưu `candidate_profiles` + `candidate_profile_history` |
| 4.6 | API sửa profile thủ công (ứng viên và nhân viên) |
| 4.7 | Đo độ chính xác trên 30 CV mẫu, ghi số liệu vào báo cáo |

*Tiêu chí*: 0% strengths không có evidence; ≥ 80% field trích đúng.

### Tuần 5 — Need Analysis và nâng cấp Chat

| # | Việc |
|---|---|
| 5.1 | Đổi taxonomy intent sang 10 nhóm (xem [10](10_GAP_ANALYSIS.md) M4) |
| 5.2 | Re-embed lại Knowledge Base theo topic mới |
| 5.3 | Xây bộ test 200 câu gán nhãn intent, đo accuracy |
| 5.4 | `need_analysis` sinh Consultation Profile, chạy theo mốc lượt hội thoại |
| 5.5 | `services/rag_service.py` facade: retriever → prompt → LLM → validator |
| 5.6 | Response Validator: công thức confidence + chặn số liệu bịa |
| 5.7 | Retry lần 2 không filter topic khi Top-K rỗng |

### Tuần 6 — Matching Engine

| # | Việc |
|---|---|
| 6.1 | `engines/matching_engine.py`: hard filter + chấm điểm 5 tiêu chí |
| 6.2 | Unit test bảng quyết định: đủ, thiếu 1 bậc, thiếu 2 bậc, thiếu ngành... |
| 6.3 | Sinh `matched_reasons` và `gaps` bằng code |
| 6.4 | LLM diễn giải, có template dự phòng khi LLM lỗi |
| 6.5 | API `/analysis/match` và `/recommendations` |
| 6.6 | Màn hình duyệt/bác bỏ đề xuất |

*Tiêu chí*: cùng input cho ra cùng score ở mọi lần chạy (kiểm bằng test).

### Tuần 7 — Summary và Lead

| # | Việc |
|---|---|
| 7.1 | `summary_service`: sinh phiếu 5 mục, đánh dấu `is_stale` |
| 7.2 | Chuẩn hóa `leads.status` về 4 giá trị + `status_history` |
| 7.3 | Tự tạo Lead khi fallback / yêu cầu gặp người / có SĐT |
| 7.4 | Quy tắc nâng `URGENT`: đã nộp CV + có match CAO, hoặc đã đặt lịch |
| 7.5 | API phân công, ghi chú, đổi trạng thái (bắt buộc lý do khi lùi) |
| 7.6 | Notification cho nhân viên |

### Tuần 8 — Knowledge Management

| # | Việc |
|---|---|
| 8.1 | `POST /knowledge/upload` + worker: parse → chunk → embed → upsert |
| 8.2 | `engines/chunker.py`: 500 token, overlap 50, giữ tiêu đề section |
| 8.3 | Point ID idempotent (UUID v5), xóa point cũ trước khi re-index |
| 8.4 | CRUD FAQ + đồng bộ vector |
| 8.5 | `POST /knowledge/search` để test truy vấn, hiện chunk và score |
| 8.6 | Màn hình KB: kéo thả, thanh tiến trình, retry khi `FAILED` |

### Tuần 9 — Admin Dashboard

| # | Việc |
|---|---|
| 9.1 | Trang hồ sơ ứng viên 360 độ, 8 tab |
| 9.2 | Nhãn nguồn và tooltip evidence cho mọi giá trị AI sinh |
| 9.3 | Danh sách ứng viên: lọc, tìm kiếm, thao tác hàng loạt |
| 9.4 | Lead: chế độ bảng và Kanban |
| 9.5 | Màn hình quản lý CV |
| 9.6 | Analytics: 6 biểu đồ + phễu chuyển đổi + xuất CSV |
| 9.7 | Kiểm tra phân quyền trên toàn bộ màn hình |

### Tuần 10 — Website và Widget

| # | Việc |
|---|---|
| 10.1 | Landing page 9 section, responsive từ 360px |
| 10.2 | Các trang nội dung + trang đơn hàng công khai |
| 10.3 | Widget: upload CV, thanh tiến trình, thẻ hồ sơ, thẻ đơn hàng |
| 10.4 | Card form thu SĐT, quick reply, form đặt lịch trong chat |
| 10.5 | Xử lý mất mạng, hàng đợi tin nhắn, nút gửi lại |
| 10.6 | SEO cơ bản, Lighthouse ≥ 85 |

### Tuần 11 — Kiểm thử và tài liệu

| # | Việc |
|---|---|
| 11.1 | Test tích hợp toàn luồng: chat → CV → profile → match → lead → lịch hẹn |
| 11.2 | Đo và ghi lại 6 chỉ số chất lượng AI ở [07](07_AI_PIPELINE.md) §7 |
| 11.3 | Test tải nhẹ: 50 phiên đồng thời |
| 11.4 | Kiểm tra bảo mật: phân quyền, upload độc hại, rate limit |
| 11.5 | `docker-compose.prod.yml` + hướng dẫn triển khai |
| 11.6 | Viết báo cáo, vẽ sơ đồ, chuẩn bị kịch bản demo |
| 11.7 | Chuẩn bị dữ liệu demo sạch và có tính thuyết phục |

## 3. Đường găng và rủi ro

```
Docker + refactor (T1)
   → Job Orders (T2)  ────────────┐
   → CV Upload (T3) → Profile (T4)┤
                                  ├→ Matching (T6) → Summary (T7) → Dashboard (T9)
   → Need Analysis (T5) ──────────┘
```

Tuần 3–4 là đường găng. Nếu CV parsing trượt tiến độ, mọi thứ sau đó trượt theo.

| Rủi ro | Mức | Giảm thiểu |
|---|:--:|---|
| Quota Gemini free hết giữa chừng | Cao | Cache embedding; tầng rule cho intent; batch khi ingest; chuẩn bị API key dự phòng |
| OCR CV tiếng Việt kém chính xác | Cao | Luôn giữ `raw_text`; cho phép sửa tay; trạng thái `PARTIAL` |
| Re-embed KB tốn thời gian và quota | Trung bình | Làm 1 lần trong tuần 5, chạy nền, ghi log tiến trình |
| Thiếu dữ liệu đơn hàng thật | Trung bình | Tuần 2 tự soạn 15–20 đơn mẫu sát thực tế |
| Phạm vi phình to | Cao | Bám MoSCoW; mọi tính năng ngoài MUST/SHOULD đẩy sang "Hướng phát triển" |
| Thời gian viết báo cáo bị ép | Trung bình | Viết tài liệu song song từ tuần 1, không dồn vào tuần 11 |

## 4. Definition of Done cho mỗi hạng mục

Một việc chỉ được tính là xong khi đủ cả 5 điều kiện:

1. Có Pydantic schema cho request và response, không dùng `dict` trần.
2. Có ít nhất một test (unit hoặc integration) cho luồng chính và một luồng lỗi.
3. Mọi lệnh gọi ngoài (Gemini, Qdrant) đều có xử lý lỗi và fallback.
4. Không còn `TODO`, không còn dữ liệu giả trong đường đi chính.
5. Chạy được trong Docker, không chỉ chạy trên máy local.
