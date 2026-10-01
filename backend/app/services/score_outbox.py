"""Sổ chờ ghi điểm — giữ lại điểm khi database hỏng, ghi bù khi nó sống lại.

## Vì sao không thử lại ngay

Thứ hỏng **chính là database**. Thử lại trong vài giây thường vẫn hỏng, và trong
lúc ấy ứng viên đang chờ một lời gọi API trả về. Nên ghi ra một tệp bên cạnh rồi
đi tiếp, và bù sau.

## Vì sao là tệp, không phải một collection

Collection cũng nằm trong chính database đang hỏng. Viết sổ chờ vào đó là xây hầm
trú ẩn bên trong tòa nhà đang cháy.

Tệp nằm trong `storage/`, thư mục đã có trong `.gitignore`.

## Mất điểm nghĩa là gì

Sổ điểm không phải để cho đẹp. Nó là căn cứ đánh giá nhân viên theo từng sự kiện,
và bản thiết kế đã chọn **lưu từng sự kiện thay vì một con số tổng** chính là để
luôn truy ngược được vì sao điểm thay đổi.

Một lần mất điểm âm thầm phá đúng tính chất ấy: tổng vẫn ra một con số, nhưng con
số đó không còn khớp với việc đã làm, và **không ai có cách nào biết**. Người bị
thiếu điểm cũng không biết để hỏi — họ đâu có đếm.

Bản trước bắt mọi ngoại lệ rồi `print` một dòng ra log máy chủ. Trên máy chạy thật
dòng ấy trôi mất trong vài phút.

## Ghi gì vào tệp

Đúng bản ghi định đưa vào database, dạng JSON một dòng một bản. Thêm `ghi_luc` để
biết nó nằm chờ bao lâu — chờ quá lâu là dấu hiệu không ai chạy bù.

Không dọn tệp tự động. Ghi bù xong thì những dòng đã vào database bị bỏ khỏi tệp,
còn dòng nào vẫn hỏng thì ở lại — để lần sau thử tiếp, và để người vận hành nhìn
thấy là có việc chưa xong.
"""
import json
import logging
import pathlib
from typing import Any

from app.core.config import settings


logger = logging.getLogger(__name__)

TEN_TEP = "so-diem-cho-ghi.jsonl"


def duong_dan() -> pathlib.Path:
    return pathlib.Path(settings.storage_path) / TEN_TEP


def ghi_cho(document: dict[str, Any], *, ly_do: str) -> bool:
    """Xếp một bản ghi điểm vào sổ chờ. Trả `False` nếu đến đây cũng hỏng.

    Không ném lỗi ra ngoài trong mọi trường hợp: hàm này được gọi từ nhánh xử lý
    sự cố, và một ngoại lệ ở đây sẽ nuốt mất ngoại lệ gốc — thứ thật sự cần đọc.
    """
    from app.db.common import now

    try:
        duong = duong_dan()
        duong.parent.mkdir(parents=True, exist_ok=True)
        dong = {
            **document,
            "ghi_luc": now().isoformat(),
            "ly_do_hoan": ly_do,
        }
        with duong.open("a", encoding="utf-8") as tep:
            tep.write(json.dumps(dong, ensure_ascii=False, default=str) + "\n")
        logger.warning(
            "Điểm '%s' của %s chưa vào được database (%s) — đã xếp vào sổ chờ %s.",
            document.get("action"),
            document.get("staff_email"),
            ly_do,
            duong.name,
        )
        return True
    except Exception:  # noqa: BLE001 — xem docstring
        logger.exception(
            "Không ghi được cả vào sổ chờ. Điểm '%s' của %s mất hẳn.",
            document.get("action"),
            document.get("staff_email"),
        )
        return False


def dang_cho() -> list[dict[str, Any]]:
    """Những bản ghi đang nằm chờ. Dòng hỏng định dạng thì bỏ qua và báo."""
    duong = duong_dan()
    if not duong.is_file():
        return []
    ra: list[dict[str, Any]] = []
    for so_dong, dong in enumerate(
        duong.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not dong.strip():
            continue
        try:
            ra.append(json.loads(dong))
        except json.JSONDecodeError:
            logger.warning("Sổ chờ ghi điểm: dòng %d hỏng định dạng, bỏ qua.", so_dong)
    return ra


async def ghi_bu() -> dict[str, int]:
    """Thử đưa những bản ghi đang chờ vào database. Trả số liệu từng loại.

    Gọi lúc khởi động: đó là thời điểm database vừa được kiểm tra kết nối, và cũng
    là thời điểm chắc chắn có người đang nhìn log.

    Ba kết quả cho mỗi dòng:

    - **vào được** — bỏ khỏi sổ chờ.
    - **đã có rồi** (`record` trả `None` do trùng khóa) — cũng bỏ, vì mục tiêu là
      điểm có mặt trong database, không phải lần ghi này thành công.
    - **vẫn hỏng** — giữ lại, lần sau thử tiếp.
    """
    from app.db import employee_scores as store

    cho = dang_cho()
    if not cho:
        return {"cho": 0, "vao_duoc": 0, "con_lai": 0}

    con_lai: list[dict[str, Any]] = []
    vao_duoc = 0
    for dong in cho:
        ban_ghi = {k: v for k, v in dong.items() if k not in ("ghi_luc", "ly_do_hoan")}
        try:
            await store.record(ban_ghi)
        except Exception:  # noqa: BLE001 — database vẫn chưa sống, giữ lại
            con_lai.append(dong)
            continue
        vao_duoc += 1

    duong = duong_dan()
    if con_lai:
        duong.write_text(
            "".join(json.dumps(d, ensure_ascii=False, default=str) + "\n" for d in con_lai),
            encoding="utf-8",
        )
    elif duong.is_file():
        duong.unlink()

    logger.info(
        "Sổ chờ ghi điểm: %d bản chờ, %d vào được, %d còn lại.",
        len(cho),
        vao_duoc,
        len(con_lai),
    )
    return {"cho": len(cho), "vao_duoc": vao_duoc, "con_lai": len(con_lai)}
