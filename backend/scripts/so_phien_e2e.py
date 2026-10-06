"""Sổ ghi danh phiên do bộ đo E2E tạo — căn cứ DUY NHẤT để tự động xóa dữ liệu thử.

## Vì sao cần sổ, không đoán theo dấu hiệu

Bản đầu của `don_du_lieu_e2e` chọn phiên theo **dấu hiệu trong dữ liệu**: câu nhắn
bộ đo hay gửi, tên "Ca Một"… Chủ đồ án chỉ ra ngày 06/10: một khách thật gõ đúng
câu *"Em muốn gặp để hỏi thêm về đơn này."* là phiên của họ bị đánh dấu xóa. Nội
dung do khách nhập không bao giờ đủ làm căn cứ xóa dữ liệu của khách.

Nên đảo chiều: bộ đo **tự khai** phiên nào là của nó, ngay lúc mở phiên — trước
khi có bất cứ bản ghi nào. Không ai ngoài bộ đo ghi vào sổ này, và sổ nằm ngoài
database nên không lời gọi API nào sửa được nó.

## Định dạng

Một dòng JSON mỗi phiên, trong `<storage>/_e2e/so_phien.jsonl`:

    {"session_id": "...", "bo_do": "e2e_hanh_trinh", "lan_chay": "...",
     "url": "http://127.0.0.1:8020", "db": "xkld_chatbot", "ghi_luc": "2026-10-06T..."}

`db` để script dọn chỉ xử lý phiên thuộc đúng database nó đang nối tới. `ghi_luc`
để chốt an toàn: mọi bản ghi của phiên phải tạo **sau** lúc phiên được ghi danh —
một bản ghi cũ hơn nghĩa là mã phiên trùng với dữ liệu khác, và script dừng.

`storage/` đã nằm trong `.gitignore`.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings

#: Một mã cho mỗi tiến trình bộ đo. `dot_bien` có thể đặt `E2E_LAN_CHAY` cho các
#: tiến trình con để mọi phiên của một lượt đột biến chung một mã.
LAN_CHAY = os.environ.get("E2E_LAN_CHAY") or uuid.uuid4().hex[:12]


def duong_so() -> Path:
    return Path(settings.storage_path) / "_e2e" / "so_phien.jsonl"


def ghi(session_id: str, *, bo_do: str, url: str) -> None:
    """Ghi danh một phiên. Gọi NGAY sau khi mở phiên, trước mọi lời gọi khác."""
    p = duong_so()
    p.parent.mkdir(parents=True, exist_ok=True)
    dong = {
        "session_id": session_id,
        "bo_do": bo_do,
        "lan_chay": LAN_CHAY,
        "url": url,
        "db": settings.mongodb_db_name,
        "ghi_luc": datetime.now(timezone.utc).isoformat(),
    }
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(dong, ensure_ascii=False) + "\n")


def doc() -> list[dict[str, Any]]:
    p = duong_so()
    if not p.exists():
        return []
    ra = []
    for dong in p.read_text(encoding="utf-8").splitlines():
        dong = dong.strip()
        if dong:
            ra.append(json.loads(dong))
    return ra


def bo_khoi_so(session_ids: set[str]) -> int:
    """Gạch khỏi sổ những phiên đã dọn. Trả số dòng đã gạch."""
    con, bo = [], 0
    for d in doc():
        if d["session_id"] in session_ids:
            bo += 1
        else:
            con.append(d)
    p = duong_so()
    if p.exists():
        p.write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in con), encoding="utf-8")
    return bo
