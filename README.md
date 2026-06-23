# Chatbot AI Tư Vấn XKLĐ Điều Dưỡng Nhật Bản

Chatbot tư vấn tự động cho chương trình xuất khẩu lao động điều dưỡng Nhật Bản, tích hợp RAG (Retrieval-Augmented Generation) với dữ liệu từ website xklddieuduong.vn.

## Stack

- **Backend:** Python 3.14 + FastAPI
- **LLM:** Gemini 2.5 Flash
- **Vector DB:** Qdrant
- **Database:** MongoDB (motor async driver)
- **Frontend:** Next.js 14 + TypeScript + Tailwind CSS

## Cấu trúc project
XKLD-CHATBOT/
├── backend/
│   ├── app/
│   │   ├── api/          # Chat + Analytics endpoints
│   │   ├── conversation/ # Session, Intent, Validator, Entity Extractor
│   │   ├── db/           # MongoDB + Qdrant
│   │   ├── lead/         # Lead Capture Service
│   │   ├── llm/          # Gemini integration
│   │   ├── rag/          # Retriever + Prompt Builder
│   │   └── services/     # Chat Service, Analytics Service
│   ├── ingestion/        # Crawler + Embedder
│   └── main.py
└── frontend/
    ├── app/
    │   ├── chat/
    │   │   └── page.tsx  # Trang chat toàn màn hình
    │   ├── globals.css
    │   ├── layout.tsx
    │   └── page.tsx      # Trang chủ nhúng widget
    ├── components/
    │   ├── ChatWidget.tsx # Nút + container widget góc màn hình
    │   ├── ChatWindow.tsx # Cửa sổ chat nhỏ trong widget
    │   └── ChatPage.tsx   # Component chat toàn màn hình
    └── lib/
        └── api.ts         # Hàm gọi API backend
## Tính năng

- Trả lời câu hỏi về chi phí, quy trình, đơn hàng điều dưỡng Nhật Bản
- Tự động capture lead (tên + SĐT) trong luồng tư vấn
- Widget chat nhúng góc màn hình + trang chat riêng
- Analytics: thống kê sessions, intents, leads, fallback rate
- Retry logic khi Gemini API quá tải

## Chạy local

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Endpoints
- Chat: `POST /chat`
- Analytics: `GET /analytics/overview|today|intents|fallbacks|leads`
- Docs: `http://localhost:8000/docs`

## Trạng thái

| Hạng mục | Trạng thái |
|---|---|
| RAG + Qdrant + Chat API | ✅ Xong |
| Session Manager + Intent Classifier | ✅ Xong |
| MongoDB + Lead Capture | ✅ Xong |
| Analytics Service | ✅ Xong |
| Frontend Next.js | ✅ Xong |
| Zalo Bot Webhook | ⏳ Chưa làm |
| Human Handoff | ⏳ Chưa làm |