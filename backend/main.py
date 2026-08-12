from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.chat import router as chat_router
from app.api.analytics import router as analytics_router
from app.api.appointments import appointment_router, notification_router
from app.api.management import router as management_router
from app.api.auth import router as auth_router
from app.api.audit import router as audit_router
from app.db.database import close_db, init_db
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="XKLD Chatbot XKLD Dieu Duong", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)

app.include_router(chat_router)
app.include_router(analytics_router)
app.include_router(appointment_router)
app.include_router(notification_router)
app.include_router(management_router)
app.include_router(auth_router)
app.include_router(audit_router)

@app.get("/")
def read_root():
    return {"message": "Chatbot XKLD Dieu duong dang hoat dong!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
