"""Nghiệm thu MVP theo 6 tình huống §10 của báo cáo mô hình 26/09 (13/10).

    MONGODB_DB_NAME=xkld_kiem_thu_0710 STORAGE_PATH=… python -m scripts.nghiem_thu_mvp [--url=…]

Qua HTTP thật tới máy chủ THỬ (database `xkld_kiem_thu_0710`), mỗi tình huống một
phiên khách riêng (cookie đã ký như trình duyệt). Không gọi mô hình: máy chủ thử
chạy `ADVISOR_ENABLED=false` và chặn mạng ra ngoài — phần câu do AI viết là bản dự
phòng ghép sẵn. Mọi phiên được ghi danh vào sổ E2E để `don_du_lieu_e2e` dọn được.
"""
import json
import random
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from app.core.config import settings  # noqa: E402
from scripts import so_phien_e2e  # noqa: E402
from scripts.e2e_hanh_trinh import Khach  # noqa: E402

# Số điện thoại mới mỗi lượt: hệ thống chỉ cho MỘT hồ sơ đăng ký đang mở trên mỗi người
# (theo số điện thoại) — dùng lại một số cố định thì lượt sau nhận 409 đúng luật.
SDT = f"09{random.randint(0, 99999999):08d}"
GOC = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--url=")), "http://127.0.0.1:8020")
BACKEND = Path(__file__).resolve().parents[1]
CV = BACKEND / "tests" / "fixtures" / "cv"  # CV giả sinh để kiểm thử, không phải hồ sơ người thật
KQ: list[tuple[str, str, bool, str]] = []  # (tình huống, kiểm gì, đạt?, ghi chú)


def kiem(th, ten, dat, ghi=""):
    KQ.append((th, ten, bool(dat), ghi))
    print(f"  [{'ĐẠT ' if dat else 'HỎNG'}] {ten}" + (f" — {ghi}" if ghi else ""))


def phien(nhan):
    k = Khach(GOC)
    s, p = k.goi("/public/phien/moi", method="POST")
    assert s == 200, (s, p)
    sid = p["session_id"]
    so_phien_e2e.ghi(sid, bo_do=f"nghiem_thu_mvp:{nhan}", url=GOC)
    return k, sid


def ho_so(k, sid, **fields):
    s1, _ = k.goi("/public/profiles", method="POST", than={"mode": "manual", "fields": fields,
                  "preferences": {"desired_prefecture": "Tokyo", "desired_employer_type": "vien_duong_lao"}})
    s2, hs = k.goi(f"/public/profiles/{sid}/confirm", method="POST")
    return s1, s2, hs


def da_gui(k, sid):
    """Khách đã gửi gì cho nhân viên: hồ sơ đăng ký của phiên."""
    s, r = k.goi(f"/public/registrations/{sid}")
    return r if s == 200 else {"loi": s}


def chot():
    if settings.mongodb_db_name != "xkld_kiem_thu_0710":
        sys.exit(f"DỪNG: tiến trình trỏ {settings.mongodb_db_name!r}")
    s, d = Khach(GOC).goi("/public/job-orders/DH-0001")
    if "[KIỂM THỬ]" not in (d or {}).get("title", ""):
        sys.exit("DỪNG: máy chủ không phải database thử")


def th1():
    th = "1. Chưa có CV / file không đọc được"
    print(th)
    k, sid = phien("th1")
    s, r = k.gui_file(f"/public/documents/{sid}", CV / "06_dang_thi_ngoc_scan.pdf")
    tl = (r or {}).get("document") or {}
    kiem(th, "CV scan được nhận nhưng đánh dấu không đọc được (không OCR, không gửi bản gốc cho mô hình)",
         s in (200, 201, 202) and tl.get("status") == "unreadable", f"HTTP {s}, trạng thái {tl.get('status')!r}")
    kiem(th, "Hướng khách gửi bản có chữ hoặc tự khai", "khai" in ((r or {}).get("message") or ""),
         repr(((r or {}).get("message") or "")[:120]))
    hs = (r or {}).get("profile") or {}
    kiem(th, "Không có trường nào bị điền từ file không đọc được", not (hs.get("fields") or {}),
         f"{len(hs.get('fields') or {})} trường")
    dk = da_gui(k, sid)
    kiem(th, "Không tự chuyển nhân viên vì thiếu CV", not (dk.get("items") or dk.get("registrations")),
         json.dumps(dk, ensure_ascii=False)[:120])


def th2():
    th = "2. Khách chưa học tiếng Nhật (đơn yêu cầu N4)"
    print(th)
    k, sid = phien("th2")
    s1, s2, _ = ho_so(k, sid, full_name="Ngô Thị Chưa Học", japanese_level="chua_hoc", birth_year=2002,
                      gender="nu", education_level="cao_dang", major="Điều dưỡng", experience_years=1)
    kiem(th, "Khai tay và xác nhận hồ sơ", s1 == 201 and s2 == 200, f"{s1}/{s2}")
    s, p = k.goi(f"/tu-van/v1/{sid}/don/DH-0001")
    kiem(th, "Đối chiếu: chưa đạt, vướng đúng tiêu chí tiếng Nhật",
         s == 200 and not p.get("eligible") and [b.get("key") for b in p.get("blockers") or []] == ["japanese"],
         f"eligible={p.get('eligible')}, blockers={[b.get('key') for b in p.get('blockers') or []]}")
    kiem(th, "Không mở nút đăng ký khi chưa đạt", p.get("can_register") is False)
    hoc = json.dumps(p.get("learning"), ensure_ascii=False)
    kiem(th, "Lộ trình học từ bảng khóa học: 6–7 tháng, 35 triệu trong tổng 90 triệu",
         (p.get("learning") or {}).get("months_text") == "6–7 tháng" and (p.get("learning") or {}).get("tuition_vnd") == 35000000
         and "90000000" in hoc, hoc)
    s, h = k.goi(f"/tu-van/v1/{sid}/don/DH-0001/hoi", method="POST", than={"question": "Em cần học bao lâu thì đủ?"})
    cau = (h or {}).get("answer") or ""
    kiem(th, "AI tắt: trợ lý vẫn trả lời bằng bản dự phòng, nói rõ chưa phải câu trả lời riêng, không bịa số",
         s == 200 and (h or {}).get("source") != "mo_hinh" and "6–7 tháng" in cau,
         f"nguồn {(h or {}).get('source')!r}: {cau[:110]!r}")
    dk = da_gui(k, sid)
    kiem(th, "Không tự gửi phiếu cho nhân viên hay tạo học viên", not (dk.get("items") or dk.get("registrations")))
    return k, sid


def th3():
    th = "3. Đã học, chưa có chứng chỉ (N4 tự khai)"
    print(th)
    k, sid = phien("th3")
    s1, s2, hs = ho_so(k, sid, full_name="Đỗ Thị Tự Khai", japanese_level="N4", birth_year=2000, gender="nu",
                       education_level="cao_dang", major="Điều dưỡng", experience_years=2, phone=SDT)
    nhan = ((hs or {}).get("trang_thai_tieng_nhat") or {}).get("nhan") or ""
    kiem(th, "Trình độ ghi là tự khai, chưa đối chứng — không coi là đã có chứng chỉ", "tự khai" in nhan, repr(nhan))
    s, p = k.goi(f"/tu-van/v1/{sid}/don/DH-0001")
    kiem(th, "Không bị coi là chưa học: vẫn đạt điều kiện N4 của đơn", s == 200 and p.get("eligible") is True)
    return k, sid


def th4(k, sid):
    th = "4. Đổi đơn / quay lại"
    print(th)
    s, a = k.goi(f"/tu-van/v1/{sid}/don/DH-0004")
    s0, hs0 = k.goi(f"/public/profiles/{sid}")
    kiem(th, "Đổi sang đơn khác dùng lại hồ sơ đã có, không bắt khai lại", s == 200 and a.get("profile_confirmed") is True,
         f"DH-0004: {a.get('branch_label')!r}")
    s, d = k.goi(f"/tu-van/v1/{sid}/don/DH-0017")
    kiem(th, "Đơn quá hạn không được trình bày như đang tuyển", s == 404 or not (d or {}).get("can_register"),
         f"HTTP {s}")
    ban = (hs0 or {}).get("version")
    s1, _ = k.goi(f"/public/profiles/{sid}", method="PATCH", than={"fields": {"japanese_level": "N3"}})
    s, b = k.goi(f"/tu-van/v1/{sid}/don/DH-0017")
    s3, p3 = k.goi(f"/tu-van/v1/{sid}/don/DH-0001")
    s4, hs4 = k.goi(f"/public/profiles/{sid}")
    kiem(th, "Quay lại sau khi học (N4 → N3): hồ sơ lên phiên bản mới và đánh giá lại",
         s1 == 200 and (hs4 or {}).get("version", 0) > (ban or 0) and p3.get("eligible") is True,
         f"phiên bản {ban} → {(hs4 or {}).get('version')}; trạng thái {(hs4 or {}).get('status')!r}")


def th5(k, sid):
    th = "5. Khách muốn chốt đơn / AI không giải quyết được"
    print(th)
    s, hs = k.goi(f"/public/profiles/{sid}")
    if (hs or {}).get("status") != "confirmed":
        k.goi(f"/public/profiles/{sid}/confirm", method="POST")
    s, _ = k.goi(f"/public/registrations/{sid}", method="POST", than={"job_order_code": "DH-0001", "confirmed": False})
    kiem(th, "Chưa xác nhận thì không tạo đăng ký", s != 201, f"HTTP {s}")
    s, dk = k.goi(f"/public/registrations/{sid}", method="POST", than={"job_order_code": "DH-0001", "confirmed": True})
    kiem(th, "Xác nhận thì tạo đúng một hồ sơ đăng ký, trạng thái chờ nhân viên (không phải 'đã tuyển')",
         s == 201 and dk.get("status") in ("pending_intake", "draft", "collecting_documents"),
         f"HTTP {s}, {dk.get('application_code')} · {dk.get('status')!r}")
    s, _ = k.goi(f"/public/registrations/{sid}", method="POST", than={"job_order_code": "DH-0001", "confirmed": True})
    kiem(th, "Bấm đăng ký lần hai không tạo hồ sơ thứ hai", s in (400, 409, 429), f"HTTP {s}")
    than = {"kind": "nhan_tin", "full_name": "Đỗ Thị Tự Khai", "phone": SDT,
            "message": "Em muốn hỏi thêm về lịch phỏng vấn.", "job_order_code": "DH-0001", "dong_y_ban_giao": False}
    s, ht = k.goi(f"/tu-van/v1/{sid}/ho-tro", method="POST", than=than)
    s2, ht2 = k.goi(f"/tu-van/v1/{sid}/ho-tro", method="POST", than=than)
    kiem(th, "Yêu cầu nhân viên được lưu, gửi lại không nhân đôi",
         s == 201 and s2 == 201 and (ht or {}).get("code") == (ht2 or {}).get("code"),
         f"{(ht or {}).get('code')} / {(ht2 or {}).get('code')}")


def th6(k, sid):
    th = "6. Khách từ chối chuyển tiếp / hệ thống lỗi"
    print(th)
    dk = da_gui(k, sid)
    kiem(th, "Khách chưa bấm gửi thì không có gì tới nhân viên (phiên tình huống 2)",
         not (dk.get("items") or dk.get("registrations")))
    s, _ = k.goi(f"/tu-van/v1/{sid}/ho-tro", method="POST", than={"kind": "nhan_tin", "full_name": "A", "phone": "1"})
    kiem(th, "Thiếu họ tên / số điện thoại hợp lệ thì từ chối, không lưu dở", s == 422, f"HTTP {s}")
    s, h = k.goi(f"/tu-van/v1/{sid}/don/DH-0001/hoi", method="POST", than={"question": "Đơn này có chắc đỗ không?"})
    cau = (h or {}).get("answer") or ""
    kiem(th, "AI lỗi/tắt: báo rõ, không hứa kết quả tuyển dụng",
         s == 200 and "chắc chắn đỗ" not in cau and "cam kết" not in cau, f"{cau[:110]!r}")


def main():
    chot()
    if "--chi-th2" in sys.argv:
        th2()
        return 0 if all(d for *_, d, _ in KQ) else 1
    th1()
    k2, sid2 = th2()
    k3, sid3 = th3()
    th4(k3, sid3)
    th5(k3, sid3)
    th6(k2, sid2)
    dat = sum(1 for *_, d, _ in KQ if d)
    print(f"\nTỔNG: {dat}/{len(KQ)} phép kiểm đạt")
    (BACKEND.parent / "docs" / "nghiem_thu" / f"{datetime.now():%Y-%m-%d}_nghiem_thu_mvp.json").write_text(
        json.dumps([{"tinh_huong": a, "kiem": b, "dat": c, "ghi": d} for a, b, c, d in KQ], ensure_ascii=False, indent=2),
        encoding="utf-8")
    return 0 if dat == len(KQ) else 1


sys.exit(main())
