from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.chat import router as chat_router
from app.api.analytics import router as analytics_router
from app.db.database import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="XKLD Chatbot XKLD Dieu Duong", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(analytics_router)

@app.get("/")
def read_root():
    return {"message": "Chatbot XKLD Dieu duong dang hoat dong!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
