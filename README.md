# Chatbot tư vấn XKLĐ điều dưỡng Nhật Bản

Chatbot tư vấn chương trình xuất khẩu lao động điều dưỡng Nhật Bản. Hệ thống
sử dụng RAG để tìm nội dung đã thu thập từ `xklddieuduong.vn`, Gemini để tạo
câu trả lời, MongoDB để lưu hội thoại/lead và Qdrant để lưu vector.

## Thành phần

- Backend: Python, FastAPI, Gemini 2.5 Flash.
- Vector database: Qdrant.
- Database: MongoDB.
- Frontend: Next.js 14, TypeScript, Tailwind CSS.
- Docker volume trên máy bàn giao hiện có 32 bài, đủ nội dung chữ đọc từ ảnh.

Zalo, hệ thống quản lý, đăng nhập và triển khai production chưa nằm trong phạm
vi hiện tại. Trang `/` mới là trang mẫu chứa widget, chưa phải giao diện website
thật.

## Cấu trúc chính

```text
xkld-chatbot/
├── backend/
│   ├── app/
│   │   ├── api/            # Chat và Analytics API
│   │   ├── conversation/   # Session, intent, entity, validator
│   │   ├── db/             # MongoDB và Qdrant
│   │   ├── lead/           # Thu thập tên, số điện thoại
│   │   ├── llm/            # Gemini
│   │   ├── rag/            # Taxonomy, truy xuất, prompt
│   │   └── services/       # Điều phối nghiệp vụ
│   ├── ingestion/          # Crawl, Vision, embedding
│   ├── tests/              # Kiểm thử backend
│   ├── check_qdrant.py     # Kiểm tra dữ liệu Qdrant
│   └── main.py
└── frontend/
    ├── app/                # Trang chủ và trang chat
    ├── components/         # Giao diện tin nhắn/widget
    ├── hooks/              # Logic và trạng thái chat
    └── lib/api.ts          # Kết nối backend
```

## Yêu cầu

- Python 3.11 trở lên (môi trường hiện tại dùng Python 3.14).
- Node.js và npm.
- MongoDB chạy tại máy cá nhân.
- Docker Desktop để chạy Qdrant.
- Gemini API key.

## Cấu hình

Tạo file `backend/.env` từ `backend/.env.example`:

```env
GEMINI_API_KEY=your_gemini_api_key
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=xkld_chatbot
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=xkld_knowledge
MIN_RETRIEVAL_SCORE=0.65
```

Không commit file `.env` hoặc đưa API key vào mã nguồn.

Frontend mặc định gọi `http://localhost:8000`. Nếu backend dùng địa chỉ khác,
tạo `frontend/.env.local`:

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

## Chạy trên máy cá nhân

### 1. MongoDB

Khởi động MongoDB service của máy.

### 2. Qdrant

Tạo lần đầu:

```powershell
docker run -d --name qdrant `
  -p 6333:6333 -p 6334:6334 `
  -v qdrant_storage:/qdrant/storage `
  qdrant/qdrant
```

Những lần sau:

```powershell
docker start qdrant
```

Qdrant lưu vector trong Docker volume, không lưu trong Git. Vì vậy máy mới
clone repo sẽ có source code và cache Vision nhưng chưa có collection vector.

### 3. Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Backend chạy tại `http://localhost:8000`; tài liệu API ở
`http://localhost:8000/docs`.

### 4. Frontend

Mở terminal khác:

```powershell
cd frontend
npm ci
npm run dev
```

Frontend chạy tại `http://localhost:3000`.

## API chính

- `POST /chat`: gửi câu hỏi.
- `GET /chat/session/{session_id}`: xem thông tin phiên.
- `DELETE /chat/session/{session_id}`: xóa dữ liệu phiên.
- `GET /analytics/overview`: thống kê tổng quan.
- `GET /analytics/today`: thống kê trong ngày.
- `GET /analytics/intents`: phân bố intent.
- `GET /analytics/fallbacks`: tỷ lệ fallback.
- `GET /analytics/leads`: danh sách lead gần nhất.

## Kiểm thử

Backend:

```powershell
cd backend
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

Frontend:

```powershell
cd frontend
npm run build
```

Kiểm tra collection đang dùng:

```powershell
cd backend
.\venv\Scripts\python.exe check_qdrant.py `
  --collection xkld_knowledge `
  --require-image-content `
  --require-complete-images
```

Kết quả hợp lệ phải có 32 URL, 32 tiêu đề, không thiếu nội dung ảnh và báo
`KẾT QUẢ: PASS`.

## Collection Qdrant

Các tên dưới đây mô tả trạng thái trong Docker volume của máy bàn giao hiện
tại; chúng không tự xuất hiện khi clone Git sang máy mới.

- `xkld_knowledge`: alias ứng dụng sử dụng.
- `xkld_knowledge_v20260730`: version dữ liệu đã nghiệm thu, 32 bài.
- `xkld_knowledge_backup_20260730`: bản cũ để khôi phục, 31 bài.
- `xkld_knowledge_staging`: vùng build và kiểm thử dữ liệu lần sau.

Không đặt `QDRANT_BUILD_COLLECTION_NAME` trùng với collection chính.

### Chạy lại ingestion an toàn

Pipeline mặc định ghi vào staging và tiếp tục từ cache:

```powershell
cd backend
$env:QDRANT_COLLECTION_NAME="xkld_knowledge"
$env:QDRANT_BUILD_COLLECTION_NAME="xkld_knowledge_staging"
$env:RESET_BUILD_COLLECTION="false"
.\venv\Scripts\python.exe -m ingestion.embedder
```

`backend/data/image_vision_cache.json` chứa kết quả Vision đã đọc để giảm số
lần gọi Gemini miễn phí. File không chứa API key. Máy mới vẫn phải tạo
embedding và ghi vector vào Qdrant.

Sau khi ingestion trên máy mới hoàn tất, kiểm tra staging:

```powershell
.\venv\Scripts\python.exe check_qdrant.py `
  --collection xkld_knowledge_staging `
  --require-image-content `
  --require-complete-images
```

Để chạy thử trực tiếp với staging trên máy mới, đặt trong `backend/.env`:

```env
QDRANT_COLLECTION_NAME=xkld_knowledge_staging
```

Chỉ tạo hoặc chuyển alias chính sau khi đã kiểm thử hội thoại và tạo backup.

### Khôi phục bản cũ

Nếu version mới có vấn đề, dừng backend rồi đổi alias
`xkld_knowledge` từ `xkld_knowledge_v20260730` về
`xkld_knowledge_backup_20260730` trong Qdrant. Luôn chạy lại
`check_qdrant.py` và một câu hỏi thử trước khi mở backend.

## Lưu ý vận hành gói miễn phí

- Gemini có thể trả `429` khi có nhiều yêu cầu. Chatbot sẽ báo người dùng thử
  lại sau thay vì chờ nhiều phút.
- Kết quả truy xuất dưới `0.65` bị loại.
- API trả tối đa ba nguồn; nguồn có điểm cao nhất được đánh dấu là nguồn chính.
- Lịch sử đưa vào prompt giới hạn 3.000 ký tự để tiết kiệm hạn mức.
- Chỉ chuyển staging sang chính sau khi kiểm thử và đã tạo backup.
- API Analytics hiện chưa có xác thực, chỉ nên dùng trên máy cá nhân.
- CORS backend hiện cho phép mọi origin để phát triển local; phải giới hạn lại
  trước khi public.
- Không chạy nhiều tiến trình ingestion cùng lúc.
