# 🏥 Chatbot AI Tư Vấn XKLĐ Điều Dưỡng

Hệ thống chatbot AI tự động tư vấn xuất khẩu lao động điều dưỡng sang Nhật Bản cho website xklddieuduong.vn

## 🚀 Tech Stack

- **Backend:** Python 3.14 + FastAPI + Uvicorn
- **AI:** Gemini 2.5 Flash API (Google)
- **Crawling:** Requests + BeautifulSoup4
- **Frontend:** Next.js 14 + TypeScript + Tailwind CSS (coming soon)

## 📁 Cấu Trúc

```
xkld-chatbot/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── gemini_service.py    # Xử lý AI
│   ├── crawler.py           # Crawl website
│   ├── image_reader.py      # Đọc ảnh Gemini Vision
│   └── requirements.txt
└── frontend/                # Coming soon
```

## ⚙️ Cài Đặt

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Tạo file `.env`:

```
GEMINI_API_KEY=your_api_key_here
```

Chạy server:

```bash
uvicorn main:app --reload --port 8000
```

## 📡 API

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | / | Kiểm tra server |
| GET | /health | Health check |
| POST | /chat | Chat với bot |

## 📞 Liên hệ

**DC Trung Tâm Học** — 0971.716.939