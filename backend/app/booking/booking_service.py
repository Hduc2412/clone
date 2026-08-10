import re
import secrets
from datetime import date, datetime, timedelta, timezone

from pymongo.errors import DuplicateKeyError

from app.conversation.entity_extractor import extract_name, extract_phone
from app.db.database import create_appointment, save_booking_draft
from app.rag.taxonomy import normalize_text


LOCAL_TIMEZONE = timezone(timedelta(hours=7))
YES_WORDS = {"co", "dong y", "xac nhan", "ok", "oke", "dung", "dat lich"}
NO_WORDS = {"khong", "khong dong y", "sai", "huy", "huy lich"}
CANCEL_PHRASES = {"huy dat lich", "khong dat nua", "thoi khong dat"}
PLAIN_NAME_BLACKLIST = {
    "dat lich",
    "tu van",
    "xac nhan",
    "dong y",
    "khong biet",
    "cam on",
    "xin chao",
    "huy lich",
    "ngay mai",
    "hom nay",
}
NON_NAME_MARKERS = {
    "bao nhieu",
    "cho toi",
    "dat lich",
    "huy lich",
    "la gi",
    "toi can",
    "toi muon",
    "tu van",
    "xac nhan",
}


def _today() -> date:
    return datetime.now(LOCAL_TIMEZONE).date()


def _extract_date(text: str) -> date | None:
    normalized = normalize_text(text)
    if "ngay mai" in normalized:
        value = _today() + timedelta(days=1)
    elif "hom nay" in normalized:
        value = _today()
    else:
        iso_match = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text)
        local_match = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text)
        if iso_match:
            year, month, day = map(int, iso_match.groups())
        elif local_match:
            day, month, year = map(int, local_match.groups())
        else:
            return None
        try:
            value = date(year, month, day)
        except ValueError as exc:
            raise ValueError("Ngày không hợp lệ. Vui lòng nhập theo dạng DD/MM/YYYY.") from exc

    if value < _today():
        raise ValueError("Không thể đặt lịch ở ngày đã qua.")
    if value.weekday() == 6:
        raise ValueError("Chủ Nhật không nhận lịch. Vui lòng chọn từ Thứ Hai đến Thứ Bảy.")
    return value


def _extract_time(text: str) -> str | None:
    match = re.search(
        r"\b([01]?\d|2[0-3])(?::|h|giờ)\s*([0-5]?\d)?\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    total_minutes = hour * 60 + minute
    morning = 8 * 60 <= total_minutes <= 11 * 60 + 30
    afternoon = 13 * 60 + 30 <= total_minutes <= 17 * 60
    if not (morning or afternoon):
        raise ValueError(
            "Giờ nhận lịch là 08:00–11:30 hoặc 13:30–17:00, "
            "từ Thứ Hai đến Thứ Bảy."
        )
    return f"{hour:02d}:{minute:02d}"


def _extract_plain_name(text: str) -> str | None:
    value = text.strip(" .,")
    if not re.fullmatch(
        r"[A-Za-zÀ-ỹĐđ]+(?:\s+[A-Za-zÀ-ỹĐđ]+){1,4}",
        value,
        flags=re.UNICODE,
    ):
        return None
    normalized = normalize_text(value).strip()
    if any(
        marker in normalized
        for marker in PLAIN_NAME_BLACKLIST | NON_NAME_MARKERS
    ):
        return None

    words = value.split()
    # A two-word, all-lowercase phrase is more likely a command ("dat lich")
    # than a full name. Three-or-more-word lowercase Vietnamese names remain valid.
    if len(words) == 2 and not any(word[:1].isupper() for word in words):
        return None
    return value


def _next_question(data: dict) -> tuple[str, str]:
    if not data.get("customer_name"):
        return "name", "Bạn vui lòng cho mình biết **họ và tên** nhé."
    if not data.get("phone"):
        return "phone", "Bạn vui lòng cho mình xin **số điện thoại** để nhân viên liên hệ."
    if not data.get("appointment_date"):
        return (
            "date",
            "Bạn muốn nhân viên liên hệ vào **ngày nào**? "
            "Vui lòng nhập dạng DD/MM/YYYY.",
        )
    if not data.get("appointment_time"):
        return (
            "time",
            "Bạn muốn được liên hệ lúc **mấy giờ**? "
            "Giờ làm việc: 08:00–11:30 và 13:30–17:00, Thứ Hai–Thứ Bảy.",
        )
    summary = (
        "Bạn xác nhận đặt lịch với thông tin sau:\n\n"
        f"- Họ tên: **{data['customer_name']}**\n"
        f"- Số điện thoại: **{data['phone']}**\n"
        f"- Thời gian: **{data['appointment_time']} ngày "
        f"{datetime.strptime(data['appointment_date'], '%Y-%m-%d').strftime('%d/%m/%Y')}**\n\n"
        "Trả lời **có** để xác nhận hoặc **không** để nhập lại."
    )
    return "confirm", summary


async def _persist(session) -> None:
    await save_booking_draft(
        session.session_id,
        session.booking_step,
        session.booking_data,
    )


async def cancel_booking(session) -> str:
    session.booking_step = None
    session.booking_data = {}
    await _persist(session)
    return "Mình đã hủy thao tác đặt lịch. Bạn vẫn có thể tiếp tục hỏi thông tin nhé."


async def process_booking_message(session, message: str) -> tuple[str, bool]:
    """Xử lý một bước booking. Giá trị bool cho biết lịch vừa được tạo."""
    normalized = normalize_text(message).strip()
    if any(phrase in normalized for phrase in CANCEL_PHRASES):
        return await cancel_booking(session), False

    started_booking = session.booking_step is None
    if started_booking:
        session.booking_step = "name"
        session.booking_data = {}
        await _persist(session)
        _, answer = _next_question(session.booking_data)
        return answer, False

    data = session.booking_data

    if session.booking_step == "confirm":
        if normalized in YES_WORDS:
            appointment_date = data["appointment_date"]
            appointment_time = data["appointment_time"]
            appointment_code = (
                f"TV-{appointment_date.replace('-', '')}-"
                f"{secrets.token_hex(2).upper()}"
            )
            appointment = {
                "appointment_code": appointment_code,
                "booking_key": (
                    f"{data['phone']}|{appointment_date}|{appointment_time}"
                ),
                "customer_name": data["customer_name"],
                "phone": data["phone"],
                "appointment_date": appointment_date,
                "appointment_time": appointment_time,
                "conversation_id": session.session_id,
            }
            try:
                await create_appointment(appointment)
            except DuplicateKeyError:
                session.booking_step = None
                session.booking_data = {}
                await _persist(session)
                return (
                    "Số điện thoại này đã có lịch chờ xác nhận vào đúng thời gian trên. "
                    "Nhân viên sẽ liên hệ với bạn theo lịch đã tạo.",
                    False,
                )

            session.booking_step = None
            session.booking_data = {}
            await _persist(session)
            return (
                f"Đặt lịch thành công! Mã lịch của bạn là **{appointment_code}**. "
                "Nhân viên sẽ xác nhận và liên hệ qua số điện thoại bạn đã cung cấp.",
                True,
            )
        if normalized in NO_WORDS:
            session.booking_step = "name"
            session.booking_data = {}
            await _persist(session)
            return (
                "Mình đã xóa thông tin vừa nhập. "
                "Bạn vui lòng cho mình biết lại **họ và tên** nhé.",
                False,
            )
        return "Bạn vui lòng trả lời **có** để xác nhận hoặc **không** để nhập lại.", False

    try:
        if session.booking_step == "name":
            name = extract_name(message) or _extract_plain_name(message)
            if name:
                data["customer_name"] = name
        elif session.booking_step == "phone":
            phone = extract_phone(message)
            if phone:
                data["phone"] = phone
        elif session.booking_step == "date":
            appointment_date = _extract_date(message)
            if appointment_date:
                data["appointment_date"] = appointment_date.isoformat()
        elif session.booking_step == "time":
            appointment_time = _extract_time(message)
            if appointment_time:
                data["appointment_time"] = appointment_time
    except ValueError as exc:
        await _persist(session)
        return str(exc), False

    next_step, answer = _next_question(data)
    if not started_booking and next_step == session.booking_step and not data.get(
        {
            "name": "customer_name",
            "phone": "phone",
            "date": "appointment_date",
            "time": "appointment_time",
        }.get(next_step, "")
    ):
        invalid_messages = {
            "name": "Mình chưa nhận ra họ tên. Bạn vui lòng nhập đầy đủ, ví dụ: **Nguyễn Văn Nam**.",
            "phone": "Số điện thoại chưa hợp lệ. Vui lòng nhập số bắt đầu bằng 0.",
            "date": "Mình chưa nhận ra ngày. Vui lòng nhập dạng **DD/MM/YYYY**.",
            "time": "Mình chưa nhận ra giờ. Vui lòng nhập dạng **09:00** hoặc **14h30**.",
        }
        answer = invalid_messages.get(next_step, answer)

    session.booking_step = next_step
    await _persist(session)
    return answer, False
