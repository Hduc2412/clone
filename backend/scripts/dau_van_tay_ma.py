"""Dấu vân tay của mã nguồn đang chạy — để gắn một kết quả nghiệm thu với đúng bản code.

    venv/Scripts/python.exe -m scripts.dau_van_tay_ma            # in dấu vân tay
    venv/Scripts/python.exe -m scripts.dau_van_tay_ma --liet-ke  # kèm danh sách file

## Vì sao không dùng mã commit

Nghiệm thu chạy TRƯỚC khi commit — commit chỉ được làm sau khi chủ đồ án duyệt.
Nên lúc chạy chưa có mã commit nào để ghi. Dấu vân tay thay chỗ đó: băm nội dung
mọi file mã và kiểm thử của cây làm việc. Sau khi commit, chạy lại lệnh này trên
bản commit; ra cùng giá trị nghĩa là bản commit **đúng là** bản đã nghiệm thu.

## Phạm vi

Mã chạy và mã kiểm thử của ba phần: `backend/` (app, scripts, tests, main.py,
requirements.txt), `frontend/`, `admin-frontend/`. **Không** gồm tài liệu — tài
liệu được viết sau khi có kết quả, và sửa câu chữ không làm kết quả sai đi.

Chỉ lấy file git theo dõi hoặc sẽ theo dõi (`git ls-files -co --exclude-standard`),
nên `node_modules`, `.next`, `storage/`, `venv` tự nằm ngoài.

## Chuẩn hóa xuống dòng

Kho bật `core.autocrlf`: file trong cây làm việc có thể là LF, bản checkout lại
là CRLF. Băm nguyên byte thì cùng một bản code ra hai dấu vân tay. Nên đổi CRLF
về LF trước khi băm.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

GOC_KHO = Path(__file__).resolve().parents[2]

PHAM_VI = (
    "backend/app/",
    "backend/scripts/",
    "backend/tests/",
    "backend/main.py",
    "backend/requirements.txt",
    "frontend/",
    "admin-frontend/",
)
BO_QUA_DUOI = (".pyc", ".log", ".png", ".jpg", ".ico", ".pdf", ".docx")


def danh_sach_file() -> list[str]:
    ra = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "--", *PHAM_VI],
        cwd=GOC_KHO, capture_output=True, text=True, encoding="utf-8", check=True,
    )
    ds = []
    for dong in ra.stdout.splitlines():
        p = dong.strip()
        if not p or p.endswith(BO_QUA_DUOI) or "/fixtures/" in p:
            # Fixture là DỮ LIỆU vào của phép đo, không phải mã; đáp án và CV
            # mẫu được băm riêng bởi `don_du_lieu_e2e`.
            continue
        if (GOC_KHO / p).is_file():
            ds.append(p)
    return sorted(set(ds))


def dau_van_tay(ds: list[str]) -> str:
    h = hashlib.sha256()
    for p in ds:
        noi_dung = (GOC_KHO / p).read_bytes().replace(b"\r\n", b"\n")
        h.update(p.encode("utf-8") + b"\0")
        h.update(hashlib.sha256(noi_dung).digest())
    return h.hexdigest()


def ma_head() -> str:
    ra = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=GOC_KHO,
                        capture_output=True, text=True, check=True)
    return ra.stdout.strip()


def main() -> int:
    ds = danh_sach_file()
    print(f"dấu vân tay: {dau_van_tay(ds)}")
    print(f"số file: {len(ds)} · HEAD: {ma_head()}")
    if "--liet-ke" in sys.argv:
        for p in ds:
            print("  " + p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
