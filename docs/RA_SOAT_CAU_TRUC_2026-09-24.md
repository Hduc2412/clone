# Rà soát cấu trúc toàn workspace

Ngày: 24/09/2026. Phạm vi: cấu trúc thư mục, điểm vào frontend/backend, phân loại tài liệu/đầu vào, phụ thuộc triển khai và trạng thái Git. Không phải kiểm toán đầy đủ bảo mật, không xác nhận chất lượng nội dung từng báo cáo và chưa chạy kiểm thử chức năng trong đợt rà soát này.

## 1. Kết luận

Hiện có hai frontend và một backend, không phải sáu hệ thống triển khai độc lập. Đây là cấu trúc phù hợp để tiếp tục MVP nếu ranh giới module rõ ràng. Không nên nhân bản frontend/backend/database cho từng vai trò chỉ để có thư mục riêng.

Tên thư mục `xkld-chatbot` không còn phản ánh phạm vi: đây là hệ thống tuyển dụng, phân tích hồ sơ và hỗ trợ tư vấn. Chatbot chỉ là một module. Tư vấn theo đơn cần được tách rõ về giao diện, trạng thái phiên và điều phối nghiệp vụ; không chỉ đổi tên thư mục.

## 2. Bản đồ code hiện tại

| Phần nghiệp vụ | Giao diện | Backend chính | Nhận xét cấu trúc |
| --- | --- | --- | --- |
| Website công khai | `frontend/app/(site)`, `components/site`, `content` | API public đơn tuyển dụng | Đã có trang đơn, chi tiết, thông tin, FAQ, liên hệ |
| Không gian khách hàng | `frontend/components/portal`, các route `tai-khoan`, `ho-so-cua-toi` | `api/candidate_auth.py`, `api/portal.py`, `auth/candidate_security.py` | Tách thành module trong website, không cần website thứ ba |
| CV, hồ sơ và đối chiếu | `frontend/components/candidate` | `api/documents.py`, `api/profiles.py`, `api/matching.py`, `documents/`, `matching/`, các service tương ứng | Có nền tảng đối chiếu, chưa đồng nghĩa với phòng tư vấn hội thoại hoàn chỉnh |
| Tư vấn AI theo đơn | Route `tu-van`, `ConsultationFlow.tsx` | `consultation/`, `learning/`, `services/chat_service.py` và các module hồ sơ/matching | Chưa tách rõ khỏi luồng chatbot; một phần code mới còn untracked |
| Chatbot chung | `components/ChatWidget.tsx`, `ChatWindow.tsx`, `ChatMessage.tsx`, `ChatPage.tsx`, `hooks/useChat.ts` | `api/chat.py`, `services/chat_service.py`, `conversation/`, `rag/`, `llm/` | Có thể gom frontend theo feature; không chuyển cả RAG thành module CV |
| Nhân viên | `admin-frontend/app/admin`: queue, leads, profiles, applications, appointments, conversations | API management, applications, appointments, customer journey; service phân công/report | Dùng chung ứng dụng nội bộ, thao tác phải kiểm tra quyền và người phụ trách ở backend |
| Manager | Cùng ứng dụng nội bộ: phân công, nhân viên, điểm, thống kê | Các API quản lý với quyền manager/admin | Không cần database nhân viên riêng để phân quyền |
| Admin | Cùng ứng dụng nội bộ: users, knowledge, audit logs và cấu hình liên quan | Auth, management, audit và kiểm tra vai trò | Tên URL `/admin` không có nghĩa mọi người được quyền admin |

Các thư mục `backend/app/lead` và `backend/app/handoff` chỉ có file khởi tạo rỗng, không đại diện cho một module đã triển khai. Nghiệp vụ thực tế nằm ở API/service/DB khác.

**Đã xử lý ngày 28/09/2026: xóa cả hai.** Một gói rỗng không ai import là chỗ mời người sau đặt nhầm logic vào — họ thấy tên thư mục hợp lý và tưởng đó là đầu mối đã chọn, trong khi nghiệp vụ thật nằm nơi khác. Cần lại thì tạo lại mất một giây.

## 3. Phân biệt tài liệu và input

| Nhóm | Vị trí | Cách sử dụng |
| --- | --- | --- |
| Báo cáo học thuật | `tailieu/*.docx`, `tailieu/*.pptx` | Tài liệu trình bày; không tự động đưa vào RAG |
| Mẫu báo cáo | `2025_10.BaoCaoTN_2024_Mau.docx`, `MauBC_Hang2Tuan.pptx` | Giữ bản mẫu, không nhầm với bản nộp |
| Tài liệu kỹ thuật/nghiệp vụ | `docs/design`, `docs/handoff`, các hướng dẫn trong `docs` | Đặc tả triển khai; cần chỉ rõ bản hiện hành, không coi mọi bản lịch sử là đồng thời đúng |
| Mẫu nhập đơn | `tailieu/DonHang/MauDonHang_ChuDe.xlsx`, `HUONG_DAN.md` | Input quản trị đơn; validate trước khi lưu DB |
| Nguồn tri thức tư vấn | Nguồn website qua `backend/ingestion` | Nguồn cần quản lý xuất xứ, ngày cập nhật và trạng thái duyệt |
| Cache trích chữ từ ảnh | `backend/data/image_vision_cache.json` | Dữ liệu dẫn xuất, hiện có 32 mục; không phải kho ảnh gốc hoặc snapshot Qdrant |
| Placeholder tri thức | `backend/knowledge.md` | Rỗng — **đã xóa ngày 28/09/2026** |
| CV khách thật | `backend/storage` ở local; volume `backend_storage` khi chạy Compose | Dữ liệu riêng tư; không gom vào tài liệu chia sẻ hoặc Git |
| CV test và đáp án | `backend/tests/fixtures/cv` | Input kiểm thử, tách khỏi CV thật |
| Bộ câu hỏi kiểm thử | `backend/tests/fixtures/chatbot`, `backend/tests/fixtures/danh_gia` | Dữ liệu đánh giá, không phải nguồn trả lời mặc định |
| Seed đơn/CV/khóa học | `backend/scripts/seed_data` | Dữ liệu demo; không chứng minh điều kiện tuyển dụng thực tế |
| Trọng số matching | `backend/app/matching/weights.json` | Cấu hình thuật toán, không phải input khách gửi |
| Nội dung website | `frontend/content` | Nội dung hiển thị; không tự động đồng bộ thành tri thức RAG |
| Hình nền giao diện | `frontend/public/nen` và `NGUON.md` | Tài nguyên thiết kế, không phải ảnh tài liệu tư vấn |
| Cấu hình bí mật | `.env`, `.env*.local` | Giữ riêng; chỉ chia sẻ `.env.example` không có bí mật |
| Bản xuất chia sẻ | `tailieu/Gui_chia_se_20260924` | PDF đầu ra; không phải nguồn ingestion mặc định |

MongoDB lưu dữ liệu nghiệp vụ; Qdrant phục vụ truy xuất tri thức. Docker volume không nằm trực tiếp trong cây thư mục nguồn. Chỉ copy thư mục dự án chưa đủ để backup dữ liệu đang chạy.

## 4. Điểm cần xử lý trước khi gom code

### 4.1. Luồng đơn đã chọn chưa nối đầy đủ vào UI đối chiếu

`frontend/app/(site)/don-hang/[code]/page.tsx` chuyển tới `/tu-van?don=...`. Trang `tu-van/page.tsx` đọc query để hiện tên đơn, nhưng render `<ConsultationFlow />` không truyền đơn. Component này không đọc query đó. Vì vậy nhánh kết nối đã kiểm tra chưa thực hiện lời hứa trên UI rằng đơn vừa xem sẽ được đánh dấu trong kết quả.

Đề xuất lần triển khai tiếp theo: truyền `selectedOrderCode` có validate; hiển thị đơn đang tư vấn; duy trì mã đơn xuyên suốt CV → nhu cầu → đối chiếu → hội thoại → xác nhận. Kiểm thử người dùng đổi đơn và mở nhiều tab. Đây là phát hiện từ code, chưa tái hiện bằng trình duyệt trong lần rà soát này.

### 4.2. Tư vấn chuyên sâu còn dùng điều phối chat chung

`services/chat_service.py` đang import `consultation.context_builder` và `next_question`. Việc có thư mục `consultation` chưa chứng minh đã có một phòng AI tư vấn theo đơn độc lập. Cần tách use case, không nhất thiết tách server:

- Chat chung: hỏi thông tin website, FAQ, hướng dẫn và dẫn tới đơn.
- Tư vấn theo đơn: phiên có đơn mục tiêu, hồ sơ/CV, nhu cầu, tiêu chí, kết quả đối chiếu và xác nhận của khách.
- Dùng chung adapter LLM, dữ liệu đơn và thành phần trích xuất hợp lý; không trộn lịch sử/ngữ cảnh hai phiên ngoài ý muốn.
- Chỉ chuyển hồ sơ và report cho nhân viên khi khách xác nhận; chưa có CV vẫn có luồng để lại thông tin yêu cầu liên hệ.

CV trong luồng đã thống nhất được trích xuất văn bản; không mặc định gửi toàn bộ PDF/ảnh sang mô hình. Tiêu chí thiếu phải hỏi lại, không suy đoán. N4 chỉ là giả định demo nếu gắn cho đơn mẫu, không áp đặt cho mọi đơn hoặc sửa nguồn gốc tài liệu cho khớp demo.

### 4.3. Tài liệu và bản làm việc dễ nhầm

- Có nhiều báo cáo tổng quan và hai PPT tiến độ; cần gắn nhãn mục đích/bản sử dụng, không xóa theo tên gần giống nhau.
- README repo chưa bao quát đúng các module website, CV/matching và cổng khách hiện có; nên đồng bộ sau khi chốt ranh giới module.
- Script dựng báo cáo ở workspace root có đường dẫn gốc `F:\DoAnTotNghiep`; chuyển script/tài liệu cần kiểm tra cả đường dẫn input/output và công cụ render.
- `ingestion/image_reader.py` dùng đường dẫn cache tương đối `backend/data/image_vision_cache.json`; thay cây thư mục hoặc thư mục chạy có thể làm đọc nhầm/mất cache.
- Compose dùng volume Qdrant external `qdrant_data`; hướng dẫn chạy cũ có tên `qdrant_storage`. Cần kiểm tra volume chứa dữ liệu thật trước khi chỉnh hướng dẫn hoặc chạy ingestion lại, không đổi/xóa volume theo tên cho đẹp.

### 4.4. Git và các thư mục ẩn

Repo chính đang ở nhánh `feature/job-orders-and-matching`, có nhiều thay đổi chưa commit và file chưa được theo dõi. Giữ nguyên thay đổi hiện hữu.

`.push-web-xkld` là worktree nhánh `publish/web-xkld` của repo chính. `.publish-xkld-dieu-duong` có `.git` riêng. Không di chuyển/xóa hai thư mục như cache. Các thư mục render/backup có thể chứa script hoặc bản duy nhất; cần lập danh sách trước khi lưu trữ.

## 5. Cấu trúc đích đề xuất — chưa di chuyển

```text
DoAnTotNghiep/
├── README_THU_MUC.md
├── tailieu/
│   ├── bao-cao/          # DOCX, đề cương
│   ├── trinh-chieu/      # PPTX bản sử dụng
│   ├── mau/              # mẫu Word, mẫu PowerPoint
│   └── ban-xuat/         # PDF để chia sẻ
├── input/
│   ├── don-tuyen-dung/   # mẫu import, không gom hồ sơ khách
│   └── tri-thuc/         # nguồn gốc đã duyệt và manifest xuất xứ
├── cong-cu-tai-lieu/     # script dựng/render, sau khi sửa đường dẫn
├── luu-tru/              # backup và QA được xác nhận có thể chuyển
└── xkld-chatbot/          # giữ tên hiện tại trong đợt đầu
    ├── frontend/         # website + cổng khách
    ├── admin-frontend/   # nhân viên + manager + admin
    ├── backend/          # API và module nghiệp vụ/AI
    ├── docs/             # tài liệu kỹ thuật đi cùng code
    └── deploy/
```

Trong frontend, đích hợp lý là nhóm feature `website`, `candidate-portal`, `consultation`, `chatbot`, bên cạnh UI dùng chung. Route vẫn nằm trong `app` theo Next.js; không đổi URL chỉ để đổi tên folder.

Trong ứng dụng nội bộ, nhóm feature theo nghiệp vụ: reception/queue, applications, appointments, customers, job-orders, staff, knowledge, audit. Vai trò quyết định quyền và màn hình được thấy; tránh copy một trang ra ba thư mục nhân viên/manager/admin.

Backend tiếp tục có API, service, repository và các domain CV/profile, matching, consultation, chatbot/RAG, registrations, appointments, assignment, scoring. Chỉ gom từng domain khi có test bảo vệ; không đồng thời đảo toàn bộ cấu trúc import.

`input/` ở workspace là đề xuất phân loại nguồn, KHÔNG tự động là đường dẫn ingestion mới hoặc thư mục được public. Dữ liệu private vẫn ở storage/database, file seed/test vẫn ở code repo. Khi đóng gói triển khai phải có manifest chỉ rõ input nào cần copy và input nào bị loại.

## 6. Trình tự thực hiện an toàn

1. Hoàn thành chỉ mục phân loại (đã thực hiện trong lượt này). Bảo toàn dirty worktree; không tự commit thay đổi của người khác.
2. Chốt bản báo cáo/PPT đang dùng; lập bảng đường dẫn cũ → mới. Chỉ chuyển tài liệu/input đã rõ, sửa script tương ứng và mở/render kiểm tra lại.
3. Gom frontend chatbot và consultation theo feature, sửa import, không thay nghiệp vụ cùng lúc. Chạy lint/typecheck/build và test hiện có ở cả hai frontend.
4. Hoàn thiện kết nối đơn mục tiêu và phòng tư vấn: trích chữ CV → xác nhận thông tin/nhu cầu → đối chiếu → giải thích/hỏi bổ sung/đề xuất đơn khác hoặc học → khách xác nhận → report/nhân viên. Việc chuyển sang học không tự tạo đăng ký học viên.
5. Rà phân quyền nhân viên/manager/admin, nhận hồ sơ atomic và kiểm tra quyền sở hữu ở backend; kiểm thử API, không chỉ ẩn menu.
6. Đồng bộ README, cấu hình Docker, đường dẫn cache/storage và hướng dẫn backup. Chạy kiểm thử luồng đầu-cuối rồi mới cân nhắc đổi tên thư mục repo.
7. Sau khi xác nhận không còn dữ liệu riêng/nhánh chưa lưu trong các bản publish và QA, mới dọn bằng thao tác có thể phục hồi. Không xóa volume MongoDB/Qdrant/CV.

## 7. Những gì đã thay đổi trong lượt rà soát

Chỉ thêm `README_THU_MUC.md` ở workspace và tài liệu này trong `docs`. Chưa sửa logic, import, đường dẫn chạy, báo cáo Word/PowerPoint; chưa di chuyển/xóa dữ liệu; chưa commit/push; chưa chạy server hoặc test chức năng.
