# Bộ tài liệu thiết kế hệ thống

**Tên đề tài:** Xây dựng hệ thống AI hỗ trợ phân tích hồ sơ, tư vấn và quản lý ứng viên
xuất khẩu lao động điều dưỡng Nhật Bản.

**Ngày lập:** 2026-09-03. **Trạng thái:** thiết kế, chưa triển khai code phần mới.

## Danh mục tài liệu

| # | Tài liệu | Nội dung |
|---|---|---|
| 01 | [Requirements](01_REQUIREMENTS.md) | Actor, yêu cầu chức năng (FR), phi chức năng (NFR), phạm vi MoSCoW |
| 02 | [Use Case](02_USECASE.md) | Sơ đồ và đặc tả use case chi tiết |
| 03 | [Workflow](03_WORKFLOW.md) | Luồng nghiệp vụ end-to-end, sequence diagram |
| 04 | [Database Schema](04_DATABASE.md) | Collection MongoDB, Qdrant collection, index, migration |
| 05 | [API Specification](05_API.md) | Toàn bộ endpoint REST, request/response |
| 06 | [Frontend Screens](06_FRONTEND.md) | Sitemap, đặc tả từng màn hình, component |
| 07 | [AI Pipeline](07_AI_PIPELINE.md) | Chat pipeline, CV pipeline, matching engine, prompt |
| 08 | [Architecture](08_ARCHITECTURE.md) | Kiến trúc tầng, deployment, cấu trúc thư mục |
| 11 | [Kiến trúc tổng quan](11_KIEN_TRUC_TONG_QUAN.md) | **Đọc trước tiên** — phát biểu bài toán, bốn khối trên ba mặt phẳng, ba luồng dữ liệu, ranh giới quyết định (kèm `Fig. 2.1`) |
| 12 | [Yêu cầu hệ thống](12_YEU_CAU_HE_THONG.md) | Người dùng, yêu cầu chức năng A–F, yêu cầu phi chức năng, những điều hệ thống không làm |
| 13 | [Phạm vi và trạng thái](13_PHAM_VI_VA_TRANG_THAI.md) | Cơ bản vs nâng cao, đã làm được gì, còn thiếu gì, thứ tự triển khai |
| 14 | [Nghiệp vụ và giá trị](14_NGHIEP_VU_VA_GIA_TRI.md) | Viết cho người ngoài ngành — câu chuyện thực tế, luồng đi, tác dụng |
| 16 | [Nội dung website](16_NOI_DUNG_WEBSITE.md) | Nội dung từng trang của website khách hàng |
| 17 | [Chính sách tài chính, thời gian, quy trình](17_CHINH_SACH_TAI_CHINH_THOI_GIAN_QUY_TRINH.md) | Gom những gì kho tri thức đã nói về tiền, mốc thời gian và các bước; kèm danh sách câu kho **chưa** trả lời được |

## Nguyên tắc xuyên suốt

1. **Giá trị cốt lõi không phải chatbot** mà là chuỗi: dữ liệu phi cấu trúc (chat + CV)
   → dữ liệu có cấu trúc (Profile) → phân tích → matching → đề xuất → lead → lịch hẹn.
2. **AI không suy diễn.** Mọi nhận định về ứng viên phải trích dẫn được bằng chứng
   (câu trong CV hoặc câu trong hội thoại). Không sinh tính từ cảm tính.
3. **Con người ra quyết định cuối.** AI đề xuất, nhân viên tư vấn xác nhận.
4. **Tái sử dụng tối đa code đã có.** Không viết lại những module đã chạy và có test.
