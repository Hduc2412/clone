# -*- coding: utf-8 -*-
"""Dọn dữ liệu do các bộ đo E2E sinh ra — theo từng phiên, chỉ phiên có căn cứ, sao lưu trước.

    venv/Scripts/python.exe -m scripts.don_du_lieu_e2e                     # chỉ XEM
    venv/Scripts/python.exe -m scripts.don_du_lieu_e2e --xoa               # sao lưu rồi xóa
    venv/Scripts/python.exe -m scripts.don_du_lieu_e2e --danh-sach f.txt   # thêm phiên đã duyệt tay
    venv/Scripts/python.exe -m scripts.don_du_lieu_e2e --khoi-phuc <thư mục sao lưu> [--phien <id> ...]

## Căn cứ xóa: chỉ hai thứ

1. **Sổ ghi danh** `storage/_e2e/so_phien.jsonl` — bộ đo tự ghi mã phiên của
   nó ngay lúc mở phiên, trước khi có bản ghi nào. Xem `scripts/so_phien_e2e`.
2. **Danh sách đã duyệt** (`--danh-sach`): một mã phiên mỗi dòng, `#` là ghi
   chú. Dành cho phiên thử dựng tay, hoặc phiên tạo trước khi có sổ — người duyệt
   tự liệt kê, chịu trách nhiệm cho từng dòng.

## Dấu hiệu trong dữ liệu KHÔNG phải căn cứ

Bản đầu chọn phiên theo dấu hiệu: câu nhắn bộ đo hay gửi, tên "Ca Một"… Chủ đồ
án chỉ ra ngày 06/10 rằng khách thật gõ đúng câu *"Em muốn gặp để hỏi thêm về
đơn này."* là phiên của họ bị đánh dấu xóa. Nội dung khách nhập không bao giờ đủ
làm căn cứ xóa dữ liệu của khách.

Dấu hiệu vẫn được dò — nhưng chỉ để **báo cáo nghi vấn**: phiên trông giống dữ
liệu thử mà không có trong sổ hay danh sách thì được liệt kê, không bị đụng tới.
Người duyệt xem rồi, nếu đúng, chép mã phiên vào danh sách.

Rà ngược lượt xóa 06/10 (chạy trước khi có sổ): 190/190 phiên đã xóa đều có
bằng chứng mạnh — việc do tài khoản `@local.test` nhận, CV trùng băm file mẫu,
hoặc hồ sơ khớp **từng trường** một ca định nghĩa trong mã bộ đo. Không phiên
nào bị xóa chỉ vì câu nhắn. Nguy cơ có thật trong mã, chưa thành thiệt hại.

## Ba chốt an toàn

1. **Thời điểm.** Phiên trong sổ: mọi bản ghi phải tạo sau lúc ghi danh (trừ hao
   `DUNG_SAI`). Phiên trong danh sách: mọi bản ghi phải tạo từ `--tu-ngay` trở
   đi. Lệch một bản ghi là **dừng hẳn**, không xóa gì.
2. **File.** Chỉ file nằm trong `settings.cv_storage_path`. `tests/fixtures/cv`
   được băm trước và sau; lệch một byte là báo lỗi.
3. **Sao lưu trước, xóa sau**, vào `storage/_sao_luu/e2e_<giờ>/`, đọc lại kiểm đủ
   trước khi xóa. `--khoi-phuc` đưa từng phiên trở lại từ đó.

## Không xóa

`audit_logs` (dấu vết kiểm toán, kể cả của chính lần dọn này); khách hàng còn
dính hồ sơ đăng ký ngoài các phiên được dọn.
"""
import argparse
import asyncio
import hashlib
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bson import json_util

import app  # noqa: F401 — đặt stdout về UTF-8
from app.core.config import settings
from app.db.common import get_db
from app.db.database import close_db, init_db
from scripts import so_phien_e2e

GOC = Path(__file__).resolve().parents[1]
FIXTURE_CV = GOC / "tests" / "fixtures" / "cv"
CV_MAU = FIXTURE_CV / "07_tran_thi_thu_ha.pdf"
KHO_CV = Path(settings.cv_storage_path).resolve()
SAO_LUU = Path(settings.storage_path).resolve() / "_sao_luu"

#: Đồng hồ của bộ đo và của máy chủ cùng một máy, nhưng bản ghi được đóng dấu giờ
#: ở máy chủ còn sổ ghi ở bộ đo. Hai phút là dư cho mọi độ trễ trên một máy.
DUNG_SAI = timedelta(minutes=2)

NHAN_VIEN_E2E_DUOI = "@local.test"

#: Thứ tự xóa không quan trọng với Mongo, nhưng thứ tự KHÔI PHỤC thì có: đưa phiên
#: trở lại theo đúng chiều tạo, để không có bản ghi con nào trỏ tới cha chưa có.
THU_TU = (
    "candidate_profiles", "candidate_documents", "recommendation_logs", "advisor_turns",
    "session_memory", "messages", "leads", "sessions", "managed_leads",
    "recruitment_applications", "application_events", "consultation_reports",
    "support_requests", "consultation_appointments", "appointment_events",
    "notifications", "employee_score_events",
)


def _bam_thu_muc(thu_muc: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(thu_muc.iterdir()) if p.is_file()}


def _gio(t):
    if t is None:
        return None
    if isinstance(t, str):
        t = datetime.fromisoformat(t)
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def doc_danh_sach(duong: str | None) -> list[str]:
    if not duong:
        return []
    ra = []
    for dong in Path(duong).read_text(encoding="utf-8").splitlines():
        dong = dong.split("#", 1)[0].strip()
        if dong:
            ra.append(dong)
    return ra


def can_cu(danh_sach: list[str], *, tu_ngay: datetime) -> dict[str, dict]:
    """`{session_id: {nguon, moc}}` — chỉ sổ ghi danh và danh sách đã duyệt.

    `moc` là thời điểm sớm nhất mà một bản ghi của phiên được phép mang. Phiên
    trong sổ dùng lúc ghi danh; phiên trong danh sách dùng `tu_ngay`.
    """
    ra: dict[str, dict] = {}
    for d in so_phien_e2e.doc():
        if d.get("db") != settings.mongodb_db_name:
            continue  # phiên của một database khác — không phải việc của lần chạy này
        ra[d["session_id"]] = {"nguon": f"sổ ghi danh ({d.get('bo_do')})", "moc": _gio(d["ghi_luc"]) - DUNG_SAI}
    for sid in danh_sach:
        ra.setdefault(sid, {"nguon": "danh sách đã duyệt", "moc": tu_ngay})
    return ra


async def nghi_van(tu_ngay: datetime, da_co: set[str]) -> dict[str, set[str]]:
    """Phiên TRÔNG GIỐNG dữ liệu thử nhưng không có căn cứ. Chỉ để báo cáo."""
    db = get_db()
    ra: dict[str, set[str]] = {}

    def gan(sid, dau):
        if sid and sid not in da_co:
            ra.setdefault(sid, set()).add(dau)

    sha = hashlib.sha256(CV_MAU.read_bytes()).hexdigest()
    async for d in db.candidate_documents.find({"sha256": sha, "created_at": {"$gte": tu_ngay}}, {"session_id": 1}):
        gan(d.get("session_id"), "CV trùng file mẫu 07")
    async for p in db.candidate_profiles.find(
        {"fields.full_name.value": {"$regex": "^Ca (Một|Hai|Ba|Bốn|Năm)$"}, "created_at": {"$gte": tu_ngay}},
        {"session_id": 1},
    ):
        gan(p.get("session_id"), "tên giống ca bộ đo")
    async for y in db.support_requests.find(
        {"assigned_to": {"$regex": f"{NHAN_VIEN_E2E_DUOI}$"}}, {"session_id": 1}
    ):
        gan(y.get("session_id"), "việc do tài khoản @local.test nhận")
    return ra


async def gom_ban_ghi(cac_phien: list[str]) -> dict[str, list[dict]]:
    """Mọi bản ghi của đúng các phiên này, theo từng collection."""
    db = get_db()
    ra: dict[str, list[dict]] = {}

    async def lay(ten, dk):
        ds = await db[ten].find(dk).to_list(None)
        if ds:
            ra.setdefault(ten, []).extend(ds)
        return ds

    theo_phien = {"session_id": {"$in": cac_phien}}
    for ten in ("sessions", "candidate_documents", "advisor_turns", "session_memory", "messages", "leads"):
        await lay(ten, theo_phien)
    ho_so = await lay("candidate_profiles", theo_phien)
    ma_hs = [p["code"] for p in ho_so if p.get("code")]
    await lay("recommendation_logs", {"$or": [theo_phien, {"profile_code": {"$in": ma_hs}}]})
    ho_tro = await lay("support_requests", theo_phien)
    ma_ht = [y["code"] for y in ho_tro]
    lich = await lay("consultation_appointments", {"$or": [
        {"conversation_id": {"$in": cac_phien}}, {"support_code": {"$in": ma_ht}},
    ]})
    ma_tv = [l["appointment_code"] for l in lich]
    await lay("appointment_events", {"appointment_code": {"$in": ma_tv}})
    don = await lay("recruitment_applications", {"$or": [theo_phien, {"profile_code": {"$in": ma_hs}}]})
    ma_don = [d["application_code"] for d in don]
    await lay("application_events", {"application_code": {"$in": ma_don}})
    await lay("consultation_reports", {"$or": [theo_phien, {"application_code": {"$in": ma_don}}]})
    ma_tc = ma_ht + ma_tv + ma_don
    await lay("notifications", {"reference_code": {"$in": ma_tc}})
    await lay("employee_score_events", {"reference_code": {"$in": ma_tc}})

    # Khách hàng: chỉ khi MỌI hồ sơ đăng ký của họ đều thuộc các phiên được dọn.
    ra["_khach_giu_lai"] = []
    for ma in sorted({d.get("lead_code") for d in don if d.get("lead_code")}):
        ngoai = await db.recruitment_applications.count_documents(
            {"lead_code": ma, "application_code": {"$nin": ma_don}}
        )
        kh = await db.managed_leads.find_one({"lead_code": ma})
        if kh is None:
            continue
        if ngoai:
            ra["_khach_giu_lai"].append({"lead_code": ma, "ly_do": f"còn {ngoai} hồ sơ ngoài các phiên được dọn"})
        else:
            ra.setdefault("managed_leads", []).append(kh)
    return ra


def _phien_cua(ten: str, b: dict, ma_hs_phien: dict[str, str]) -> str | None:
    """Bản ghi này thuộc phiên nào — để chốt thời điểm theo đúng mốc của phiên ấy."""
    if b.get("session_id"):
        return b["session_id"]
    if b.get("conversation_id"):
        return b["conversation_id"]
    if b.get("profile_code") in ma_hs_phien:
        return ma_hs_phien[b["profile_code"]]
    return None


def kiem_thoi_diem(ban_ghi: dict[str, list[dict]], can: dict[str, dict]) -> list[str]:
    """Chốt 1. Trả danh sách vi phạm; rỗng là qua."""
    ma_hs_phien = {p["code"]: p["session_id"] for p in ban_ghi.get("candidate_profiles", []) if p.get("code")}
    moc_som_nhat = min(c["moc"] for c in can.values())
    loi = []
    for ten, ds in ban_ghi.items():
        for b in ds:
            t = _gio(b.get("created_at"))
            if t is None:
                if ten in ("session_memory", "sessions"):
                    continue  # hai loại này không đóng dấu giờ tạo; đã gom theo đúng mã phiên
                loi.append(f"{ten} {b.get('code') or b.get('_id')}: không có giờ tạo")
                continue
            sid = _phien_cua(ten, b, ma_hs_phien)
            moc = can[sid]["moc"] if sid in can else moc_som_nhat
            if t < moc:
                loi.append(f"{ten} {b.get('code') or b.get('_id')}: tạo {t:%d/%m %H:%M}, trước mốc {moc:%d/%m %H:%M} của phiên {str(sid)[:8]}")
    return loi


async def khoi_phuc(thu_muc: Path, phien: list[str]) -> int:
    """Đưa các phiên trở lại từ một bản sao lưu. Không ghi đè bản ghi đang có."""
    if not (thu_muc / "PHIEN.json").exists():
        print(f"Không phải thư mục sao lưu: {thu_muc}")
        return 1
    tat_ca = json.loads((thu_muc / "PHIEN.json").read_text(encoding="utf-8"))
    chon = set(phien) if phien else set(tat_ca)
    la = chon - set(tat_ca)
    if la:
        print(f"Không có trong bản sao lưu: {sorted(la)}")
        return 1
    db = get_db()
    ma_hs, ma_ht, ma_tv, ma_don = set(), set(), set(), set()
    nap = {
        ten: json_util.loads((thu_muc / f"{ten}.json").read_text(encoding="utf-8"))
        for ten in THU_TU if (thu_muc / f"{ten}.json").exists()
    }
    for p in nap.get("candidate_profiles", []):
        if p.get("session_id") in chon:
            ma_hs.add(p["code"])
    for y in nap.get("support_requests", []):
        if y.get("session_id") in chon:
            ma_ht.add(y["code"])
    for l in nap.get("consultation_appointments", []):
        if l.get("conversation_id") in chon or l.get("support_code") in ma_ht:
            ma_tv.add(l["appointment_code"])
    for d in nap.get("recruitment_applications", []):
        if d.get("session_id") in chon or d.get("profile_code") in ma_hs:
            ma_don.add(d["application_code"])
    ma_kh = {d.get("lead_code") for d in nap.get("recruitment_applications", []) if d.get("application_code") in ma_don}

    def cua_phien(ten, b):
        return (
            b.get("session_id") in chon
            or b.get("conversation_id") in chon
            or b.get("profile_code") in ma_hs
            or b.get("support_code") in ma_ht
            or b.get("appointment_code") in ma_tv
            or b.get("application_code") in ma_don
            or b.get("reference_code") in (ma_ht | ma_tv | ma_don)
            or (ten == "managed_leads" and b.get("lead_code") in ma_kh)
        )

    tong = 0
    for ten in THU_TU:
        ds = [b for b in nap.get(ten, []) if cua_phien(ten, b)]
        if not ds:
            continue
        da_co = {x["_id"] async for x in db[ten].find({"_id": {"$in": [b["_id"] for b in ds]}}, {"_id": 1})}
        moi = [b for b in ds if b["_id"] not in da_co]
        if moi:
            await db[ten].insert_many(moi)
        tong += len(moi)
        print(f"  khôi phục {ten:28s} {len(moi):5d}" + (f"  (bỏ qua {len(da_co)} đang có)" if da_co else ""))
    so_file = 0
    for d in nap.get("candidate_documents", []):
        if d.get("session_id") in chon and d.get("stored_path"):
            nguon = thu_muc / "cv" / d["stored_path"]
            dich = KHO_CV / d["stored_path"]
            if nguon.exists() and not dich.exists():
                dich.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(nguon, dich)
                so_file += 1
    print(f"Đã khôi phục {len(chon)} phiên: {tong} bản ghi, {so_file} file CV.")
    return 0


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xoa", action="store_true", help="sao lưu rồi XÓA. Thiếu cờ này thì chỉ xem.")
    ap.add_argument("--danh-sach", help="file mã phiên đã duyệt tay, một mã mỗi dòng")
    ap.add_argument("--tu-ngay", default="2026-10-05", help="mốc sớm nhất cho phiên trong danh sách (YYYY-MM-DD)")
    ap.add_argument("--khoi-phuc", help="thư mục sao lưu để đưa phiên trở lại")
    ap.add_argument("--phien", nargs="*", default=[], help="chỉ khôi phục các phiên này")
    args = ap.parse_args()
    tu_ngay = datetime.fromisoformat(args.tu_ngay).replace(tzinfo=timezone.utc)

    bam_truoc = _bam_thu_muc(FIXTURE_CV)
    await init_db()
    try:
        if args.khoi_phuc:
            return await khoi_phuc(Path(args.khoi_phuc), args.phien)

        can = can_cu(doc_danh_sach(args.danh_sach), tu_ngay=tu_ngay)
        print(f"{len(can)} phiên có căn cứ xóa:", dict(Counter(c["nguon"] for c in can.values())))

        nv = await nghi_van(tu_ngay, set(can))
        if nv:
            print(f"\n{len(nv)} phiên TRÔNG GIỐNG dữ liệu thử nhưng KHÔNG có căn cứ — không đụng tới:")
            for sid, dau in sorted(nv.items()):
                print(f"  {sid}  {sorted(dau)}")
            print("  Nếu đúng là dữ liệu thử: chép mã phiên vào một file rồi chạy lại với --danh-sach.")

        if not can:
            print("\nKhông có phiên nào để dọn.")
            return 0

        ban_ghi = await gom_ban_ghi(sorted(can))
        giu_kh = ban_ghi.pop("_khach_giu_lai", [])

        loi = kiem_thoi_diem(ban_ghi, can)
        if loi:
            print(f"\nDỪNG: {len(loi)} bản ghi không qua chốt thời điểm:")
            for x in loi[:20]:
                print("  " + x)
            print("Mã phiên trùng với dữ liệu ngoài phạm vi. KHÔNG xóa gì.")
            return 1

        file_xoa = []
        for d in ban_ghi.get("candidate_documents", []):
            if not d.get("stored_path"):
                continue
            p = (KHO_CV / d["stored_path"]).resolve()
            if KHO_CV not in p.parents or FIXTURE_CV.resolve() in p.parents:
                print(f"DỪNG: file nằm ngoài kho CV: {p}")
                return 1
            file_xoa.append(p)

        print("\nSẽ xóa:")
        for ten in sorted(ban_ghi):
            print(f"  {ten:28s} {len(ban_ghi[ten]):5d}")
        print(f"  {'file CV trong kho':28s} {sum(1 for p in file_xoa if p.exists()):5d}")
        for k in giu_kh:
            print(f"  GIỮ khách {k['lead_code']}: {k['ly_do']}")
        print("Không đụng: audit_logs, phiên không có căn cứ, tests/fixtures/cv.")

        if not args.xoa:
            print("\nChế độ XEM — chưa xóa gì. Thêm --xoa để sao lưu rồi xóa.")
            return 0

        thu_muc = SAO_LUU / f"e2e_{datetime.now():%Y%m%d_%H%M%S}"
        (thu_muc / "cv").mkdir(parents=True, exist_ok=False)
        for ten, ds in ban_ghi.items():
            (thu_muc / f"{ten}.json").write_text(json_util.dumps(ds, ensure_ascii=False, indent=1), encoding="utf-8")
        for p in file_xoa:
            if p.exists():
                dich = thu_muc / "cv" / p.relative_to(KHO_CV)
                dich.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dich)
        (thu_muc / "PHIEN.json").write_text(
            json.dumps({s: [c["nguon"]] for s, c in can.items()}, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        for ten, ds in ban_ghi.items():
            if len(json_util.loads((thu_muc / f"{ten}.json").read_text(encoding="utf-8"))) != len(ds):
                print(f"DỪNG: bản sao lưu {ten} đọc lại không đủ")
                return 1
        print(f"\nĐã sao lưu vào {thu_muc}")

        db = get_db()
        for ten, ds in ban_ghi.items():
            r = await db[ten].delete_many({"_id": {"$in": [b["_id"] for b in ds]}})
            print(f"  xóa {ten:28s} {r.deleted_count:5d}/{len(ds)}")
        n_file = 0
        for p in file_xoa:
            if p.exists():
                p.unlink()
                n_file += 1
        print(f"  xóa file CV {n_file}")
        print(f"  gạch khỏi sổ ghi danh {so_phien_e2e.bo_khoi_so(set(can))} phiên")
    finally:
        await close_db()

    if _bam_thu_muc(FIXTURE_CV) != bam_truoc:
        print("\nLỖI: tests/fixtures/cv đã thay đổi!")
        return 1
    print("\ntests/fixtures/cv nguyên vẹn.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
