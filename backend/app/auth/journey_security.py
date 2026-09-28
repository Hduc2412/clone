"""Quyền truy cập cho luồng tư vấn công khai — không đăng nhập, nhưng có chứng minh.

## Lỗ hổng mà module này vá

Trước ngày 22/09/2026, bảy đường `/public/*` nhận diện người dùng bằng **đúng
mã phiên trên URL**, không có gì khác. Không cookie, không token, không kiểm gì
ngoài hình dạng chuỗi. `docs` của `app/core/session_id.py` nói thẳng điều đó:
*"mã phiên chính là mật khẩu của hồ sơ ấy"*.

Nhưng một mật khẩu thì không bao giờ được đặt trên đường dẫn URL. Mã phiên nằm
trên URL sẽ lọt vào access log của máy chủ, vào header `Referer` gửi sang mọi
trang bên ngoài mà người dùng bấm vào, và vào lịch sử trình duyệt — ba nơi mà
không ai coi là chỗ giữ bí mật. Ai nhặt được chuỗi ấy thì đọc được họ tên, số
điện thoại, câu trích nguyên văn từ CV và hai mươi tin nhắn gần nhất của người
khác, đồng thời **sửa** được hồ sơ ấy và xác nhận hộ.

Nặng hơn nữa: máy chủ chỉ kiểm hình dạng, không kiểm tính ngẫu nhiên. Chuỗi
`"a" * 32` là một mã phiên hợp lệ.

## Cách vá, và vì sao phải là cách này

Điều kiện ràng buộc: khách vãng lai **không được bắt đăng nhập**. Người ta vào
hỏi vài câu về chi phí, chưa có lý do gì để lập tài khoản.

Giải pháp: máy chủ phát một cookie `httponly` đã ký, gắn với mã phiên. Trình
duyệt tự gửi kèm mọi yêu cầu; JavaScript của trang không đọc được nó; và vì nó
đi trong header chứ không trên URL nên không lọt vào log hay `Referer`.

**Điểm mấu chốt: mã phiên do máy chủ sinh, không nhận từ client.** Nếu cho phép
client gửi lên một mã rồi cấp cookie cho mã đó, thì kẻ tấn công chỉ việc gửi mã
của nạn nhân và tự nhận được cookie hợp lệ — vá xong vẫn thủng y như cũ. Đây là
chỗ dễ làm sai nhất trong cả thiết kế này.

Hệ quả phải chấp nhận: **mọi phiên đang mở sẽ mất quyền đọc hồ sơ cũ** cho tới
khi người dùng quay lại và nhận mã mới. Với dữ liệu thật thì đây là một cuộc di
trú cần báo trước; ở giai đoạn này dữ liệu chỉ là hồ sơ thử nghiệm.

## Cái này không phải là gì

Cookie ký chứng minh **"vẫn là trình duyệt đã bắt đầu phiên này"**, không chứng
minh **"đúng người ấy"**. Ai mượn được máy, hay lấy được cookie, thì vẫn vào
được. Muốn chắc hơn phải đăng nhập — và đó đúng là thứ hệ khách hàng
(`candidate_security.py`) đang làm cho phần hồ sơ đã bàn giao cho nhân viên.
Ranh giới là có chủ ý: phần công khai đủ an toàn cho dữ liệu mới nhập, phần đã
thành hồ sơ chính thức thì đòi mật khẩu.
"""
import hashlib
import hmac
import json
import secrets
import time
import uuid
from typing import Any

from fastapi import Cookie, HTTPException, Path, Response

from app.auth.security import _b64decode, _b64encode, _secret
from app.core.config import settings
from app.core.session_id import SESSION_PATTERN


TOKEN_TYPE = "journey"

# Hành trình tư vấn kéo dài nhiều ngày: gửi CV hôm nay, xem lại và xác nhận hôm
# sau, bàn với gia đình rồi mới đăng ký. Hạn ngắn sẽ đá người ta ra giữa chừng
# và họ mất luôn hồ sơ đã khai — không có cách nào lấy lại vì không có tài khoản.
TOKEN_DAYS = 30


def new_session_id() -> str:
    """Mã phiên mới, do máy chủ sinh.

    `uuid4` lấy entropy từ nguồn ngẫu nhiên của hệ điều hành. Không dùng mã
    client gửi lên: xem phần "Điểm mấu chốt" ở đầu tệp.
    """
    return str(uuid.uuid4())


def create_journey_token(session_id: str) -> str:
    now = int(time.time())
    payload = {
        "sid": session_id,
        "typ": TOKEN_TYPE,
        "iat": now,
        "exp": now + TOKEN_DAYS * 24 * 3600,
        # Làm mỗi token khác nhau kể cả khi cấp lại trong cùng một giây.
        "jti": secrets.token_urlsafe(8),
    }
    encoded = _b64encode(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    )
    signature = _b64encode(hmac.new(_secret(), encoded.encode(), hashlib.sha256).digest())
    return f"{encoded}.{signature}"


def read_journey_token(token: str) -> dict[str, Any] | None:
    """Giải mã và kiểm chữ ký. Trả `None` nếu token không dùng được.

    Không ném lỗi: nơi gọi cần phân biệt "không có cookie" với "cookie hỏng"
    theo cách riêng của nó, và cả hai đều dẫn tới cùng một việc — cấp phiên mới.
    """
    if not token or "." not in token:
        return None
    try:
        encoded, signature = token.rsplit(".", 1)
        expected = _b64encode(
            hmac.new(_secret(), encoded.encode(), hashlib.sha256).digest()
        )
        # `compare_digest` để thời gian so sánh không phụ thuộc vào chỗ lệch đầu
        # tiên — nếu không, đo thời gian phản hồi có thể dò dần ra chữ ký đúng.
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(_b64decode(encoded))
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    if payload.get("typ") != TOKEN_TYPE:
        return None
    if int(payload.get("exp", 0)) <= int(time.time()):
        return None
    sid = payload.get("sid")
    if not isinstance(sid, str) or not sid:
        return None
    return payload


def attach_cookie(response: Response, session_id: str) -> None:
    """Gắn cookie phiên vào phản hồi.

    `httponly` để JavaScript của trang không đọc được — kể cả khi trang dính một
    đoạn mã lạ. `samesite="lax"` để cookie không bị gửi kèm trong yêu cầu ghi
    phát sinh từ trang khác.
    """
    response.set_cookie(
        key=settings.journey_cookie_name,
        value=create_journey_token(session_id),
        max_age=TOKEN_DAYS * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.auth_cookie_secure,
        path="/",
    )


def session_from_cookie(token: str | None) -> str | None:
    payload = read_journey_token(token or "")
    return payload["sid"] if payload else None


async def require_journey_session(
    session_id: str = Path(..., pattern=SESSION_PATTERN),
    token: str | None = Cookie(default=None, alias=settings.journey_cookie_name),
) -> str:
    """Chặn cửa cho mọi đường `/public/*` có mã phiên trên URL.

    Hai điều kiện, và điều kiện thứ hai mới là cái quan trọng: cookie phải hợp
    lệ, **và** mã phiên trong cookie phải đúng bằng mã phiên trên URL. Thiếu vế
    sau thì bất kỳ ai có một cookie hợp lệ của chính họ cũng đọc được hồ sơ của
    người khác chỉ bằng cách đổi mã trên URL.
    """
    cookie_session = session_from_cookie(token)
    if cookie_session is None:
        raise HTTPException(
            status_code=401,
            detail="Phiên tư vấn đã hết hạn hoặc chưa được mở. Bạn tải lại trang nhé.",
        )
    # So bằng `compare_digest` cho nhất quán với phần kiểm chữ ký; ở đây cả hai
    # vế đều là mã phiên nên rò rỉ qua thời gian không đáng kể, nhưng không có
    # lý do gì để so theo cách yếu hơn.
    if not hmac.compare_digest(cookie_session, session_id):
        raise HTTPException(
            status_code=403,
            detail="Phiên tư vấn này không thuộc về bạn.",
        )
    return session_id
