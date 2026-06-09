from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.chat import router as chat_router

app = FastAPI(title="XKLD Chatbot XKLD Dieu Duong")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)

@app.get
def read_root():
    return {"message": "Chatbot XKLD Dieu duong dang hoat dong!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
