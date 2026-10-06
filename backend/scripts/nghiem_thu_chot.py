# -*- coding: utf-8 -*-
"""Lượt nghiệm thu chốt: chạy mọi bộ đo trên MỘT bản code, ghi kết quả kèm dấu vân tay.

    venv/Scripts/python.exe -m scripts.nghiem_thu_chot [--url http://127.0.0.1:8020]

## Làm gì, theo thứ tự

1. **Chốt máy chủ chạy đúng bản code.** Tìm tiến trình đang nghe cổng, lấy giờ
   khởi động, so với file mã sửa gần nhất. File nào mới hơn → máy chủ đang chạy
   mã cũ → **dừng**, không đo. Ba lần trong hai ngày 05–06/10, máy chủ chạy mã cũ
   đã làm sai kết quả đo; lần này nó bị chặn trước khi đo.
2. Ghi dấu vân tay mã nguồn (`dau_van_tay_ma`).
3. Chạy: kiểm thử backend · `nghiem_thu_xuyen_suot` · `e2e_xuyen_suot` ·
   `nghiem_thu_agent --gioi-han=0` (chấm lại, không gọi mô hình) ·
   **`e2e_hanh_trinh --hoi`** — hành trình đầy đủ từ upload CV thật, có gọi mô hình.
4. Tính lại dấu vân tay. Lệch với bước 2 → có người sửa mã giữa chừng → kết quả
   không gắn được với bản code nào → ghi rõ là **không hợp lệ**.
5. Ghi biên bản vào `docs/nghiem_thu/` — Markdown để đọc, JSON để máy so.

## Không dọn dữ liệu

Lượt này là lượt demo: dữ liệu giữ lại để chủ đồ án xem trên màn hình quản trị.
Các phiên được ghi danh vào sổ như mọi bộ đo khác, nên dọn được về sau — khi
chủ đồ án quyết định, không phải lúc này.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import app  # noqa: F401 — đặt stdout về UTF-8
from app.core.config import settings
from scripts import dau_van_tay_ma, so_phien_e2e

GOC = Path(__file__).resolve().parents[1]
PY = sys.executable
THU_MUC_BIEN_BAN = GOC.parent / "docs" / "nghiem_thu"
VN = timezone(timedelta(hours=7))


def _gio_vn(t: datetime) -> str:
    return t.astimezone(VN).strftime("%d/%m/%Y %H:%M:%S")


def gio_khoi_dong_may_chu(cong: int) -> datetime | None:
    """Giờ khởi động của tiến trình đang nghe `cong`, theo đồng hồ máy."""
    lenh = (
        f"$c = Get-NetTCPConnection -LocalPort {cong} -State Listen -ErrorAction SilentlyContinue | "
        "Select-Object -First 1; if ($c) { (Get-Process -Id $c.OwningProcess).StartTime.ToUniversalTime()"
        ".ToString('o') }"
    )
    # Đường dẫn đầy đủ: tiến trình sinh ra từ Git Bash không có `powershell` trong PATH.
    ps = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    ra = subprocess.run([str(ps), "-NoProfile", "-Command", lenh],
                        capture_output=True, text=True, encoding="utf-8")
    s = ra.stdout.strip()
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


#: Thứ máy chủ backend THẬT SỰ nạp. Scripts, tests, frontend không chạy trong
#: tiến trình máy chủ, nên một file ở đó mới hơn máy chủ không có nghĩa là máy
#: chủ chạy mã cũ — bản đầu của chốt này so cả chúng và tự chặn chính nó.
MA_MAY_CHU = ("backend/app/", "backend/main.py")


def file_moi_nhat(ds: list[str]) -> tuple[str, datetime]:
    goc_kho = dau_van_tay_ma.GOC_KHO
    ds = [x for x in ds if x.startswith(MA_MAY_CHU)]
    p = max(ds, key=lambda x: (goc_kho / x).stat().st_mtime)
    return p, datetime.fromtimestamp((goc_kho / p).stat().st_mtime, timezone.utc)


def _node() -> str:
    import shutil

    return os.environ.get("NODE_EXE") or shutil.which("node") or "F:/NodeJS/node.exe"


def chay(ten: str, lenh: list[str], cwd: Path = GOC) -> dict:
    bat_dau = datetime.now(timezone.utc)
    ra = subprocess.run(lenh, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    van_ban = ra.stdout + ("\n" + ra.stderr if ra.stderr.strip() else "")
    return {
        "ten": ten,
        "lenh": " ".join(lenh[2:]) if lenh[:2] == [PY, "-m"] else " ".join(lenh),
        "ma_thoat": ra.returncode,
        "bat_dau": bat_dau.isoformat(),
        "giay": round((datetime.now(timezone.utc) - bat_dau).total_seconds(), 1),
        "dau_ra": van_ban,
    }


def tom_tat(ket: dict) -> str:
    """Một dòng kết quả, rút từ đầu ra của từng bộ."""
    t = ket["dau_ra"]
    dat, hong = re.search(r"^ℹ pass (\d+)$", t, re.M), re.search(r"^ℹ fail (\d+)$", t, re.M)
    if dat and hong:  # đầu ra của `node --test`
        return f"{dat.group(1)} đạt · {hong.group(1)} hỏng"
    for mau in (r"^Ran \d+ tests.*$", r"TỔNG: .*$", r"HÀNH TRÌNH: .*$", r"TỔNG trên .*$"):
        m = re.findall(mau, t, re.M)
        if m:
            kq = m[-1].strip()
            if mau.startswith("^Ran"):
                kq += " · " + ("OK" if re.search(r"^OK", t, re.M) else "FAILED")
            return kq
    return f"mã thoát {ket['ma_thoat']}"


#: Mã thoát "chưa đo được" mà mọi bộ đo dùng chung (mô hình không trả lời, hết
#: hạn mức). Xem `e2e_hanh_trinh.KHONG_DO_DUOC`, `nghiem_thu_agent.KHONG_DO_DUOC`.
KHONG_DO_DUOC = 3


def trang_thai(ma_thoat: int) -> str:
    return "ĐẠT" if ma_thoat == 0 else "CHƯA ĐO ĐƯỢC" if ma_thoat == KHONG_DO_DUOC else "HỎNG"


def tong_ket(ma_thoat: list[int], *, hop_le: bool) -> int:
    """Một mã thoát cho cả lượt, từ mã thoát của từng bộ đo.

    Bản trước chỉ hiểu mã 3 cho riêng bộ hành trình: bộ khác trả 3 thì bị tính
    thành HỎNG, còn bộ chấm Agent thì trước 06/10 luôn trả 0 kể cả khi có ca hỏng
    — nên lượt chốt có thể báo ĐẠT trong khi chất lượng Agent không đạt.

    Thứ tự ưu tiên: dấu vân tay lệch (kết quả không gắn được với bản code nào) →
    có bộ HỎNG → có bộ CHƯA ĐO ĐƯỢC → ĐẠT. Một bộ hỏng là kết luận chắc chắn, nên
    nó thắng "chưa đo được" của bộ khác.
    """
    if not hop_le:
        return 1
    if any(m not in (0, KHONG_DO_DUOC) for m in ma_thoat):
        return 1
    if any(m == KHONG_DO_DUOC for m in ma_thoat):
        return KHONG_DO_DUOC
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8020")
    args = ap.parse_args()
    cong = int(args.url.rsplit(":", 1)[1].split("/")[0])

    bat_dau = datetime.now(timezone.utc)
    ds = dau_van_tay_ma.danh_sach_file()
    van_tay = dau_van_tay_ma.dau_van_tay(ds)
    head = dau_van_tay_ma.ma_head()
    print(f"Dấu vân tay mã: {van_tay}  ({len(ds)} file, HEAD {head})")

    # --- Chốt 1: máy chủ chạy đúng bản code ---------------------------------
    khoi_dong = gio_khoi_dong_may_chu(cong)
    if khoi_dong is None:
        print(f"DỪNG: không có tiến trình nào nghe cổng {cong}.")
        return 2
    moi_nhat, luc = file_moi_nhat(ds)
    print(f"Máy chủ cổng {cong} khởi động lúc {_gio_vn(khoi_dong)}")
    print(f"File mã máy chủ sửa gần nhất: {moi_nhat} lúc {_gio_vn(luc)}")
    if luc > khoi_dong:
        print("DỪNG: có file mã MỚI HƠN máy chủ — máy chủ đang chạy mã cũ. Khởi động lại rồi chạy lại.")
        return 2

    lan_chay = so_phien_e2e.LAN_CHAY
    so_truoc = {d["session_id"] for d in so_phien_e2e.doc()}

    bo = [
        ("Kiểm thử backend", [PY, "-m", "unittest", "discover", "-s", "tests", "-t", "."]),
        ("Xuyên suốt, dựng bằng quy tắc", [PY, "-m", "scripts.nghiem_thu_xuyen_suot"]),
        ("Năm hồ sơ qua HTTP thật", [PY, "-m", "scripts.e2e_xuyen_suot", "--url", args.url]),
        ("Agent — chấm lại bản ghi đo mô hình", [PY, "-m", "scripts.nghiem_thu_agent", "--gioi-han=0"]),
        ("Hành trình đầy đủ từ upload CV thật", [PY, "-m", "scripts.e2e_hanh_trinh", "--hoi", "--url", args.url]),
        # Giao diện: lượt HTTP ở trên KHÔNG chạm tới nó. Hai bộ này chạy component
        # thật (TypeScript dịch, chạy trong `vm`) với API giả — gồm các ca lỗi mạng.
        ("Kiểm thử website (component)", [_node(), "--test", "tests/**/*.test.cjs"], GOC.parent / "frontend"),
        ("Kiểm thử hệ quản trị (component)", [_node(), "--test", "tests/**/*.test.cjs"], GOC.parent / "admin-frontend"),
    ]
    ket = []
    os.environ["E2E_LAN_CHAY"] = lan_chay  # mọi phiên của lượt này chung một mã lần chạy
    for ten, lenh, *noi in bo:
        print(f"\n▶ {ten} …", flush=True)
        k = chay(ten, lenh, noi[0] if noi else GOC)
        k["tom_tat"] = tom_tat(k)
        ket.append(k)
        print(f"  {k['tom_tat']}  ({k['giay']} giây, mã thoát {k['ma_thoat']})")

    # --- Chốt 2: không ai sửa mã giữa chừng ---------------------------------
    van_tay_sau = dau_van_tay_ma.dau_van_tay(dau_van_tay_ma.danh_sach_file())
    hop_le = van_tay_sau == van_tay
    phien_moi = [d for d in so_phien_e2e.doc() if d["session_id"] not in so_truoc]
    phien_hanh_trinh = [d["session_id"] for d in phien_moi if d["bo_do"] == "e2e_hanh_trinh"]
    dat_het = all(k["ma_thoat"] == 0 for k in ket)
    ma_tong = tong_ket([k["ma_thoat"] for k in ket], hop_le=hop_le)
    hanh_trinh = next(k for k in ket if k["ten"].startswith("Hành trình"))
    khong_do_duoc = hanh_trinh["ma_thoat"] == 3

    bien_ban = {
        "lan_chay": lan_chay,
        "bat_dau": bat_dau.isoformat(),
        "ket_thuc": datetime.now(timezone.utc).isoformat(),
        "dau_van_tay_ma": van_tay,
        "dau_van_tay_ma_sau": van_tay_sau,
        "hop_le": hop_le,
        "head": head,
        "so_file_ma": len(ds),
        "may_chu": {"url": args.url, "khoi_dong": khoi_dong.isoformat(),
                    "file_moi_nhat": moi_nhat, "file_moi_nhat_luc": luc.isoformat()},
        "mo_hinh": {"doc_cv_va_chat": settings.gemini_model, "tu_van": settings.advisor_model,
                    "tu_van_du_phong": settings.advisor_model_du_phong or None},
        "database": settings.mongodb_db_name,
        "phien_hanh_trinh": phien_hanh_trinh,
        "phien_moi": [d["session_id"] for d in phien_moi],
        "dat_het": dat_het,
        "hanh_trinh_khong_do_duoc": khong_do_duoc,
        "ket_luan": trang_thai(ma_tong) if hop_le else "KHÔNG HỢP LỆ",
        "bo_do": [{k2: v for k2, v in k.items()} for k in ket],
    }
    THU_MUC_BIEN_BAN.mkdir(parents=True, exist_ok=True)
    ten_file = f"{bat_dau.astimezone(VN):%Y-%m-%d_%H%M}_nghiem_thu_chot"
    (THU_MUC_BIEN_BAN / f"{ten_file}.json").write_text(
        json.dumps(bien_ban, ensure_ascii=False, indent=1), encoding="utf-8")

    dong = [
        f"# Biên bản nghiệm thu chốt — {_gio_vn(bat_dau)}",
        "",
        "Sinh tự động bởi `backend/scripts/nghiem_thu_chot.py`. Bản đầy đủ, kèm toàn bộ đầu ra",
        f"từng bộ đo, ở `{ten_file}.json` cùng thư mục.",
        "",
        "## Bản code",
        "",
        "| | |",
        "|---|---|",
        f"| Dấu vân tay mã (trước) | `{van_tay}` |",
        f"| Dấu vân tay mã (sau) | `{van_tay_sau}` |",
        f"| Hợp lệ | **{'có' if hop_le else 'KHÔNG — mã bị sửa giữa lượt chạy'}** |",
        f"| HEAD lúc chạy | `{head}` (chưa commit — xem mục *Kiểm lại sau khi commit*) |",
        f"| Số file mã | {len(ds)} |",
        f"| Máy chủ khởi động | {_gio_vn(khoi_dong)} — sau file mã máy chủ mới nhất ({_gio_vn(luc)}) |",
        f"| Mô hình | đọc CV / chat: `{settings.gemini_model}` · tư vấn: `{settings.advisor_model}`"
        f" · dự phòng: `{settings.advisor_model_du_phong or '—'}` |",
        "",
        "## Kết quả",
        "",
        "| Bộ đo | Trạng thái | Kết quả | Thời gian |",
        "|---|---|---|---:|",
        *[f"| {k['ten']} | {trang_thai(k['ma_thoat'])} | {k['tom_tat']} | {k['giay']} s |" for k in ket],
        "",
        f"**Tổng: {trang_thai(ma_tong) if hop_le else 'KHÔNG HỢP LỆ — mã bị sửa giữa lượt chạy'}**",
        "",
        "## Phạm vi — đo gì, bằng gì, và CHƯA đo gì",
        "",
        "| Phần | Đo bằng | Ở lượt này |",
        "|---|---|---|",
        "| Máy chủ, dữ liệu, phân quyền, chuỗi nghiệp vụ | kiểm thử backend + bộ HTTP | có |",
        "| Đọc CV và lời trợ lý viết | **mô hình thật**, trong bộ hành trình | có — 2 lượt gọi |",
        "| Giao diện: hành vi component, gồm ca lỗi mạng | kiểm thử component (`node --test`, API giả) | có |",
        "| Giao diện trên **trình duyệt thật** — bố cục, thao tác, mạng thật | — | **KHÔNG** |",
        "",
        "Lượt HTTP từ CV thật không đi qua giao diện. Kết quả của nó **không** được dùng",
        "để tuyên bố giao diện đã nghiệm thu đầy đủ. Hai lỗi giao diện sửa ngày 06/10",
        "(thử lại lượt mở đầu; mã phiên rỗng và lỗi không hiện ở bước kết quả) được",
        "chứng minh bằng kiểm thử component và phép đột biến, chưa bằng một lượt bấm",
        "trên trình duyệt.",
        "",
        "## Phiên của lượt này",
        "",
        f"Mã lần chạy: `{lan_chay}`. Mọi phiên dưới đây đã được ghi danh vào",
        "`storage/_e2e/so_phien.jsonl` và **được giữ lại** để xem trên màn hình quản trị.",
        "",
        *[f"- `{d['session_id']}` — {d['bo_do']}" for d in phien_moi],
        "",
        "## Hành trình đầy đủ — đầu ra nguyên văn",
        "",
        "```",
        hanh_trinh["dau_ra"].strip(),
        "```",
        "",
        "## Kiểm lại sau khi commit",
        "",
        "Checkout bản commit rồi chạy:",
        "",
        "```bash",
        "cd backend && venv/Scripts/python.exe -m scripts.dau_van_tay_ma",
        "```",
        "",
        f"Ra `{van_tay}` nghĩa là bản commit đúng là bản đã nghiệm thu ở đây.",
    ]
    (THU_MUC_BIEN_BAN / f"{ten_file}.md").write_text("\n".join(dong) + "\n", encoding="utf-8")

    print(f"\nBiên bản: docs/nghiem_thu/{ten_file}.md")
    print(f"Hợp lệ: {hop_le} · Đạt hết: {dat_het} · Phiên hành trình: {phien_hanh_trinh}")
    return ma_tong


if __name__ == "__main__":
    raise SystemExit(main())
