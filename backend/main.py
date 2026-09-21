from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.chat import router as chat_router
from app.api.analytics import router as analytics_router
from app.api.appointments import appointment_router, notification_router
from app.api.management import router as management_router
from app.api.auth import router as auth_router
from app.api.audit import router as audit_router
from app.api.applications import router as application_router
from app.api.customer_journey import router as customer_journey_router
from app.api.documents import public_router as public_document_router
from app.api.documents import router as document_router
from app.api.job_orders import public_router as public_job_order_router
from app.api.job_orders import router as job_order_router
from app.api.matching import public_router as public_match_router
from app.api.matching import router as recommendation_log_router
from app.api.profiles import public_router as public_profile_router
from app.api.profiles import router as profile_router
from app.api.registrations import public_router as public_registration_router
from app.api.registrations import router as registration_router
from app.api.staff_scores import router as staff_score_router
from app.api.candidate_auth import router as candidate_auth_router
from app.api.portal import router as portal_router
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
app.include_router(application_router)
app.include_router(customer_journey_router)
app.include_router(public_job_order_router)
app.include_router(job_order_router)
app.include_router(public_profile_router)
app.include_router(profile_router)
app.include_router(public_match_router)
app.include_router(recommendation_log_router)
app.include_router(public_document_router)
app.include_router(document_router)
app.include_router(public_registration_router)
app.include_router(registration_router)
app.include_router(staff_score_router)
# Hệ khách hàng. Đăng nhập trước, rồi mới tới các trang xem hồ sơ của chính mình.
app.include_router(candidate_auth_router)
app.include_router(portal_router)

@app.get("/")
def read_root():
    return {"message": "Chatbot XKLD Dieu duong dang hoat dong!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    # Chạy bằng `python main.py` thì cổng lấy từ API_PORT trong .env, nên đổi cổng
    # không phải sửa lệnh chạy ở từng chỗ. Cách cũ vẫn dùng được và vẫn thắng:
    # `python -m uvicorn main:app --reload --port 8020`.
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
