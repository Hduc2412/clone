"""Bóc tách CV thành trường dữ liệu có nguồn.

## Chỉ bóc `fields`, không bóc `preferences`

Hồ sơ chia làm hai mục: `fields` là năng lực kiểm chứng được trên giấy tờ,
`preferences` là nguyện vọng do ứng viên nói. CV là giấy tờ, nên nó chỉ được phép
điền vào `fields`. Nguyện vọng phải do chính ứng viên nói ra — suy ra nguyện vọng
từ một tờ CV là đoán hộ người khác, mà đơn hàng lại xếp hạng theo nguyện vọng.

## Mỗi trường phải chỉ được chỗ nó lấy ra

Mô hình được yêu cầu trả kèm `evidence`: đoạn chữ **nguyên văn** trong CV chứa
thông tin đó. Sau đó `map_extraction` đối chiếu ngược đoạn đó với bản gốc, đoạn
nào không tìm thấy thì **bỏ luôn cả trường**.

Đây là chốt chặn chính của module. Mô hình ngôn ngữ rất sẵn lòng điền một năm
sinh hợp lý vào chỗ trống; nhưng nó khó bịa ra một câu nguyên văn có thật trong
tài liệu. Buộc phải trỏ vào bản gốc là cách rẻ nhất để phân biệt "đọc được" với
"đoán ra". Và vì đoạn dẫn được lưu lại, nhân viên mở hồ sơ ra là thấy ngay máy
lấy con số đó từ đâu, không phải tin suông.

## Giá trị phải nằm trong danh mục

Mọi giá trị đi qua bộ chuẩn hóa của `catalog`. Mô hình trả "Tiếng Nhật sơ cấp N4"
thì thành `N4`; trả một thứ không ánh xạ được thì trường đó bị bỏ. Bộ đối chiếu
chỉ hiểu mã trong danh mục, nên để lọt chữ tự do vào là làm hỏng bước sau.
"""
import time
from dataclasses import dataclass, field
from typing import Any

import requests

from app.core.config import settings
from app.matching import catalog

# Tên trường phải trùng với `FIELD_KEYS` của hồ sơ ứng viên.
RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "full_name": {"type": "string"},
        "birth_year": {"type": "integer"},
        "gender": {"type": "string", "enum": ["nam", "nu"]},
        "education_level": {
            "type": "string",
            "enum": ["khac", "trung_cap", "cao_dang", "dai_hoc"],
        },
        "major": {"type": "string"},
        "japanese_level": {
            "type": "string",
            "enum": ["chua_hoc", "N5", "N4", "N3", "N2", "N1"],
        },
        "experience_years": {"type": "number"},
        "care_experience": {"type": "boolean"},
        "phone": {"type": "string"},
        # Dạng **mảng**, không phải object có chín khóa con. Đo trên dịch vụ thật:
        # lược đồ lồng một object chín trường bị từ chối thẳng, kèm thông báo
        # "high demand" gây hiểu nhầm là quá tải nhất thời. Rút bớt còn một trường
        # con thì chạy. Dạng mảng không chạm giới hạn đó và còn thêm được trường
        # mới sau này mà không phải dò lại ngưỡng.
        "evidence": {
            "type": "array",
            "description": "Với mỗi trường đã điền, trích nguyên văn đoạn trong CV.",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["field", "quote"],
            },
        },
    },
}

PROMPT = """Bạn đọc một bản CV của ứng viên ứng tuyển chương trình điều dưỡng tại Nhật Bản.

Nhiệm vụ: rút ra các thông tin có thật trong CV.

Quy tắc bắt buộc:
- Chỉ điền trường mà CV nói rõ. Không suy đoán, không điền giá trị mặc định.
- Trường nào không chắc thì bỏ trống hẳn, đừng đoán.
- Với MỖI trường đã điền, phải ghi vào `evidence` một đoạn NGUYÊN VĂN
  lấy từ CV bên dưới, sao chép đúng từng ký tự, đủ để người đọc kiểm chứng.
- `experience_years` là số năm kinh nghiệm làm việc, tính theo năm.
- `care_experience` chỉ đặt true khi CV mô tả công việc chăm sóc **đã thực sự
  làm** — đi làm, hoặc thực tập có nêu đầu việc cụ thể. KHÔNG tính nguyện vọng,
  mục tiêu nghề nghiệp, ngành đang học, hay danh sách kỹ năng: những mục đó nói
  về việc muốn làm hoặc biết làm, không phải việc đã làm.
- `experience_years` cũng vậy: chỉ đếm thời gian đã đi làm thật.
- `japanese_level` lấy theo chứng chỉ hoặc trình độ CV nêu. CV nói chưa học
  tiếng Nhật thì ghi `chua_hoc`.

--- NỘI DUNG CV ---
{text}
"""

# Giá trị nào cũng phải qua bộ chuẩn hóa tương ứng, hoặc qua hàm ép kiểu riêng.
_NORMALIZERS = {
    "gender": catalog.normalize_gender,
    "education_level": catalog.normalize_education,
    "japanese_level": catalog.normalize_japanese_level,
}

# Chờ rồi thử lại khi dịch vụ quá tải. Ba nhịp tăng dần, tổng cộng dưới hai mươi
# giây — ứng viên vẫn đang nhìn màn hình chờ, không kéo dài hơn được.
RETRY_DELAYS: tuple[int, ...] = (2, 5, 10)
RETRYABLE_CODES = frozenset({429, 500, 503})

# Đoạn dẫn ngắn quá thì không chứng minh được gì: một chữ "Nam" xuất hiện khắp
# nơi trong mọi tài liệu tiếng Việt.
MIN_EVIDENCE_CHARS = 4


class ExtractionFailed(Exception):
    """Không gọi được mô hình, hoặc mô hình trả về thứ không đọc được."""


@dataclass
class Extraction:
    """Kết quả đã lọc: giá trị nhận, giá trị bị loại, và lý do loại."""

    fields: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, str] = field(default_factory=dict)
    rejected: dict[str, str] = field(default_factory=dict)


def map_extraction(raw: dict[str, Any], source_text: str) -> Extraction:
    """Lọc kết quả thô của mô hình. Hàm thuần — kiểm thử được, không cần mạng."""
    from app.db.candidate_profiles import FIELD_KEYS

    evidence_map = _evidence_map(raw.get("evidence"))
    haystack = _searchable(source_text)
    result = Extraction()

    for key, value in raw.items():
        if key == "evidence":
            continue
        if key not in FIELD_KEYS:
            result.rejected[key] = "không phải trường của hồ sơ"
            continue
        if value is None or value == "":
            continue

        quote = str(evidence_map.get(key) or "").strip()
        if len(quote) < MIN_EVIDENCE_CHARS:
            result.rejected[key] = "không chỉ được đoạn dẫn trong CV"
            continue
        if _searchable(quote) not in haystack:
            result.rejected[key] = "đoạn dẫn không có trong CV"
            continue

        normalized = _normalize_value(key, value)
        if normalized is None:
            result.rejected[key] = f"giá trị ngoài danh mục: {value!r}"
            continue

        result.fields[key] = normalized
        result.evidence[key] = quote

    return result


def _evidence_map(evidence: Any) -> dict[str, str]:
    """Đưa phần đoạn dẫn về dạng `{tên trường: câu trích}`.

    Nhận cả hai hình dạng: mảng `[{field, quote}]` theo lược đồ hiện tại, và
    object `{trường: câu}`. Giữ cả hai vì hình dạng lược đồ đã phải đổi một lần
    do giới hạn của dịch vụ, và có thể còn phải đổi nữa — phần lọc không nên gãy
    theo mỗi lần như vậy.
    """
    if isinstance(evidence, dict):
        return {str(key): str(value) for key, value in evidence.items()}
    if isinstance(evidence, list):
        return {
            str(item.get("field")): str(item.get("quote") or "")
            for item in evidence
            if isinstance(item, dict) and item.get("field")
        }
    return {}


def extract_fields(text: str) -> Extraction:
    """Gọi mô hình rồi lọc. Ném `ExtractionFailed` nếu không nhận được JSON."""
    raw = call_model(text)
    return map_extraction(raw, text)


def call_model(text: str) -> dict[str, Any]:
    """Gọi Gemini ở chế độ trả JSON theo lược đồ.

    Viết riêng thay vì dùng lại `app/llm/gemini.py`: file đó phục vụ luồng trò
    chuyện và do nhóm khác phát triển song song, còn ở đây cần ràng buộc lược đồ
    và một model riêng (`gemini_json_model`). Gộp chung thì mỗi lần một bên đổi
    tham số sinh chữ là bên kia lệch theo mà không ai nhận ra.

    Có thử lại khi dịch vụ quá tải. Đo trên máy thật: lần gọi đầu tiên đã dính
    "high demand" — một trục trặc vài giây. Không thử lại thì ứng viên nhận thông
    báo đọc hỏng và phải tự tay khai lại cả tờ CV, vì một sự cố thoáng qua.
    """
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_json_model}:generateContent"
    )
    payload = {
        "contents": [{"parts": [{"text": PROMPT.format(text=text)}]}],
        "generationConfig": {
            # Bóc tách là việc chép lại, không phải việc sáng tạo.
            "temperature": 0.0,
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
        },
    }
    headers = {"x-goog-api-key": settings.gemini_api_key}
    last_error = "Lỗi không rõ"

    for attempt, delay in enumerate(RETRY_DELAYS + (0,)):
        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=settings.gemini_timeout_seconds
            )
            data = response.json()
        except requests.exceptions.RequestException as exc:
            raise ExtractionFailed(f"Không gọi được dịch vụ đọc CV: {exc}") from exc
        except ValueError as exc:
            raise ExtractionFailed("Dịch vụ đọc CV trả về dữ liệu không đọc được.") from exc

        if "error" not in data:
            return _parse_payload(data)

        last_error = data["error"].get("message", "Lỗi không rõ")
        if response.status_code not in RETRYABLE_CODES or not delay:
            break
        print(
            f"[Đọc CV] HTTP {response.status_code} — thử lại sau {delay}s "
            f"(lần {attempt + 1}/{len(RETRY_DELAYS)})"
        )
        time.sleep(delay)

    raise ExtractionFailed(last_error)


def _parse_payload(data: dict[str, Any]) -> dict[str, Any]:
    import json

    candidates = data.get("candidates") or []
    if not candidates:
        raise ExtractionFailed("Dịch vụ đọc CV không trả về nội dung.")

    parts = candidates[0].get("content", {}).get("parts") or []
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise ExtractionFailed("Dịch vụ đọc CV không trả về nội dung.")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ExtractionFailed("Kết quả đọc CV không phải JSON hợp lệ.") from exc

    if not isinstance(parsed, dict):
        raise ExtractionFailed("Kết quả đọc CV không đúng định dạng.")
    return parsed


def _normalize_value(key: str, value: Any) -> Any | None:
    normalizer = _NORMALIZERS.get(key)
    if normalizer is not None:
        return normalizer(value)

    if key == "birth_year":
        return _int_in_range(value, 1950, 2015)
    if key == "experience_years":
        return _float_in_range(value, 0, 50)
    if key == "care_experience":
        return bool(value) if isinstance(value, bool) else None
    if key == "phone":
        from app.core.phone import normalize_vietnamese_phone

        return normalize_vietnamese_phone(str(value))

    # full_name, major: chuỗi tự do, chỉ chặn độ dài vô lý.
    cleaned = " ".join(str(value).split())
    return cleaned if 2 <= len(cleaned) <= 100 else None


def _int_in_range(value: Any, low: int, high: int) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if low <= number <= high else None


def _float_in_range(value: Any, low: float, high: float) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if low <= number <= high else None


def _searchable(text: str) -> str:
    """Dạng dùng để so khớp đoạn dẫn: gộp khoảng trắng, bỏ phân biệt hoa thường.

    Mô hình hay chép lại đúng chữ nhưng đổi cách xuống dòng hoặc khoảng trắng —
    đó vẫn là trích dẫn thật, không nên vì vậy mà loại.
    """
    return " ".join(text.split()).casefold()
