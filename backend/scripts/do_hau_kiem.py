# -*- coding: utf-8 -*-
"""Đo hậu kiểm của trợ lý tư vấn trên bộ câu mẫu có nhãn — bản hiện tại, và bản cũ.

    venv/Scripts/python.exe -m scripts.do_hau_kiem [--so-voi=HEAD]

Không gọi mô hình, không chạm database. Bản cũ lấy nguyên `app/advisor/qa.py` ở mốc
git đưa vào, chạy đúng đường xử lý của nó lúc ấy: `kiem_tra` trên bốn khối cũ, rồi
biểu thức `_TU_CHOI` thay mọi câu ngắn chứa "chưa có thông tin". Bản mới chạy
`qa.xu_ly_cau_tra_loi` trên đủ các khối mới cộng câu khách vừa hỏi.

Ba con số cho mỗi bản: chặn nhầm (câu `giu` không tới được khách), để lọt (câu `chan`
tới được khách), và lời từ chối không thành câu chuẩn.
"""
import argparse
import subprocess
import sys
import types
from pathlib import Path

import app  # noqa: F401 — đặt stdout về UTF-8
from app.advisor import qa
from tests import hau_kiem_mau as mau

GOC = Path(__file__).resolve().parents[1]


def _qa_cu(moc: str) -> types.ModuleType:
    nguon = subprocess.run(
        ["git", "show", f"{moc}:backend/app/advisor/qa.py"],
        cwd=GOC, capture_output=True, check=True, encoding="utf-8",
    ).stdout
    mod = types.ModuleType("qa_cu")
    exec(compile(nguon, f"qa.py@{moc}", "exec"), mod.__dict__)
    return mod


def _nhan_moi(cau_hoi: str, cau: str) -> str:
    k = mau.cac_khoi()
    khoi = "\n".join((*k.values(), qa.so_khach_vua_noi(cau_hoi)))
    kq = qa.xu_ly_cau_tra_loi(cau, khoi)
    if kq.nguon == qa.NGUON_MO_HINH:
        return "giu"
    return "tu_choi" if kq.ly_do.startswith("mo_hinh") else "chan"


def _nhan_cu(qa_cu: types.ModuleType, cau: str) -> str:
    k = mau.cac_khoi()
    khoi = "\n".join((k["ho_so"], k["don"], k["doi_chieu"], k["dieu_kien_nen"]))
    if qa_cu.kiem_tra(cau, khoi) is not None:
        return "chan"
    sach = cau.strip()
    if qa_cu._TU_CHOI.search(sach) and len(sach) < 200:
        return "tu_choi"
    return "giu"


def _dem(nhan_that: list[str], nhan_ra: list[str]) -> dict[str, int]:
    cap = list(zip(nhan_that, nhan_ra))
    return {
        "chặn nhầm câu đúng": sum(1 for t, r in cap if t == "giu" and r != "giu"),
        "để lọt câu bịa": sum(1 for t, r in cap if t == "chan" and r == "giu"),
        "từ chối không thành câu chuẩn": sum(1 for t, r in cap if t == "tu_choi" and r != "tu_choi"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--so-voi", default="HEAD", help="mốc git của bản cũ")
    args = ap.parse_args()

    that = [c[2] for c in mau.CAC_CA]
    moi = [_nhan_moi(c[0], c[1]) for c in mau.CAC_CA]
    cu_mod = _qa_cu(args.so_voi)
    cu = [_nhan_cu(cu_mod, c[1]) for c in mau.CAC_CA]

    print(f"Bộ mẫu: {len(that)} câu — giữ {that.count('giu')}, từ chối {that.count('tu_choi')}, chặn {that.count('chan')}")
    print()
    print(f"{'':32}{'bản ' + args.so_voi:>12}{'bản hiện tại':>16}")
    for (ten, a), (_, b) in zip(_dem(that, cu).items(), _dem(that, moi).items()):
        print(f"{ten:32}{a:>12}{b:>16}")
    print()
    print("Từng câu khác nhãn (nhãn thật → bản cũ / bản mới):")
    for (cau_hoi, cau, nhan, ghi_chu, _), a, b in zip(mau.CAC_CA, cu, moi):
        if a != nhan or b != nhan:
            print(f"  [{nhan:7}] cũ={a:7} mới={b:7} · {ghi_chu}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
