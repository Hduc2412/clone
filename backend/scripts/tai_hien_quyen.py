# -*- coding: utf-8 -*-
"""Tái hiện (hoặc bác bỏ) từng vấn đề quyền và dữ liệu trên MÁY CHỦ THẬT, database thử.

    MONGODB_DB_NAME=xkld_kiem_thu_0710 STORAGE_PATH=... \\
        venv/Scripts/python.exe -m scripts.tai_hien_quyen [--goc http://127.0.0.1:8020]

Mỗi phép đo gọi đúng API mà giao diện gọi, bằng tài khoản `consultant` thật (tạo
tạm), cookie phiên thật của khách. Kết quả của từng phép đo là một trong hai:

- `LỖI` — hành vi trái quy tắc đã chốt, kèm bằng chứng lấy từ phản hồi.
- `ĐÚNG` — hành vi đúng quy tắc.

## Chốt an toàn — chạy trước mọi lần ghi

1. Tiến trình này phải trỏ `xkld_kiem_thu_0710` (đọc `settings`).
2. Máy chủ đang chạy cũng phải trỏ đúng database ấy: đơn `DH-0001` trong database thử
   mang dấu `[KIỂM THỬ]` ở tên; máy chủ trả tên không có dấu thì dừng.
3. Kho tệp phải nằm trong thư mục kiểm thử.

Không đạt cả ba thì không ghi gì. Tài khoản tạm chỉ xóa đúng những cái chính script
này tạo. Dữ liệu khách thử (phiên, hồ sơ, yêu cầu) nằm lại trong database thử.
"""
import argparse
import asyncio
import json
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

import app  # noqa: F401 — đặt stdout về UTF-8
from app.core.config import settings
from scripts.e2e_hanh_trinh import Khach

DB_THU = "xkld_kiem_thu_0710"
DAU_THU = "[KIỂM THỬ]"
GHI_CHU_NOI_BO = "NOI_BO_KIEM_QUYEN_0810"

NV_A = ("tq-tu-van-a@local.test", "TqTuVanA!2026")
NV_B = ("tq-tu-van-b@local.test", "TqTuVanB!2026")
QL = ("tq-quan-ly@local.test", "TqQuanLy!2026")

KET: list[dict] = []


def ghi(ma: str, mo_ta: str, loi: bool, bang_chung) -> None:
    KET.append({"ma": ma, "mo_ta": mo_ta, "ket_qua": "LỖI" if loi else "ĐÚNG", "bang_chung": bang_chung})
    print(f"[{'LỖI ' if loi else 'ĐÚNG'}] {ma}: {mo_ta}\n        {json.dumps(bang_chung, ensure_ascii=False)[:400]}")


# --- Database: chỉ database thử -------------------------------------------------


async def _db(viec):
    from app.db.common import get_db
    from app.db.database import close_db, init_db

    await init_db()
    try:
        return await viec(get_db())
    finally:
        await close_db()


async def _tao_tai_khoan() -> list[str]:
    from app.auth.security import hash_password
    from app.db.database import create_staff_user

    async def viec(db):
        tao = []
        for (email, mk), vai in ((NV_A, "consultant"), (NV_B, "consultant"), (QL, "manager")):
            if await db.staff_users.count_documents({"email": email}):
                continue
            await create_staff_user({"full_name": f"Kiểm quyền {email[3:12]} (tạm)", "email": email,
                                     "role": vai, "password_hash": hash_password(mk)})
            tao.append(email)
        return tao
    return await _db(viec)


async def _xoa_tai_khoan(emails: list[str]) -> int:
    async def viec(db):
        return (await db.staff_users.delete_many({"email": {"$in": emails}})).deleted_count if emails else 0
    return await _db(viec)


def _dang_nhap(goc: str, email: str, mk: str) -> Khach:
    k = Khach(goc)
    ma, ra = k.goi("/auth/login", method="POST", than={"email": email, "password": mk})
    if ma != 200:
        raise SystemExit(f"{email} không đăng nhập được: {ma} {ra}")
    return k


def _khach_moi(goc: str, ten: str, so: str, *, muc="N4") -> tuple[Khach, str]:
    k = Khach(goc)
    ma, ra = k.goi("/public/phien/moi", method="POST")
    sid = (ra or {}).get("session_id")
    ma, ra = k.goi("/public/profiles", method="POST", than={
        "mode": "manual",
        "fields": {"full_name": ten, "birth_year": 1998, "japanese_level": muc, "education_level": "cao_dang",
                   "gender": "nu", "experience_years": 1, "phone": so},
        "preferences": {"desired_region_group": "kanto"},
    })
    if ma not in (200, 201):
        raise SystemExit(f"không tạo được hồ sơ thử: {ma} {ra}")
    return k, sid


def _ngay_lam_viec() -> str:
    d = date.today() + timedelta(days=2)
    while d.weekday() == 6:
        d += timedelta(days=1)
    return d.isoformat()


def _khoa_nhay_cam(item: dict) -> list[str]:
    return sorted(k for k in ("phone", "full_name", "message", "ban_giao", "advice_block", "session_id") if item.get(k))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--goc", default="http://127.0.0.1:8020")
    ap.add_argument("--ghi", default=str(Path(__file__).resolve().parents[2] / "docs" / "nghiem_thu"
                                        / "2026-10-08_tai_hien_quyen.json"))
    args = ap.parse_args()
    goc = args.goc

    # --- Chốt an toàn ---
    if settings.mongodb_db_name != DB_THU:
        print(f"DỪNG: tiến trình trỏ {settings.mongodb_db_name!r}, không phải {DB_THU!r}.")
        return 2
    if "kiem_thu" not in str(settings.storage_path):
        print(f"DỪNG: kho tệp {settings.storage_path} không phải kho kiểm thử.")
        return 2
    ma, don = Khach(goc).goi("/public/job-orders/DH-0001")
    if ma != 200 or DAU_THU not in (don or {}).get("title", ""):
        print(f"DỪNG: máy chủ {goc} không chứng minh được đang đọc {DB_THU} (DH-0001: {ma} {(don or {}).get('title')!r}).")
        return 2
    print(f"Chốt an toàn: tiến trình và máy chủ đều đọc {DB_THU}; kho {settings.storage_path}\n")

    tao = asyncio.run(_tao_tai_khoan())
    try:
        a = _dang_nhap(goc, *NV_A)
        b = _dang_nhap(goc, *NV_B)
        ql = _dang_nhap(goc, *QL)
        hau_to = uuid.uuid4().hex[:4]
        so1, so2, so3, so4 = (f"0900{int(hau_to, 16) % 1000000:06d}"[:10],
                              f"0901{int(hau_to, 16) % 1000000:06d}"[:10],
                              f"0902{int(hau_to, 16) % 1000000:06d}"[:10],
                              f"0903{int(hau_to, 16) % 1000000:06d}"[:10])
        k1, s1 = _khach_moi(goc, "Kiểm Quyền Một", so1)
        k2, s2 = _khach_moi(goc, "Kiểm Quyền Hai", so2)
        k3, s3 = _khach_moi(goc, "Kiểm Quyền Ba", so3)

        # ===== B.1 Yêu cầu hỗ trợ =====
        _, h1 = k1.goi(f"/tu-van/v1/{s1}/ho-tro", method="POST", than={
            "kind": "gap_mat", "message": "Kiểm quyền: yêu cầu của khách một", "full_name": "Kiểm Quyền Một",
            "phone": so1, "job_order_code": "DH-0001", "appointment_date": _ngay_lam_viec(),
            "appointment_time": "10:00", "meeting_kind": "truc_tuyen"})
        _, h2 = k2.goi(f"/tu-van/v1/{s2}/ho-tro", method="POST", than={
            "kind": "nhan_tin", "message": "Kiểm quyền: câu hỏi riêng của khách hai", "full_name": "Kiểm Quyền Hai",
            "phone": so2})
        h1, h2 = (h1 or {}).get("code"), (h2 or {}).get("code")
        a.goi(f"/ho-tro/{h1}/nhan", method="POST")

        ma, ds = b.goi("/ho-tro?status=dang_xu_ly")
        dong = next((i for i in (ds or {}).get("items", []) if i.get("code") == h1), None)
        ghi("HT-1", "B (consultant) liệt kê yêu cầu A đang giữ qua ?status=dang_xu_ly",
            dong is not None and bool(_khoa_nhay_cam(dong)),
            {"http": ma, "thay": dong is not None, "khoa_nhay_cam": _khoa_nhay_cam(dong or {})})
        ma, ct = b.goi(f"/ho-tro/{h1}")
        yc = (ct or {}).get("request") or {}
        ghi("HT-2", "B đọc chi tiết yêu cầu A đang giữ bằng gọi thẳng API",
            ma == 200, {"http": ma, "khoa_nhay_cam": _khoa_nhay_cam(yc), "co_lich": bool((ct or {}).get("appointment"))})
        ma, ds = b.goi("/ho-tro")
        dong = next((i for i in (ds or {}).get("items", []) if i.get("code") == h2), None)
        ghi("HT-3", "Hàng đợi chưa ai nhận trả cho consultant cả số điện thoại, lời nhắn, bản bàn giao",
            bool(_khoa_nhay_cam(dong or {})), {"http": ma, "thay": dong is not None, "khoa_nhay_cam": _khoa_nhay_cam(dong or {})})
        ma, ct = b.goi(f"/ho-tro/{h2}")
        ghi("HT-4", "B đọc chi tiết đầy đủ yêu cầu CHƯA ai nhận (trước khi bấm nhận)",
            ma == 200 and bool(_khoa_nhay_cam((ct or {}).get("request") or {})),
            {"http": ma, "khoa_nhay_cam": _khoa_nhay_cam((ct or {}).get("request") or {})})

        # ===== B.2 Hội thoại =====
        phien_chat = f"kiem-quyen-chat-{hau_to}"

        async def chen_hoi_thoai(db):
            from app.db.common import now
            await db.sessions.insert_one({"session_id": phien_chat, "created_at": now(), "last_active": now(),
                                          "message_count": 2, "booking_data": {"phone": so4}})
            await db.messages.insert_many([
                {"session_id": phien_chat, "role": "user", "content": "Kiểm quyền: tin riêng tư của một khách", "created_at": now()},
                {"session_id": phien_chat, "role": "assistant", "content": "Trả lời thử", "created_at": now()}])
        asyncio.run(_db(chen_hoi_thoai))
        ma, ds = b.goi("/management/conversations?limit=500")
        thay = any(i.get("session_id") == phien_chat for i in (ds if isinstance(ds, list) else (ds or {}).get("items", [])))
        ghi("HT-5", "B liệt kê hội thoại của khách không liên quan tới mình", thay, {"http": ma, "thay": thay})
        ma, ct = b.goi(f"/management/conversations/{phien_chat}")
        ghi("HT-6", "B đọc nội dung hội thoại của khách không liên quan", ma == 200,
            {"http": ma, "so_tin": len((ct or {}).get("messages", []))})

        # ===== B.3 Tạo khách hàng =====
        ma, ra = a.goi("/management/leads", method="POST", than={
            "customer_name": "Khách kiểm quyền", "phone": so4, "assigned_to": NV_B[0]})
        ghi("HT-7", "A (consultant) tạo khách và giao luôn cho B qua assigned_to trong thân yêu cầu",
            ma == 201 and (ra or {}).get("assigned_to") == NV_B[0], {"http": ma, "assigned_to": (ra or {}).get("assigned_to")})

        # ===== B.4 internal_note =====
        async def dat_ghi_chu(db):
            await db.job_orders.update_one({"code": "DH-0001"}, {"$set": {"internal_note": GHI_CHU_NOI_BO}})
        asyncio.run(_db(dat_ghi_chu))
        lo = []
        for duong, kh in (("/public/job-orders/DH-0001", Khach(goc)), ("/public/job-orders", Khach(goc)),
                          (f"/tu-van/v1/{s1}/don/DH-0001?dien_dat=false", k1), (f"/public/matches/{s1}", k1)):
            ma, ra = kh.goi(duong)
            if GHI_CHU_NOI_BO in json.dumps(ra, ensure_ascii=False):
                lo.append(duong)
        ghi("HT-8", "internal_note lọt ra API phía khách", bool(lo), {"lot_ra": lo})
        ma, ra = b.goi("/job-orders/DH-0001")
        thay_ghi_chu = GHI_CHU_NOI_BO in json.dumps(ra, ensure_ascii=False)
        KET.append({"ma": "HT-9", "mo_ta": "consultant đọc internal_note qua API nội bộ (chỉ ghi nhận, chưa kết luận)",
                    "ket_qua": "GHI NHẬN", "bang_chung": {"http": ma, "doc_duoc": thay_ghi_chu}})
        print(f"[GHI NHẬN] HT-9: consultant đọc internal_note nội bộ: {thay_ghi_chu}")

        # ===== Phiếu tóm tắt hồ sơ đăng ký chưa ai nhận =====
        k2.goi(f"/public/matches/{s2}")  # đăng ký đòi khách đã xem danh sách đơn phù hợp
        ma, dk2 = k2.goi(f"/public/registrations/{s2}", method="POST", than={"job_order_code": "DH-0001", "confirmed": True})
        r2 = (dk2 or {}).get("application_code")
        if not r2:
            raise SystemExit(f"không dựng được hồ sơ đăng ký thử: {ma} {dk2}")
        ma, ds = b.goi("/registrations/queue")
        dong = next((i for i in (ds or {}).get("items", []) if i.get("application_code") == r2), {})
        ghi("HT-10", "Hàng đợi đăng ký trả cho consultant họ tên, số điện thoại của khách chưa ai nhận",
            bool(dong.get("phone") or dong.get("full_name") or dong.get("customer_name")),
            {"http": ma, "khoa": sorted(k for k in ("phone", "full_name", "customer_name", "note") if dong.get(k))})
        ma, ra = b.goi(f"/registrations/{r2}/report")
        ghi("HT-11", "Consultant đọc phiếu tóm tắt đầy đủ của hồ sơ đăng ký chưa ai nhận", ma == 200,
            {"http": ma, "do_dai": len(json.dumps(ra, ensure_ascii=False))})

        # ===== C. Thông tin đã xác minh =====
        k1.goi(f"/public/matches/{s1}")
        ma, dk1 = k1.goi(f"/public/registrations/{s1}", method="POST", than={"job_order_code": "DH-0001", "confirmed": True})
        r1 = (dk1 or {}).get("application_code")
        if not r1:
            raise SystemExit(f"không dựng được hồ sơ đăng ký thử: {ma} {dk1}")
        a.goi(f"/registrations/{r1}/accept", method="POST")
        _, ung = a.goi(f"/applications/{r1}")
        trang_thai = ((ung or {}).get("application") or ung or {}).get("status")
        for buoc in ("collecting_documents", "screening"):
            if trang_thai != buoc:
                ma_b, _ = a.goi(f"/applications/{r1}", method="PATCH", than={"status": buoc})
                trang_thai = buoc if ma_b == 200 else trang_thai
        ma, ra = a.goi(f"/applications/{r1}/so-tuyen", method="POST", than={
            "japanese_level": "N4", "chung_cu": "ban_goc", "hinh_thuc": "truc_tuyen", "next_status": "eligible",
            "note": "GHI_CHU_NOI_BO_HS"})
        if ma != 200:
            ghi("XM-0", "Không ghi được kết quả sơ tuyển để dựng ca xác minh", True, {"http": ma, "ra": ra})
        else:
            ma, hs = k1.goi(f"/public/profiles/{s1}")
            ma_p, ra = k1.goi(f"/public/profiles/{s1}", method="PATCH",
                              than={"fields": {"japanese_level": "N5"}, "expected_version": (hs or {}).get("version")})
            ma, sau = k1.goi(f"/public/profiles/{s1}")
            o = ((sau or {}).get("fields") or {}).get("japanese_level") or {}
            xung = ((sau or {}).get("consultation") or {}).get("conflicts") or []
            co_ghi = any(c.get("field") == "japanese_level" and c.get("suggested") == "N5" for c in xung)
            ghi("XM-1", "Khách sửa trình độ đã được nhân viên xác minh: bị bỏ qua im lặng, không lưu đề xuất, không báo",
                o.get("value") == "N4" and not co_ghi and "xac_minh" not in json.dumps(ra, ensure_ascii=False),
                {"http_patch": ma_p, "gia_tri_sau": o.get("value"), "nguon": o.get("source"),
                 "verification": o.get("verification"), "co_luu_de_xuat": co_ghi})
            # Nhân viên sửa giá trị qua biểu mẫu chung: nhãn xác minh cũ có còn bám không?
            ma, hs_nv = a.goi(f"/profiles/{(sau or {}).get('code')}")
            hs_nv = (hs_nv or {}).get("profile") or hs_nv or {}
            ma, ra = a.goi(f"/profiles/{hs_nv.get('code')}", method="PATCH",
                           than={"fields": {"japanese_level": "N3"}, "expected_version": hs_nv.get("version")})
            o2 = (((ra or {}).get("profile") or ra or {}).get("fields") or {}).get("japanese_level") or {}
            ghi("XM-2", "Nhân viên đổi giá trị đã xác minh bằng biểu mẫu chung mà nhãn xác minh cũ vẫn còn",
                o2.get("verification") == "verified" and o2.get("value") == "N3",
                {"http": ma, "gia_tri": o2.get("value"), "verification": o2.get("verification"),
                 "verified_by": o2.get("verified_by")})

            # ===== F. Nhân viên cập nhật → ngữ cảnh trợ lý và kết quả đổi theo =====
            ma_hs = hs_nv.get("code")
            _, hs_moi = a.goi(f"/profiles/{ma_hs}")
            hs_moi = (hs_moi or {}).get("profile") or hs_moi or {}
            ma_h, ra_h = a.goi(f"/profiles/{ma_hs}/hoc-tap", method="POST", than={
                "trang_thai": "dang_hoc", "muc_tieu": "N2", "khoa_code": None,
                "expected_version": hs_moi.get("version")})
            ma_m, kq = k1.goi(f"/public/matches/{s1}")
            _, hs_sau = a.goi(f"/profiles/{ma_hs}")
            hs_sau = (hs_sau or {}).get("profile") or hs_sau or {}

            async def doc_khoi(db):
                from app.consultation import tien_do
                from app.db import candidate_profiles as store
                return tien_do.render(await tien_do.nap(s1, await store.get_by_session(s1)))
            khoi = asyncio.run(_db(doc_khoi))
            ghi("KN-1", "Ghi tiến độ học không thành công hoặc không vào ngữ cảnh trợ lý",
                ma_h != 200 or "đang học hướng tới N2" not in khoi or "chưa phải trình độ đã có" not in khoi,
                {"http": ma_h, "trich": [d for d in khoi.splitlines() if "học" in d][:2]})
            ghi("KN-2", "Kết quả đối chiếu không theo phiên bản hồ sơ mới sau khi nhân viên sửa",
                ma_m != 200 or (kq or {}).get("profile_version") not in (None, hs_sau.get("version")),
                {"http": ma_m, "phien_ban_ket_qua": (kq or {}).get("profile_version"), "phien_ban_ho_so": hs_sau.get("version")})
            ghi("KN-3", "Ngữ cảnh trợ lý thiếu chặng hồ sơ đăng ký (theo đúng chặng khách thấy)",
                "Đủ điều kiện sơ bộ" not in khoi,
                {"trich": [d for d in khoi.splitlines() if "đơn DH-0001" in d][:2]})
            # Nhân viên đã sửa đúng ô khách đề xuất (XM-2) → đề xuất phải đóng, không còn
            # treo trong ngữ cảnh như thể chưa ai xem.
            xung = ((hs_sau.get("consultation") or {}).get("conflicts")) or []
            cua_o = [c for c in xung if c.get("field") == "japanese_level" and c.get("kind") == "khac_gia_tri_nhan_vien"]
            ghi("KN-5", "Đề xuất của khách không được đóng sau khi nhân viên sửa chính ô đó",
                not cua_o or any(c.get("trang_thai") != "da_xu_ly" for c in cua_o) or "xem lại" in khoi,
                {"trang_thai": [c.get("trang_thai") for c in cua_o]})
            lo = [x for x in (NV_A[0], "GHI_CHU_NOI_BO_HS", "eligible") if x in khoi]
            ghi("KN-4", "Ngữ cảnh trợ lý lộ email nhân viên, ghi chú nội bộ hoặc trạng thái nội bộ", bool(lo), {"lo": lo})

        # ===== Bản 2 (08/10 tối): liên kết rõ ràng, đồng ý bàn giao, căn cứ xác minh =====
        phien_la = f"kiem-quyen-trung-so-{hau_to}"

        async def chen_chat(db):
            from app.db.common import now
            # Phiên chat của CHÍNH khách một (cùng mã phiên với hồ sơ — liên kết rõ ràng),
            # và một phiên của NGƯỜI KHÁC đặt lịch bằng ĐÚNG số của khách một.
            for sid, so_dl in ((s1, so1), (phien_la, so1)):
                await db.sessions.update_one({"session_id": sid}, {"$set": {
                    "session_id": sid, "last_active": now(), "message_count": 1,
                    "booking_data": {"phone": so_dl}}, "$setOnInsert": {"created_at": now()}}, upsert=True)
                await db.messages.insert_one({"session_id": sid, "role": "user", "content": "Kiểm quyền bản 2", "created_at": now()})
        asyncio.run(_db(chen_chat))
        _, ds = a.goi("/management/conversations?limit=500")
        thay = {i.get("session_id") for i in (ds if isinstance(ds, list) else [])}
        ghi("HT-12", "Trùng số điện thoại mở hội thoại của người khác cho nhân viên", phien_la in thay,
            {"thay_phien_cua_khach_minh": s1 in thay, "thay_phien_nguoi_khac_cung_so": phien_la in thay})
        ma_h, _ = ql.goi(f"/registrations/{r1}/handover", method="POST",
                         than={"assigned_to": NV_B[0], "note": "Kiểm quyền: chuyển A sang B"})
        _, ds = a.goi("/management/conversations?limit=500")
        thay_a = {i.get("session_id") for i in (ds if isinstance(ds, list) else [])}
        _, ds = b.goi("/management/conversations?limit=500")
        thay_b = {i.get("session_id") for i in (ds if isinstance(ds, list) else [])}
        ghi("HT-13", "Chuyển hồ sơ A → B mà A vẫn đọc hội thoại hoặc B chưa đọc được",
            ma_h != 200 or s1 in thay_a or s1 not in thay_b,
            {"http_chuyen": ma_h, "A_con_thay": s1 in thay_a, "B_thay": s1 in thay_b})

        for ten_ma, dong_y in (("HT-14", True), ("HT-15", False)):
            kx, sx = _khach_moi(goc, f"Kiểm Đồng Ý {ten_ma}", f"0904{int(hau_to, 16) % 100000:05d}{int(dong_y)}"[:10])
            _, yc = kx.goi(f"/tu-van/v1/{sx}/ho-tro", method="POST", than={
                "kind": "nhan_tin", "message": "Kiểm quyền bản 2", "full_name": f"Kiểm Đồng Ý {ten_ma}",
                "phone": f"0904{int(hau_to, 16) % 100000:05d}{int(dong_y)}"[:10], "dong_y_ban_giao": dong_y})
            ma_yc = (yc or {}).get("code")
            b.goi(f"/ho-tro/{ma_yc}/nhan", method="POST")
            _, cua_b = b.goi("/ho-tro/cua-toi")
            dong = next((i for i in (cua_b or {}).get("items", []) if i.get("code") == ma_yc), {})
            ma_hs = dong.get("profile_code")
            if not ma_hs:
                async def tim(db):
                    return (await db.candidate_profiles.find_one({"session_id": sx}, {"code": 1}) or {}).get("code")
                ma_hs = asyncio.run(_db(tim))
            ma_doc, _ = b.goi(f"/profiles/{ma_hs}")
            ma_cv, _ = b.goi(f"/documents/profile/{ma_hs}")
            ma_sua, _ = b.goi(f"/profiles/{ma_hs}", method="PATCH", than={"fields": {"major": "Thử sửa"}})
            if dong_y:
                ghi(ten_ma, "Người giữ yêu cầu (khách đồng ý) không đọc được hồ sơ/CV, hoặc lại SỬA được",
                    ma_doc != 200 or ma_cv != 200 or ma_sua == 200,
                    {"profile_code_trong_danh_sach": dong.get("profile_code"), "doc_ho_so": ma_doc, "doc_cv": ma_cv, "sua_ho_so": ma_sua})
            else:
                ghi(ten_ma, "Khách KHÔNG đồng ý mà người giữ yêu cầu vẫn đọc được hồ sơ/CV",
                    ma_doc == 200 or ma_cv == 200 or dong.get("profile_code"),
                    {"doc_ho_so": ma_doc, "doc_cv": ma_cv, "profile_code": dong.get("profile_code")})

        # Ô nhân viên nhập KHÔNG có căn cứ: khách sửa được, nhân viên nhận thông báo.
        _, hs_b = b.goi(f"/profiles/{(sau or {}).get('code')}")
        hs_b = (hs_b or {}).get("profile") or hs_b or {}
        ma_nv, _ = b.goi(f"/profiles/{hs_b.get('code')}", method="PATCH",
                         than={"fields": {"experience_years": 1}, "expected_version": hs_b.get("version")})
        _, hs_k = k1.goi(f"/public/profiles/{s1}")
        ma_k, _ = k1.goi(f"/public/profiles/{s1}", method="PATCH",
                         than={"fields": {"experience_years": 3}, "expected_version": (hs_k or {}).get("version")})
        _, hs_k = k1.goi(f"/public/profiles/{s1}")
        o_kn = ((hs_k or {}).get("fields") or {}).get("experience_years") or {}
        ghi("XM-3", "Ô nhân viên nhập không có căn cứ vẫn khóa lời khai mới của khách",
            ma_nv != 200 or o_kn.get("value") != 3,
            {"nhan_vien_ghi": ma_nv, "khach_sua": ma_k, "gia_tri_sau": o_kn.get("value"), "nguon": o_kn.get("source")})

        _, jo_b = b.goi("/job-orders/DH-0001")
        _, jo_q = ql.goi("/job-orders/DH-0001")
        ghi("JO-1", "internal_note không đúng phạm vi đọc (chỉ Admin/Manager)",
            "internal_note" in (jo_b or {}) or "internal_note" not in (jo_q or {}),
            {"consultant_co": "internal_note" in (jo_b or {}), "manager_co": "internal_note" in (jo_q or {})})

        # ===== D. Hồ sơ chưa xác nhận =====
        k3.goi(f"/public/matches/{s3}")

        async def bo_xac_nhan(db):
            await db.candidate_profiles.update_one({"session_id": s3}, {"$set": {"status": "extracted"}})
        asyncio.run(_db(bo_xac_nhan))
        ma, ra = k3.goi(f"/tu-van/v1/{s3}/don/DH-0001?dien_dat=false")
        ghi("XN-1", "API tư vấn theo đơn trả bảng, điểm, kết luận cho hồ sơ CHƯA xác nhận",
            ma == 200 and bool((ra or {}).get("rows") or (ra or {}).get("blockers") or (ra or {}).get("strengths")),
            {"http": ma, "so_dong": len((ra or {}).get("rows") or []), "branch": (ra or {}).get("branch")})
        ma, ra = k3.goi(f"/public/matches/{s3}/orders/DH-0001")
        ghi("XN-2", "API lý do chi tiết một đơn trả kết quả cho hồ sơ CHƯA xác nhận", ma == 200,
            {"http": ma, "eligible": (ra or {}).get("eligible")})

        # Kết quả cũ sau khi sửa hồ sơ
        async def xac_nhan_lai(db):
            await db.candidate_profiles.update_one({"session_id": s3}, {"$set": {"status": "confirmed"}})
        asyncio.run(_db(xac_nhan_lai))
        _, hs3 = k3.goi(f"/public/profiles/{s3}")
        k3.goi(f"/public/profiles/{s3}", method="PATCH",
               than={"fields": {"japanese_level": "chua_hoc"}, "expected_version": (hs3 or {}).get("version")})
        ma, ra = k3.goi(f"/public/matches/{s3}/orders/DH-0001")
        dong_tn = next((r for r in (ra or {}).get("hard_rows", []) if r.get("key") == "japanese"), {})
        ghi("XN-3", "Sau khi sửa trình độ, API lý do chi tiết vẫn trả kết quả của phiên bản hồ sơ cũ",
            ma == 200 and "N4" in (dong_tn.get("candidate_text") or ""),
            {"http": ma, "dong_tieng_nhat": dong_tn.get("candidate_text"), "eligible": (ra or {}).get("eligible")})
    finally:
        xoa = asyncio.run(_xoa_tai_khoan(tao))
        print(f"\nTài khoản tạm: tạo {len(tao)}, xóa {xoa}")

    loi = sum(r["ket_qua"] == "LỖI" for r in KET)
    print(f"\nTỔNG: {loi} lỗi tái hiện được / {len(KET)} phép đo")
    Path(args.ghi).write_text(json.dumps({"database": settings.mongodb_db_name, "goc": goc, "ket_qua": KET},
                                         ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Ghi: {args.ghi}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
