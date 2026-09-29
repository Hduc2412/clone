"""Cấu hình ứng dụng, đọc từ biến môi trường và file .env.

Dùng `pydantic_settings` thay cho dataclass thuần để cấu hình được kiểm tra ngay
lúc khởi động. Thiếu `GEMINI_API_KEY` hoặc `JWT_SECRET` thì ứng dụng phải chết
ngay với thông báo rõ ràng, thay vì chạy tiếp rồi lỗi mơ hồ ở request đầu tiên —
lúc đó rất khó lần ngược về nguyên nhân thật.

Tên thuộc tính giữ nguyên như bản cũ để các module đang dùng (`auth/security.py`,
`db/database.py`, `llm/gemini.py`, `rag/retriever.py`) không phải sửa theo.
"""
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Bắt buộc: thiếu là không khởi động được ---
    gemini_api_key: str = Field(min_length=20)
    jwt_secret: str = Field(min_length=32)

    # --- Mô hình ngôn ngữ ---
    gemini_model: str = "gemini-2.5-flash"
    # Model riêng cho các tác vụ trả về JSON có schema (trích xuất CV, diễn giải
    # kết quả đối chiếu). Tách biến để đổi model cho nhánh này mà không đụng chat.
    gemini_json_model: str = "gemini-2.5-flash"
    gemini_timeout_seconds: float = 60.0
    embedding_model: str = "gemini-embedding-001"

    # --- Engine tư vấn (app/advisor) ---
    # Hệ tư vấn là hệ **chính** của đề tài; khung chat hỏi đáp là phần phụ trợ.
    # Hai bên chạy độc lập tới mức nào thì khai ở đây.
    #
    # Khóa riêng là điểm quan trọng nhất trong nhóm này. Dùng chung khóa nghĩa là
    # dùng chung hạn mức: khách hỏi chat nhiều tới mức hết hạn mức thì phần tư
    # vấn chết theo, dù hai nhánh code không liên quan gì nhau. Mà tư vấn mới là
    # thứ không được chết — nó đang trả lời câu "tôi có đi được không".
    #
    # Để trống thì dùng lại `gemini_api_key`, và `advisor/client.py` ghi một dòng
    # cảnh báo lúc khởi động để không ai quên mất mình đang dùng chung.
    advisor_api_key: str = ""
    advisor_model: str = "gemini-2.5-flash"
    # Ngắn hơn hẳn hạn chờ của chat. Đây là phần diễn đạt lại một khối chữ đã có
    # sẵn — chờ lâu thì thà hiện bản ghép sẵn còn hơn để ứng viên nhìn màn hình
    # quay vòng.
    advisor_timeout_seconds: float = 12.0
    # Tắt thì toàn hệ tư vấn chạy bằng bản ghép sẵn. Điểm số và kết luận không
    # đổi một ly, vì chúng chưa bao giờ do mô hình tính.
    advisor_enabled: bool = True

    # --- Dữ liệu ---
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "xkld_chatbot"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "xkld_knowledge"
    # Sàn tuyệt đối cho đoạn hợp nhất. Xem `app/rag/retriever.py` để biết con số
    # này chọn theo phép đo nào, và vì sao nó không thể làm hết việc.
    min_retrieval_score: float = 0.65

    # Số hotline công ty. Trước đây hard-code ở 4 nơi (validator, prompt, chat
    # service); đổi số mà sót một chỗ là chatbot đọc sai số cho khách.
    #
    # Giá trị mặc định ở đây là số GIẢ, có chủ ý. Kho mã này công khai, và số
    # hotline thật là số của một người thật — commit nó vào lịch sử git thì xóa
    # đi rất khó, mà crawler thu số điện thoại thì đọc GitHub trước cả website.
    # Số thật khai trong `backend/.env`, tệp ấy không vào kho.
    #
    # Hệ quả cần biết: máy nào chưa khai `SUPPORT_PHONE` thì chatbot sẽ đọc số
    # giả này cho khách. Thà vậy hơn là lặng lẽ đọc số thật của người khác.
    support_phone: str = "0000.000.000"

    # --- Xác thực ---
    jwt_expire_minutes: int = 480
    auth_cookie_name: str = "xkld_admin_session"
    auth_cookie_secure: bool = False
    # Mật khẩu mặc định khi cấp tài khoản hoặc đặt lại mật khẩu, cho cả ứng viên
    # lẫn nhân viên. Đây là một dãy **ai cũng biết**, nên nó chỉ an toàn nhờ hai
    # điều đi kèm, và cả hai đều bắt buộc: tài khoản bị chặn ngay sau khi đăng
    # nhập cho tới khi tự đặt mật khẩu mới, và mọi trang khác không mở được
    # trước đó. Bỏ một trong hai là để ngỏ mọi tài khoản vừa được cấp.
    default_password: str = "12345678"
    # Dãy mặc định chỉ sống trong ngần này giờ. Hết hạn thì tài khoản vẫn còn
    # nguyên, chỉ là dãy cũ không đăng nhập được nữa và phải xin cấp lại.
    #
    # Thứ này bịt lỗ mà `must_change_password` không bịt được: cờ đó bắt người
    # đăng nhập phải đổi mật khẩu, nhưng **không xác minh được người đăng nhập
    # là ai**. Ai biết số điện thoại cũng gõ đúng dãy mặc định, và nếu họ vào
    # trước chủ tài khoản thì họ là người đặt mật khẩu mới. Không có hạn dùng
    # thì cửa đó mở vô thời hạn kể từ lúc nhân viên cấp tài khoản.
    #
    # Bảy hai giờ là ba ngày làm việc — đủ rộng cho một cuộc gọi lỡ và một ngày
    # nghỉ, đủ hẹp để không còn là cửa mở thường trực.
    default_password_hours: int = 72
    # Cookie riêng cho hệ khách hàng. Phải khác tên cookie của nhân viên: dùng
    # chung một tên thì đăng nhập bên này đá văng phiên bên kia, và tệ hơn là
    # một token có thể bị đem thử ở nhầm cửa.
    candidate_cookie_name: str = "xkld_candidate_session"
    # Ngắn hơn phiên nhân viên. Ứng viên đăng nhập trên máy mượn hoặc điện thoại
    # chung là chuyện thường, nên để phiên tự hết hạn sớm.
    candidate_session_minutes: int = 240
    # Cookie thứ ba, cho luồng tư vấn công khai chưa đăng nhập. Phải khác hai
    # tên trên: nó chứng minh một thứ yếu hơn hẳn — "vẫn là trình duyệt đã mở
    # phiên này" — nên không được nhầm lẫn với phiên đã xác thực bằng mật khẩu.
    journey_cookie_name: str = "xkld_journey"
    initial_admin_email: str = ""
    initial_admin_name: str = "Quản trị viên"
    initial_admin_password_hash: str = ""

    # --- Lưu trữ file ứng viên ---
    storage_path: Path = BACKEND_DIR / "storage"
    max_upload_mb: int = 10
    # Số trang tối đa đem đi nhận dạng chữ khi CV là bản scan. Giới hạn để một
    # hồ sơ dài không đốt hết hạn mức gọi mô hình.
    cv_ocr_max_pages: int = 5

    # --- Đối chiếu đơn hàng ---
    # Tắt cờ này thì phần diễn giải bằng mô hình ngôn ngữ bị bỏ qua và hệ thống
    # dùng câu ghép sẵn. Điểm số không đổi vì điểm do quy tắc tính, không do mô hình.
    llm_explanations_enabled: bool = True
    matching_weights_path: Path | None = None
    score_rules_path: Path | None = None

    # --- Web ---
    # Cổng 8020 thay vì 8000 mặc định của uvicorn, để không đụng ứng dụng khác
    # trên máy phát triển. Đổi số ở đây thì phải đổi kèm NEXT_PUBLIC_BACKEND_URL
    # của cả hai frontend, nếu không trình duyệt vẫn gọi vào cổng cũ.
    api_host: str = "127.0.0.1"
    api_port: int = 8020

    cors_origins: Annotated[tuple[str, ...], NoDecode] = (
        "http://localhost:3100",
        "http://localhost:3101",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Nhận chuỗi phân tách bằng dấu phẩy thay vì bắt người dùng viết JSON."""
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split(",") if item.strip())
        return value

    @field_validator("initial_admin_email", mode="before")
    @classmethod
    def _normalize_admin_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def cv_storage_path(self) -> Path:
        return self.storage_path / "cv"


settings = Settings()
