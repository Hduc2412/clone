# Cấu trúc dự án và cách hai phần kết nối với nhau

Tài liệu này dành cho người đọc cần hiểu **dự án gồm những phần nào, ai làm phần
nào, và hai phần nói chuyện với nhau ra sao**. Viết cho cả hai phía: người phát
triển chatbot và người phát triển web nghiệp vụ.

Cập nhật: 14/09/2026.

---

## 1. Dự án gồm bốn khối

```
                    ┌─────────────────────────────────────────┐
   Ứng viên  ─────► │  frontend/        Website khách hàng     │
   (không có        │                   + khung chat góc phải  │
    tài khoản)      └──────────────┬──────────────────────────┘
                                   │  HTTP
                    ┌──────────────▼──────────────────────────┐
                    │  backend/         FastAPI               │
                    │  ┌───────────────┬────────────────────┐ │
                    │  │ Phân hệ       │ Phân hệ nghiệp vụ  │ │
                    │  │ hội thoại     │ (đơn hàng, CV,     │ │
                    │  │ (chat, RAG)   │  đối chiếu, hồ sơ) │ │
                    │  └───────┬───────┴─────────┬──────────┘ │
                    └──────────┼─────────────────┼────────────┘
                               │                 │
                    ┌──────────▼──────┐  ┌───────▼──────────┐
                    │ Qdrant          │  │ MongoDB          │
                    │ vector tri thức │  │ dữ liệu nghiệp vụ│
                    └─────────────────┘  └──────────────────┘
                                   ▲
                    ┌──────────────┴──────────────────────────┐
   Nhân viên ─────► │  admin-frontend/  Hệ thống quản trị      │
   (bắt buộc        │                   (không có chat)       │
    đăng nhập)      └─────────────────────────────────────────┘
```

Hai ứng dụng web chạy độc lập trên hai cổng khác nhau. Ứng viên không bao giờ
chạm tới dữ liệu nội bộ: dữ liệu chỉ đi gián tiếp qua MongoDB, phân hệ quản trị
đọc lên. Đây là ranh giới an toàn quan trọng nhất của kiến trúc.

---

## 2. Ai làm phần nào

| Phần | Thư mục và file | Phụ trách |
|---|---|---|
| Khung chat, giao diện hội thoại | `frontend/components/Chat*`, `frontend/hooks/useChat.ts`, `frontend/lib/api.ts` | Nhóm chatbot |
| Pipeline hội thoại | `backend/app/conversation/`, `app/rag/`, `app/llm/gemini.py`, `app/services/chat_service.py`, `app/api/chat.py` | Nhóm chatbot |
| Thu thập và nạp tri thức vào Qdrant | `backend/ingestion/` | Nhóm chatbot |
| Đơn tuyển dụng, đọc CV, đối chiếu, hồ sơ, hàng đợi, điểm nhân viên | `backend/app/matching/`, `app/db/job_orders.py`, `app/api/job_orders.py`, `app/services/job_order_import.py`, `backend/scripts/` | Phần đồ án này |
| Website khách hàng và luồng tư vấn | `frontend/app/` (trừ các file chat ở trên) | Phần đồ án này |
| Hệ thống quản trị | `admin-frontend/` | Phần đồ án này |
| Đặt lịch, khách hàng, hội thoại, người dùng, nhật ký | có sẵn từ trước, hai bên dùng chung | dùng chung |

Nguyên tắc đang áp dụng: **không bên nào sửa file của bên kia.** Phần nghiệp vụ
không import một dòng nào từ `app/conversation`, `app/rag`, `app/llm`,
`chat_service` hay `ingestion`. Kiểm chứng được bằng một lệnh:

```bash
grep -rn "app\.rag\|app\.conversation\|app\.llm\|chat_service" \
  backend/app/matching backend/app/db/job_orders.py backend/app/api/job_orders.py
```

Có hai tiện ích nhỏ bị lặp lại có chủ ý — hàm bỏ dấu tiếng Việt và hàm lọc giá
trị rỗng. Sáu dòng trùng nhau rẻ hơn nhiều so với một phụ thuộc chéo giữa hai
phần đang được viết song song, vì mỗi lần một bên dọn dẹp là bên kia gãy theo.

---

## 3. Ba điểm hai phần dùng chung

### 3.1. Cấu hình

`backend/app/core/config.py` dùng `pydantic_settings`. Thiếu `GEMINI_API_KEY`
hoặc `JWT_SECRET` thì ứng dụng **chết ngay lúc khởi động** kèm thông báo rõ,
thay vì chạy tiếp rồi lỗi mơ hồ ở request đầu tiên.

Tên thuộc tính giữ nguyên như bản cũ, nên `auth/security.py`, `db/database.py`,
`llm/gemini.py`, `rag/retriever.py` không phải sửa theo. Biến môi trường mới:
`STORAGE_PATH`, `MAX_UPLOAD_MB`, `CV_OCR_MAX_PAGES`, `LLM_EXPLANATIONS_ENABLED`,
`MATCHING_WEIGHTS_PATH`.

Kiểm thử cần đặt sẵn giá trị mặc định, xem `backend/tests/__init__.py`.

### 3.2. Cơ sở dữ liệu

Một MongoDB, tách theo collection. Qdrant **chỉ** lưu vector phục vụ truy xuất
tri thức, không lưu trạng thái xử lý nghiệp vụ.

| Collection | Của phần nào |
|---|---|
| `sessions`, `messages` | chatbot |
| `job_orders`, `job_order_events`, `counters` | nghiệp vụ |
| `managed_leads`, `consultation_appointments`, `staff_users`, `audit_logs` | dùng chung |
| `candidate_profiles`, `documents`, `recruitment_applications`, `consultation_reports`, `employee_score_events` | nghiệp vụ, đang làm |

Index của nghiệp vụ mới **không** khai báo trong `database.py`. Mỗi module dữ
liệu tự khai `ensure_indexes(db)`, `app/db/indexes.py` gọi tất cả trong một lượt,
và `init_db()` gọi đúng một dòng. Thêm nghiệp vụ mới không phải sửa file lõi.

### 3.3. Phiên làm việc

Chatbot định danh người dùng bằng `session_id` dạng UUID, lưu trong
`sessionStorage` với khóa `xkld-chat-state-v1`.

Luồng tư vấn của phần nghiệp vụ **tự sinh mã phiên riêng**, không đọc ké phiên
của chatbot. Lý do: hai bên không phụ thuộc nhau, và bản demo của đồ án không gãy
khi bên kia sửa khung chat. Nếu sau này muốn gộp một phiên, hai bên thống nhất
lại, nhưng đó là việc tùy chọn.

---

## 4. Phần nghiệp vụ cung cấp gì cho chatbot

Các endpoint dưới đây không cần đăng nhập, định danh bằng mã phiên. Khung chat
gọi được ngay nếu muốn hiển thị đơn hàng hoặc mời ứng viên gửi CV.

### Đang chạy

| Method | Đường dẫn | Trả về |
|---|---|---|
| GET | `/public/job-orders` | Danh sách đơn đang tuyển, đã duyệt công khai, còn hạn |
| GET | `/public/job-orders/{code}` | Chi tiết một đơn |
| GET | `/public/job-orders/facets` | Các giá trị lọc thực sự có đơn, để dựng bộ lọc |

Tham số lọc: `prefecture`, `region_group`, `employer_type`, `program`,
`japanese_required`, `limit`.

Một đơn chỉ ra khỏi endpoint công khai khi đồng thời đủ ba điều: đã bật công
khai, đang tuyển, và còn hạn nộp. Lọc ngay lúc truy vấn nên đơn quá hạn tự biến
mất, không cần tác vụ định kỳ.

Bản trả về đã loại sẵn trường nội bộ (`internal_note`, `created_by`,
`updated_by`, `hired_count`) ở tầng truy vấn, không dựa vào việc tầng trên nhớ bỏ đi.

Mỗi đơn kèm khối `labels` chứa nhãn tiếng Việt (trạng thái, loại hình cơ sở,
chương trình, vùng, trình độ tiếng Nhật, bằng cấp, giới tính). Giao diện dùng
thẳng nhãn đó, **không tự chép bảng danh mục**, vì giữ bảng ở hai nơi là cách
chắc chắn nhất để chúng lệch nhau sau vài lần sửa.

```jsonc
// GET /public/job-orders?prefecture=Tokyo
[
  {
    "code": "DH-0001",
    "title": "Điều dưỡng viện dưỡng lão Tokyo",
    "employer_name": "Viện dưỡng lão Sakura",
    "employer_type": "vien_duong_lao",
    "program": "tokutei_ginou",
    "prefecture": "Tokyo",
    "region_group": "kanto",
    "quota": 5,
    "deadline": "2026-11-30",
    "requirements": {
      "japanese_required": "N4",
      "education_required": "cao_dang",
      "experience_min": 0.0,
      "age_min": 20, "age_max": 35,
      "gender_pref": "khong_yeu_cau"
    },
    "reference": {
      "salary_min": 195000, "salary_max": 215000,
      "allowances": ["Hỗ trợ ký túc xá", "Phụ cấp ca đêm"],
      "cost_total_vnd": 110000000,
      "interview_date": "2026-10-13",
      "departure_expected": "2027-03",
      "highlights": ["Cơ sở mới xây, trang thiết bị hiện đại"]
    },
    "labels": {
      "status": "Đang tuyển",
      "employer_type": "Viện dưỡng lão",
      "program": "Kỹ năng đặc định (Tokutei Ginou)",
      "region_group": "Kantō",
      "japanese_required": "N4",
      "education_required": "Cao đẳng",
      "gender_pref": "Không yêu cầu"
    }
  }
]
```

### Luồng ứng viên — cũng đã chạy

Bảng này trước đây ghi là "sẽ có". Cả năm phần đều đã dựng xong, và **đường dẫn
thật khác với bản dự kiến cũ**: mọi endpoint đều mang mã phiên trên đường dẫn,
không có bản không tham số. Viết theo bảng cũ là gọi vào 404.

| Method | Đường dẫn | Mục đích |
|---|---|---|
| GET | `/public/profiles/meta` | Danh mục cho biểu mẫu: mức tiếng Nhật, bằng cấp, 47 tỉnh, vùng |
| POST | `/public/profiles` | Tạo hồ sơ, `session_id` nằm trong thân yêu cầu |
| GET/PATCH | `/public/profiles/{session_id}` | Xem và sửa hồ sơ |
| POST | `/public/profiles/{session_id}/confirm` | Ứng viên xác nhận hồ sơ đúng |
| POST | `/public/documents/{session_id}` | Gửi CV (multipart, khóa `file`), trả về ngay, xử lý nền |
| GET | `/public/documents/{session_id}` | Theo dõi tiến trình đọc CV của phiên |
| GET | `/public/matches/{session_id}` | Đơn phù hợp kèm lý do từng tiêu chí |
| GET | `/public/matches/{session_id}/orders/{code}` | Lý do chi tiết cho đúng một đơn |
| POST | `/public/registrations/{session_id}` | Ứng viên chọn đơn, tạo đăng ký sơ bộ |
| GET | `/public/registrations/{session_id}` | Ứng viên xem lại mình đã đăng ký đơn nào |

Hai chốt chặn không đi vòng được: `/public/matches` trả **409** nếu hồ sơ chưa
xác nhận, và `/public/registrations` chỉ nhận đơn nằm trong danh sách vừa được
giới thiệu cho chính phiên đó. Cả hai là để không có đăng ký nào sinh ra từ suy
đoán của mô hình.

---

## 5. Phần nghiệp vụ cần gì từ chatbot

Màn hình **Tri thức AI** trong hệ thống quản trị hiện đang hiển thị số liệu cố
định viết cứng trong mã nguồn. Để thay bằng dữ liệu thật, cần từ phía chatbot:

| Method | Đường dẫn đề xuất | Trả về |
|---|---|---|
| GET | `/knowledge/documents` | Danh sách tài liệu kèm trạng thái vector, số đoạn, lần cập nhật cuối |
| GET | `/knowledge/stats` | Tổng số tài liệu, số đã lập chỉ mục, số lỗi, phân bố theo chủ đề |
| POST | `/knowledge/documents` | Tải tài liệu lên, xử lý nền |
| POST | `/knowledge/documents/{id}/reindex` | Lập chỉ mục lại |
| DELETE | `/knowledge/documents/{id}` | Xóa tài liệu và các điểm vector tương ứng |

Quy ước chung nếu làm: dùng `get_current_user` và `require_roles` sẵn có trong
`app/auth/security.py`; ghi nhật ký bằng `audit_action`; khai index qua
`app/db/indexes.py`; file lưu trong `storage/kb/`.

Hai thứ **đề nghị giữ nguyên** vì phần nghiệp vụ đang dựa vào:

- Trường `intent` trên collection `messages`. Phiếu tóm tắt tư vấn dùng nó để
  thống kê ứng viên đã hỏi về những chủ đề nào.
- Khóa `url` trong payload nguồn trả về cho khung chat. Giao diện đang đọc
  `sources[].url`; đổi tên khóa sẽ làm mất liên kết nguồn.

---

## 6. Chạy dự án

```bash
# 1. MongoDB: khởi động service của máy

# 2. Qdrant
docker start qdrant     # lần đầu xem README

# 3. Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py                             # http://localhost:8020

# 4. Nạp đơn tuyển dụng mẫu
python -m scripts.seed_job_orders --reset  # 19 đơn, 16 đơn công khai

# 5. Website khách hàng
cd frontend && npm ci && npm run dev       # http://localhost:3100

# 6. Hệ thống quản trị
cd admin-frontend && npm ci && npm run dev # http://localhost:3101
```

**Lưu ý về cổng.** Dự án dùng bộ cổng riêng để không đụng ứng dụng khác trên
máy: backend `8020`, website `3100`, hệ thống quản trị `3101`. Cổng backend đọc từ
`API_PORT` trong `backend/.env`, nên `python main.py` là đủ, không cần nhớ tham số
dòng lệnh.

Hai ứng dụng web đọc địa chỉ backend từ `NEXT_PUBLIC_BACKEND_URL`. Đổi cổng backend
mà quên sửa hai file `.env.local` thì màn hình sẽ trắng dữ liệu mà không báo lỗi gì
rõ ràng — đây là lỗi hay gặp nhất khi hai người cùng chạy dự án trên hai máy.

Cổng của hai app Next đặt bằng `-p` trong `package.json`. Muốn đổi tạm thì chạy
`npm run dev -- -p 4000`; viết `PORT` vào `.env.local` không có tác dụng vì Next
chọn cổng trước khi nạp file `.env`.

**Kiểm thử.**

```bash
cd backend
.\venv\Scripts\python.exe -m unittest discover -s tests -t .
```

Tham số `-t .` là bắt buộc, đừng bỏ. Thiếu nó thì Python nạp các file kiểm thử
như module rời chứ không như một gói, nên `tests/__init__.py` không chạy và các
giá trị cấu hình mặc định dành cho kiểm thử không được đặt. Trên máy đã có `.env`
thì vẫn chạy được nên lỗi này dễ bị bỏ qua; trên máy vừa clone repo về thì toàn
bộ bộ kiểm thử đổ lỗi nạp module.

---

## 7. Tài liệu liên quan

| File | Nội dung |
|---|---|
| `docs/SCOPE_PHAT_TRIEN.md` | Phạm vi công việc: làm gì, không làm gì, tiến độ |
| `docs/design/11_KIEN_TRUC_TONG_QUAN.md` | Kiến trúc bốn khối trên ba mặt phẳng tin cậy |
| `docs/design/12_YEU_CAU_HE_THONG.md` | Yêu cầu chức năng nhóm A đến F |
| `docs/design/13_PHAM_VI_VA_TRANG_THAI.md` | Thứ tự triển khai, không đảo được |
| `tailieu/DonHang/HUONG_DAN.md` | Hướng dẫn doanh nghiệp nhập đơn hàng bằng Excel |
