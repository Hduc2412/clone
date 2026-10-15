"""Quyền đọc, thông tin đã xác minh và cửa chặn hồ sơ chưa xác nhận — qua ROUTE thật (08/10).

Mỗi ca dựng ứng dụng FastAPI với đúng router sản phẩm, gọi bằng `TestClient` như trình
duyệt gọi, chỉ giả lập tầng lưu trữ. Đi kèm `scripts/tai_hien_quyen.py`, bộ kiểm cùng
những điều này trên máy chủ thật trỏ database thử — 13 lỗi tái hiện được trước khi sửa.
"""
import json
import re
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from tests.test_khong_lo_lien_lac import CO_CAY_MA_DAY_DU, LY_DO_BO_QUA

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.security import get_current_user
from app.db import candidate_profiles as store

ADMIN = {"email": "admin@example.com", "full_name": "Quản trị", "role": "admin"}
QUAN_LY = {"email": "quan.ly@example.com", "full_name": "Quản lý", "role": "manager"}
A = {"email": "tu.van.a@example.com", "full_name": "Tư vấn A", "role": "consultant"}
B = {"email": "tu.van.b@example.com", "full_name": "Tư vấn B", "role": "consultant"}
PHIEN = "3db5442f-f6d1-41ee-8928-cf4392392d00"


def app_voi(*routers, nguoi=None) -> TestClient:
    ung_dung = FastAPI()
    for r in routers:
        ung_dung.include_router(r)
    if nguoi is not None:
        ung_dung.dependency_overrides[get_current_user] = lambda: nguoi
    return TestClient(ung_dung)


# --- B.1 Yêu cầu hỗ trợ ------------------------------------------------------


def yeu_cau(code="HT-AAA111", *, assigned_to=None, status="cho_xu_ly"):
    return {
        "code": code, "kind": "gap_mat", "status": status, "session_id": PHIEN,
        "full_name": "Lê Thị Minh", "phone": "0900000000", "message": "Lời nhắn riêng",
        "ban_giao": "BẢN BÀN GIAO ĐẦY ĐỦ", "advice_block": "KHỐI ĐỐI CHIẾU",
        "job_order_code": "DH-0001", "assigned_to": assigned_to, "appointment_code": "TV-1",
        "created_at": "2026-10-08T07:00:00Z",
    }


NHAY_CAM = ("phone", "full_name", "message", "ban_giao", "advice_block", "session_id")


class HoTroTests(unittest.TestCase):
    def setUp(self):
        from app.api import support
        self.support = support
        self.store = support.store

    def _goi(self, nguoi, method, duong, **kw):
        with app_voi(self.support.router, nguoi=nguoi) as c:
            return getattr(c, method)(duong, **kw)

    def test_hang_doi_cho_consultant_chi_co_ban_toi_thieu(self):
        with patch.object(self.store, "list_requests", AsyncMock(return_value=[yeu_cau()])), \
             patch.object(self.store, "count_requests", AsyncMock(return_value=1)):
            r = self._goi(B, "get", "/ho-tro")
        dong = r.json()["items"][0]
        self.assertEqual(r.status_code, 200)
        self.assertEqual(dong["code"], "HT-AAA111")
        self.assertEqual(dong["ten_viet_tat"], "L. T. M.")
        for k in NHAY_CAM:
            self.assertNotIn(k, dong, f"hàng đợi lộ {k}")

    def test_trang_thai_khac_chi_tra_viec_cua_minh(self):
        ds = AsyncMock(return_value=[])
        with patch.object(self.store, "list_requests", ds), \
             patch.object(self.store, "count_requests", AsyncMock(return_value=0)):
            self._goi(B, "get", "/ho-tro?status=dang_xu_ly")
        self.assertEqual(ds.await_args.kwargs.get("assigned_to"), B["email"])

    def test_chi_tiet_viec_nguoi_khac_dang_giu_bi_chan(self):
        with patch.object(self.store, "get_request", AsyncMock(return_value=yeu_cau(assigned_to=A["email"], status="dang_xu_ly"))):
            r = self._goi(B, "get", "/ho-tro/HT-AAA111")
        self.assertEqual(r.status_code, 403)

    def test_chi_tiet_viec_chua_ai_nhan_chi_ban_toi_thieu(self):
        with patch.object(self.store, "get_request", AsyncMock(return_value=yeu_cau())):
            r = self._goi(B, "get", "/ho-tro/HT-AAA111")
        self.assertEqual(r.status_code, 200)
        for k in NHAY_CAM:
            self.assertNotIn(k, r.json()["request"])
        self.assertIsNone(r.json()["appointment"])

    def test_nguoi_giu_va_quan_ly_doc_du(self):
        for nguoi in (A, QUAN_LY):
            with patch.object(self.store, "get_request", AsyncMock(return_value=yeu_cau(assigned_to=A["email"], status="dang_xu_ly"))), \
                 patch.object(self.support, "_dong_bo_lich", AsyncMock(return_value=None)):
                r = self._goi(nguoi, "get", "/ho-tro/HT-AAA111")
            self.assertEqual(r.status_code, 200, nguoi["email"])
            self.assertEqual(r.json()["request"]["phone"], "0900000000")

    def test_sau_khi_chuyen_nguoi_cu_mat_quyen(self):
        """Quyền theo người giữ HIỆN TẠI — không theo lịch sử phụ trách."""
        doc = {**yeu_cau(assigned_to=B["email"], status="dang_xu_ly"),
               "lich_su_phu_trach": [{"tu": A["email"], "den": B["email"]}]}
        with patch.object(self.store, "get_request", AsyncMock(return_value=doc)):
            r = self._goi(A, "get", "/ho-tro/HT-AAA111")
        self.assertEqual(r.status_code, 403)

    def test_tra_loi_viec_chua_nhan_bi_chan(self):
        with patch.object(self.store, "get_request", AsyncMock(return_value=yeu_cau())):
            r = self._goi(B, "post", "/ho-tro/HT-AAA111/tra-loi", json={"reply": "Trả lời khi chưa nhận"})
        self.assertEqual(r.status_code, 403)


# --- Hàng đợi đăng ký ---------------------------------------------------------


def ho_so_dang_ky(**kw):
    return {"application_code": "HS-AAA111", "customer_name": "Lê Thị Minh", "phone": "0900000000",
            "job_order_code": "DH-0001", "status": "draft", "source": "self_registration",
            "assigned_to": None, "note": "ghi chú nội bộ", "created_at": "2026-10-08", **kw}


class HangDoiDangKyTests(unittest.TestCase):
    def setUp(self):
        from app.api import registrations
        self.api = registrations

    def test_consultant_thay_ban_toi_thieu_quan_ly_thay_du(self):
        for nguoi, du in ((B, False), (QUAN_LY, True)):
            with patch.object(self.api, "list_unassigned_registrations", AsyncMock(return_value=[ho_so_dang_ky()])), \
                 patch.object(self.api, "count_unassigned_registrations", AsyncMock(return_value=1)):
                with app_voi(self.api.router, nguoi=nguoi) as c:
                    dong = c.get("/registrations/queue").json()["items"][0]
            self.assertEqual("phone" in dong, du, nguoi["role"])
            self.assertEqual("customer_name" in dong, du, nguoi["role"])
            if not du:
                self.assertNotIn("note", dong)

    def test_phieu_ho_so_chua_ai_nhan(self):
        for nguoi, ma in ((B, 403), (QUAN_LY, 200)):
            with patch.object(self.api, "get_recruitment_application", AsyncMock(return_value=ho_so_dang_ky())), \
                 patch.object(self.api.reports, "get_by_application", AsyncMock(return_value={"code": "PT-1"})):
                with app_voi(self.api.router, nguoi=nguoi) as c:
                    r = c.get("/registrations/HS-AAA111/report")
            self.assertEqual(r.status_code, ma, nguoi["role"])


# --- B.2 Hội thoại, B.3 tạo khách ---------------------------------------------


class _Con:
    """Con trỏ giả: đủ `limit`, `to_list`, lặp async."""

    def __init__(self, rows):
        self.rows = rows

    def limit(self, _):
        return self

    def sort(self, *_a, **_k):
        return self

    async def to_list(self, length=None):
        return list(self.rows)

    def __aiter__(self):
        self._i = iter(self.rows)
        return self

    async def __anext__(self):
        try:
            return next(self._i)
        except StopIteration:
            raise StopAsyncIteration


class _Kho:
    def __init__(self, rows):
        self.rows = rows
        self.loc = []

    def find(self, query, _proj=None):
        self.loc.append(query)
        return _Con(self.rows)


class _Db:
    def __init__(self, **kho):
        for ten, rows in kho.items():
            setattr(self, ten, _Kho(rows))


class HoiThoaiTests(unittest.IsolatedAsyncioTestCase):
    async def test_quan_ly_khong_gioi_han(self):
        from app.services import quyen_hoi_thoai
        self.assertIsNone(await quyen_hoi_thoai.phien_duoc_xem(QUAN_LY))

    async def _phien(self, nguoi, *, ho_so=(), lich=(), don=(), ho_tro=frozenset()):
        from app.services import quyen_hoi_thoai
        db = _Db(candidate_profiles=list(ho_so), consultation_appointments=list(lich),
                 sessions=[{"session_id": "chat-nguoi-la-cung-so"}])
        with patch.object(quyen_hoi_thoai, "get_db", return_value=db), \
             patch.object(quyen_hoi_thoai, "list_recruitment_applications", AsyncMock(return_value=list(don))), \
             patch("app.services.quyen_ho_so.phien_qua_ho_tro", AsyncMock(return_value=set(ho_tro))):
            return await quyen_hoi_thoai.phien_duoc_xem(nguoi), db

    async def test_chi_lien_ket_ro_rang(self):
        phien, db = await self._phien(
            B, ho_so=[{"session_id": "phien-ho-so-cua-b"}], lich=[{"conversation_id": "phien-lich-cua-b"}],
            don=[{"session_id": "phien-don-cua-b"}], ho_tro={"phien-ho-tro-dong-y"})
        self.assertEqual(phien, {"phien-ho-so-cua-b", "phien-lich-cua-b", "phien-don-cua-b", "phien-ho-tro-dong-y"})
        # Hồ sơ và lịch hẹn tra theo người phụ trách HIỆN TẠI của chính bản ghi.
        self.assertEqual(db.candidate_profiles.loc[0], {"assigned_to": B["email"]})
        self.assertEqual(db.consultation_appointments.loc[0]["assigned_to"], B["email"])

    async def test_trung_so_dien_thoai_khong_mo_hoi_thoai_nguoi_khac(self):
        """Hai người dùng chung một số: bản 1 nối qua `booking_data.phone` nên lộ phiên
        của người kia. Bản 2 không tra bảng phiên theo số nào cả."""
        phien, db = await self._phien(B, ho_so=[{"session_id": "phien-ho-so-cua-b"}])
        self.assertNotIn("chat-nguoi-la-cung-so", phien)
        self.assertEqual(db.sessions.loc, [], "không được tra phiên chat theo số điện thoại")

    async def test_chuyen_nguoi_phu_trach_thi_nguoi_cu_mat_quyen(self):
        # Hồ sơ đã chuyển sang người khác: tra theo `assigned_to` của B không ra gì nữa.
        phien, _ = await self._phien(B)
        self.assertEqual(phien, set())

    def test_route_chi_tiet_chan_phien_khong_lien_quan(self):
        from app.api import management
        with patch.object(management.quyen_hoi_thoai, "phien_duoc_xem", AsyncMock(return_value={"chat-cua-minh"})), \
             patch.object(management, "get_messages", AsyncMock(return_value=[{"role": "user", "content": "x"}])):
            with app_voi(management.router, nguoi=B) as c:
                self.assertEqual(c.get("/management/conversations/chat-nguoi-khac").status_code, 403)
                self.assertEqual(c.get("/management/conversations/chat-cua-minh").status_code, 200)

    def test_route_danh_sach_loc_theo_quyen(self):
        from app.api import management
        ds = AsyncMock(return_value=[])
        with patch.object(management.quyen_hoi_thoai, "phien_duoc_xem", AsyncMock(return_value={"chat-cua-minh"})), \
             patch.object(management, "list_conversations", ds):
            with app_voi(management.router, nguoi=B) as c:
                c.get("/management/conversations")
        self.assertEqual(ds.await_args.kwargs["session_ids"], {"chat-cua-minh"})

    def test_tao_khach(self):
        from app.api import management
        tao = AsyncMock(side_effect=lambda d: d)
        with patch.object(management, "create_managed_lead", tao), \
             patch.object(management, "audit_action", AsyncMock()), \
             patch.object(management, "validate_assignee", AsyncMock(side_effect=lambda e: e)):
            with app_voi(management.router, nguoi=A) as c:
                r1 = c.post("/management/leads", json={"customer_name": "Khách", "phone": "0900000000", "assigned_to": B["email"]})
                r2 = c.post("/management/leads", json={"customer_name": "Khách", "phone": "0900000000"})
            with app_voi(management.router, nguoi=QUAN_LY) as c:
                r3 = c.post("/management/leads", json={"customer_name": "Khách", "phone": "0900000000", "assigned_to": B["email"]})
        self.assertEqual(r1.status_code, 403)
        self.assertEqual(r2.json()["assigned_to"], A["email"])
        self.assertEqual(r3.json()["assigned_to"], B["email"])


# --- C. Thông tin đã xác minh --------------------------------------------------


def ho_so(**kw):
    return {
        "code": "UV-AAA111", "session_id": PHIEN, "status": "confirmed", "version": 3,
        "assigned_to": A["email"],
        "fields": {
            "full_name": store.cell("Lê Thị Minh", "user_confirmed"),
            "japanese_level": {**store.cell("N4", "staff"), "verification": "verified",
                               "evidence_type": "ban_goc", "verified_by": A["email"], "verified_at": "2026-10-08"},
        },
        "preferences": {}, "consultation": {}, **kw,
    }


class XacMinhTests(unittest.TestCase):
    def _khach_patch(self, profile, body):
        from app.api import profiles as api
        from tests.cookie_phien import cookies_cho
        ghi = AsyncMock()
        # Lần ghi giả trả ĐÚNG những gì được ghi xuống — không trả lại hồ sơ cũ, nếu
        # không thì ca "giá trị vẫn N4" xanh cả khi đã bị đè (đột biến lọt 08/10).
        self.da_ghi = {}

        def _ghi(*a, **k):
            self.da_ghi.update(k)
            return {**profile, "fields": k["fields"], "preferences": k["preferences"], "version": 4}
        with patch.object(store, "get_by_session", AsyncMock(return_value=profile)), \
             patch.object(store, "apply_changes", AsyncMock(side_effect=_ghi)), \
             patch.object(store, "ghi_de_xuat", ghi), \
             patch.object(store, "ghi_thong_bao_khach_sua", AsyncMock()):
            with app_voi(api.public_router) as c:
                c.cookies.update(cookies_cho(PHIEN))
                r = c.patch(f"/public/profiles/{PHIEN}", json=body)
        return r, ghi

    def test_khach_sua_gia_tri_nhan_vien_da_ghi_thanh_de_xuat_khong_im_lang(self):
        r, ghi = self._khach_patch(ho_so(), {"fields": {"japanese_level": "N5"}})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["fields"]["japanese_level"]["value"], "N4")
        # Có ghi xuống thì ô đã xác minh vẫn phải nguyên.
        if self.da_ghi:
            self.assertEqual(self.da_ghi["fields"]["japanese_level"]["value"], "N4")
        self.assertEqual(body["de_xuat_cho_nhan_vien"][0]["gia_tri_de_xuat"], "N5")
        ghi.assert_awaited_once()
        self.assertEqual(ghi.await_args.args[1][0]["field"], "japanese_level")

    def test_o_nhan_vien_nhap_khong_can_cu_thi_khach_sua_duoc_va_bao_nhan_vien(self):
        """Nhân viên ghi chưa chắc là đã xác minh (08/10, bản 2): ô nguồn `staff` không có
        căn cứ đối chứng thì KHÔNG khóa; khách sửa được, nhân viên nhận một dòng thông báo."""
        from app.api import profiles as api
        from tests.cookie_phien import cookies_cho
        hs = ho_so(fields={"full_name": store.cell("Lê Thị Minh", "user_confirmed"),
                           "experience_years": store.cell(1, "staff")})
        bao = AsyncMock()
        ghi = AsyncMock(side_effect=lambda *a, **k: {**hs, "fields": k["fields"], "version": 4})
        with patch.object(store, "get_by_session", AsyncMock(return_value=hs)), \
             patch.object(store, "apply_changes", ghi), \
             patch.object(store, "ghi_de_xuat", AsyncMock()) as de_xuat, \
             patch.object(store, "ghi_thong_bao_khach_sua", bao):
            with app_voi(api.public_router) as c:
                c.cookies.update(cookies_cho(PHIEN))
                r = c.patch(f"/public/profiles/{PHIEN}", json={"fields": {"experience_years": 3}})
        self.assertEqual(r.json()["fields"]["experience_years"]["value"], 3)
        self.assertEqual(r.json()["de_xuat_cho_nhan_vien"], [])
        de_xuat.assert_not_awaited()
        bao.assert_awaited_once()

    def test_so_tuyen_khong_xuat_trinh_khong_khoa(self):
        """Nhân viên ghi N4 nhưng khách không xuất trình gì → không có căn cứ → không khóa."""
        o = {**store.cell("N4", "staff"), "verification": "claimed", "evidence_type": "khong_xuat_trinh"}
        self.assertFalse(store.da_xac_minh_co_can_cu(o))
        self.assertEqual(store.o_bi_giu({"japanese_level": o}, {"japanese_level": "N5"}, source="user_confirmed"), [])
        gop, doi = store.merge_section({"japanese_level": o}, {"japanese_level": "N5"},
                                       source="user_confirmed", allowed=store.FIELD_KEYS)
        self.assertEqual((gop["japanese_level"]["value"], doi), ("N5", ["japanese_level"]))

    def test_cv_van_khong_de_duoc_o_nhan_vien_nhap(self):
        gop, doi = store.merge_section({"experience_years": store.cell(1, "staff")}, {"experience_years": 5},
                                       source="cv", allowed=store.FIELD_KEYS)
        self.assertEqual((gop["experience_years"]["value"], doi), (1, []))

    def test_ban_cho_khach_khong_lo_email_nhan_vien(self):
        r, _ = self._khach_patch(ho_so(), {"fields": {"full_name": "Lê Thị Minh Anh"}})
        self.assertNotIn(A["email"], json.dumps(r.json(), ensure_ascii=False))
        self.assertEqual(r.json()["fields"]["japanese_level"]["verification"], "verified")

    def test_nhan_vien_doi_gia_tri_thi_nhan_cu_vao_lich_su_va_dong_de_xuat(self):
        from app.api import profiles as api
        cu = ho_so(consultation={"conflicts": [{"field": "japanese_level", "suggested": "N5",
                                                "kind": store.LOAI_DE_XUAT_NHAN_VIEN, "trang_thai": store.DE_XUAT_CHO}]})
        ghi = AsyncMock(side_effect=lambda *a, **k: {**cu, "fields": k["fields"], "consultation": k["consultation"], "version": 4})
        with patch.object(store, "get_by_code", AsyncMock(return_value=cu)), \
             patch.object(api.quyen_ho_so, "co_quyen_ho_so", AsyncMock(return_value=True)), \
             patch.object(store, "apply_changes", ghi), \
             patch.object(api, "audit_action", AsyncMock()):
            with app_voi(api.router, nguoi=A) as c:
                r = c.patch("/profiles/UV-AAA111", json={"fields": {"japanese_level": "N3"}})
        o = r.json()["fields"]["japanese_level"]
        self.assertEqual(o["value"], "N3")
        self.assertNotIn("verification", o, "nhãn xác minh cũ không được bám vào giá trị mới")
        tu_van = ghi.await_args.kwargs["consultation"]
        self.assertEqual(tu_van["lich_su_xac_minh"][0]["value"], "N4")
        self.assertEqual(tu_van["lich_su_xac_minh"][0]["verified_by"], A["email"])
        self.assertEqual(tu_van["conflicts"][0]["trang_thai"], store.DE_XUAT_DA_XU_LY)

    def test_tro_ly_xac_nhan_o_nhan_vien_da_ghi_tra_ma_on_dinh(self):
        from app.api import agent
        from tests.cookie_phien import cookies_cho
        ghi = AsyncMock()
        with patch.object(agent.profiles, "get_by_session", AsyncMock(return_value=ho_so())), \
             patch.object(agent.profiles, "ghi_de_xuat", ghi):
            with app_voi(agent.public_router) as c:
                c.cookies.update(cookies_cho(PHIEN))
                r = c.post(f"/tu-van/v1/{PHIEN}/tro-ly/xac-nhan", json={"field": "japanese_level", "value": "N5"})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["detail"]["code"], "gia_tri_nhan_vien_da_ghi")
        ghi.assert_awaited_once()


class DocHoSoTuYeuCauHoTroTests(unittest.IsolatedAsyncioTestCase):
    async def _quyen(self, nguoi, yeu_cau, *, chi_doc=True):
        from app.services import quyen_ho_so
        from app.db import support_requests as ht
        hs = {"code": "UV-X", "session_id": PHIEN, "assigned_to": None}

        async def ds(*, status, assigned_to, limit):
            return [y for y in yeu_cau if y["assigned_to"] == assigned_to and y["status"] == status]
        with patch.object(ht, "list_requests", ds), \
             patch.object(quyen_ho_so, "ma_ho_so_qua_don", AsyncMock(return_value=set())):
            return await quyen_ho_so.co_quyen_ho_so(hs, nguoi, chi_doc=chi_doc)

    def _yc(self, nguoi, dong_y):
        return {"session_id": PHIEN, "assigned_to": nguoi["email"], "status": "dang_xu_ly", "dong_y_ban_giao": dong_y}

    async def test_nguoi_giu_co_dong_y_doc_duoc(self):
        self.assertTrue(await self._quyen(B, [self._yc(B, True)]))

    async def test_khong_dong_y_hoac_ban_ghi_cu_thi_khong(self):
        self.assertFalse(await self._quyen(B, [self._yc(B, False)]))
        cu = {k: v for k, v in self._yc(B, True).items() if k != "dong_y_ban_giao"}
        self.assertFalse(await self._quyen(B, [cu]))

    async def test_chuyen_viec_thi_nguoi_cu_mat_quyen(self):
        self.assertFalse(await self._quyen(A, [self._yc(B, True)]))

    async def test_chi_doc_khong_cho_sua(self):
        self.assertFalse(await self._quyen(B, [self._yc(B, True)], chi_doc=False))


class GhiChuNoiBoDonTests(unittest.TestCase):
    def _doc(self, nguoi):
        from app.api import job_orders as api
        don = {"code": "DH-0001", "title": "x", "status": "open", "internal_note": "CHI_QUAN_LY",
               "consultant_note": "CHO_TU_VAN", "requirements": {}, "reference": {}}
        with patch.object(api.store, "get_job_order", AsyncMock(return_value=don)):
            with app_voi(api.router, nguoi=nguoi) as c:
                return c.get("/job-orders/DH-0001").json()

    def test_internal_note_chi_quan_ly(self):
        self.assertNotIn("internal_note", self._doc(B))
        self.assertEqual(self._doc(B)["consultant_note"], "CHO_TU_VAN")
        self.assertEqual(self._doc(QUAN_LY)["internal_note"], "CHI_QUAN_LY")

    def test_ca_hai_khong_ra_cong_khai(self):
        from app.db import job_orders
        self.assertIn("internal_note", job_orders.PUBLIC_EXCLUDED_FIELDS)
        self.assertIn("consultant_note", job_orders.PUBLIC_EXCLUDED_FIELDS)


class BonTrangThaiTiengNhatTests(unittest.TestCase):
    def _tt(self, **o):
        return store.trang_thai_tieng_nhat({"fields": {"japanese_level": {"value": "N4", "source": "staff", **o}}})

    def test_bon_trang_thai(self):
        self.assertEqual(self._tt()["ma"], store.TT_TU_KHAI)
        self.assertEqual(self._tt(verification="claimed", evidence_type="khong_xuat_trinh")["ma"], store.TT_TU_KHAI)
        self.assertEqual(self._tt(verification="center")["ma"], store.TT_HOAN_THANH_TRUNG_TAM)
        self.assertEqual(self._tt(verification="verified", evidence_type="ban_goc")["ma"], store.TT_CO_CHUNG_CHI)
        dang = store.trang_thai_tieng_nhat({"fields": {"japanese_level": {"value": "N5"}},
                                            "hoc_tap": {"trang_thai": "dang_hoc", "muc_tieu": "N4"}})
        self.assertEqual(dang["muc"], "N5", "đang học N4 không được thành N4")
        self.assertIn("chưa phải trình độ đã có", dang["dang_hoc"]["nhan"])


class HocTapTests(unittest.TestCase):
    def _ghi(self, body):
        from app.api import profiles as api
        ghi = AsyncMock(side_effect=lambda *a, **k: {**ho_so(), "fields": k["fields"], "hoc_tap": k["extra"]["hoc_tap"]})
        with patch.object(store, "get_by_code", AsyncMock(return_value=ho_so(fields={"full_name": store.cell("X", "user_confirmed"), "japanese_level": store.cell("N5", "user_confirmed")}))), \
             patch.object(api.quyen_ho_so, "co_quyen_ho_so", AsyncMock(return_value=True)), \
             patch.object(store, "apply_changes", ghi), \
             patch("app.db.courses.get_course", AsyncMock(return_value={"code": "KH-0001"})), \
             patch.object(api, "audit_action", AsyncMock()):
            with app_voi(api.router, nguoi=A) as c:
                return c.post("/profiles/UV-AAA111/hoc-tap", json=body), ghi

    def test_dang_hoc_khong_doi_trinh_do(self):
        r, ghi = self._ghi({"trang_thai": "dang_hoc", "muc_tieu": "N4", "khoa_code": "KH-0001"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ghi.await_args.kwargs["fields"]["japanese_level"]["value"], "N5")
        self.assertEqual(r.json()["trang_thai_tieng_nhat"]["ma"], store.TT_TU_KHAI)
        self.assertIsNotNone(r.json()["trang_thai_tieng_nhat"]["dang_hoc"])

    def test_hoan_thanh_chuong_trinh_khong_doi_trinh_do_doi_chieu(self):
        """Quyết định 08/10: hoàn thành chương trình N4 tại trung tâm chưa phải chứng chỉ,
        không tự coi tương đương yêu cầu chứng chỉ của đơn."""
        r, ghi = self._ghi({"trang_thai": "da_hoan_thanh", "muc_tieu": "N4", "ket_qua": "N4"})
        o = ghi.await_args.kwargs["fields"]["japanese_level"]
        self.assertEqual((o["value"], o["source"]), ("N5", "user_confirmed"))
        self.assertNotIn("verification", o)
        tt = r.json()["trang_thai_tieng_nhat"]
        self.assertEqual(tt["ma"], store.TT_TU_KHAI)
        self.assertEqual(tt["chuong_trinh"]["nhan"], "Hoàn thành chương trình N4 tại trung tâm — chưa xác minh chứng chỉ")

    def test_ket_qua_khi_chua_hoan_thanh_bi_tu_choi(self):
        r, _ = self._ghi({"trang_thai": "dang_hoc", "muc_tieu": "N4", "ket_qua": "N4"})
        self.assertEqual(r.status_code, 422)


class DeXuatKhongTrungTests(unittest.IsolatedAsyncioTestCase):
    async def test_gui_lai_cung_de_xuat_khong_them_dong(self):
        dang = ho_so(consultation={"conflicts": [{"field": "japanese_level", "suggested": "N5",
                                                  "kind": store.LOAI_DE_XUAT_NHAN_VIEN, "trang_thai": store.DE_XUAT_CHO}]})
        kho = AsyncMock()
        with patch.object(store, "get_by_session", AsyncMock(return_value=dang)), \
             patch.object(store, "get_db", return_value={store.COLLECTION: kho}):
            await store.ghi_de_xuat(PHIEN, [{"field": "japanese_level", "gia_tri_nhan_vien": "N4", "gia_tri_de_xuat": "N5"}],
                                    source="user_confirmed", by="x")
        kho.update_one.assert_not_called()


# --- D. Hồ sơ chưa xác nhận qua API trực tiếp -----------------------------------


class ChuaXacNhanTests(unittest.TestCase):
    def test_tu_van_theo_don_tra_ma_on_dinh(self):
        from app.api import consultation_room as phong
        from tests.cookie_phien import cookies_cho
        chay = AsyncMock()
        with patch.object(phong.profiles, "get_by_session", AsyncMock(return_value=ho_so(status="extracted"))), \
             patch.object(phong.matching_service, "run_matching", chay):
            with app_voi(phong.public_router) as c:
                c.cookies.update(cookies_cho(PHIEN))
                r = c.get(f"/tu-van/v1/{PHIEN}/don/DH-0001?dien_dat=false")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["detail"]["code"], store.MA_CHUA_XAC_NHAN)
        chay.assert_not_awaited()

    def test_ly_do_chi_tiet_chan_chua_xac_nhan_va_khong_dung_nhat_ky_cu(self):
        from app.api import matching
        from tests.cookie_phien import cookies_cho
        with app_voi(matching.public_router) as c:
            c.cookies.update(cookies_cho(PHIEN))
            with patch.object(matching.profile_store, "get_by_session", AsyncMock(return_value=ho_so(status="extracted"))):
                r = c.get(f"/public/matches/{PHIEN}/orders/DH-0001")
            self.assertEqual(r.json()["detail"]["code"], store.MA_CHUA_XAC_NHAN)

            cu = {"code": "RL-CU", "profile_version": 2, "items": [{"code": "DH-0001", "cu": True}]}
            moi = {"code": "RL-MOI", "profile_version": 3, "items": [{"code": "DH-0001", "cu": False}]}
            chay = AsyncMock(return_value=(moi, False))
            with patch.object(matching.profile_store, "get_by_session", AsyncMock(return_value=ho_so())), \
                 patch.object(matching.log_store, "latest_for_profile", AsyncMock(return_value=cu)), \
                 patch.object(matching.matching_service, "run_matching", chay), \
                 patch.object(matching.matching_service, "public_item", side_effect=lambda i: i):
                r = c.get(f"/public/matches/{PHIEN}/orders/DH-0001")
        chay.assert_awaited_once()
        self.assertFalse(r.json()["cu"], "dùng nhật ký của phiên bản hồ sơ cũ")


# --- E. Điểm trung lập và lý do chưa rõ -----------------------------------------


class ChiPhiChuaRoTests(unittest.TestCase):
    def _dong(self, cost, budget):
        from app.matching import engine
        from app.matching.weights import load_weights
        facts = engine.build_facts({"fields": {}, "preferences": (
            {"budget_vnd": store.cell(budget, "user_confirmed")} if budget else {})}, __import__("datetime").date(2026, 10, 8))
        don = {"prefecture": "Tokyo", "region_group": "kanto", "employer_type": "vien_duong_lao",
               "reference": {"cost_total_vnd": cost} if cost else {}}
        return next(r for r in engine.evaluate_soft(don, facts, load_weights()) if r.key == "cost")

    def test_phan_biet_khach_chua_neu_va_don_chua_cong_bo(self):
        self.assertEqual(self._dong(90_000_000, None).unknown_reasons, ("khach_chua_neu",))
        self.assertEqual(self._dong(None, 100_000_000).unknown_reasons, ("don_chua_cong_bo",))
        self.assertEqual(self._dong(None, None).unknown_reasons, ("khach_chua_neu", "don_chua_cong_bo"))
        self.assertEqual(self._dong(90_000_000, 100_000_000).unknown_reasons, ())

    def test_trong_so_giu_nguyen_va_khoi_ai_ghi_trung_lap(self):
        from app.matching import explain
        dong = self._dong(None, 100_000_000)
        self.assertEqual(dong.points, 5, "cost.unknown vẫn là 5 trong đợt này")
        self.assertIn("trung lập", explain._outcome_text(dong))
        self.assertIn("không phải điểm mạnh", explain._outcome_text(dong))

    def test_nhat_ky_cu_suy_duoc_ly_do(self):
        from app.matching import engine
        cu = {"key": "cost", "label": "Chi phí", "requirement_text": "chưa rõ chi phí",
              "candidate_text": "khả năng 1 đ", "outcome": "unknown", "points": 5, "max_points": 10,
              "missing_field": None, "kind": "mem"}
        self.assertEqual(engine.SoftRow.tu_ban_ghi(cu).unknown_reasons, ("don_chua_cong_bo",))


class KhoaThoTests(unittest.TestCase):
    def test_luot_cu_hien_nhan_tieng_viet(self):
        from app.db.advisor_turns import _khoa_tho_thanh_nhan
        self.assertEqual(_khoa_tho_thanh_nhan("Hồ sơ còn thiếu: experience_years, budget_vnd."),
                         "Hồ sơ còn thiếu: Kinh nghiệm, Ngân sách.")


# --- F. Ngữ cảnh AI: dữ liệu nhân viên được phép, không gì khác ------------------


class TienDoTests(unittest.IsolatedAsyncioTestCase):
    async def test_khoi_tien_do_chi_co_du_lieu_duoc_phep(self):
        from app.consultation import tien_do
        dang_ky = [{"job_order_code": "DH-0001", "job_order_title": "Điều dưỡng Tokyo", "status": "screening",
                    "note": "GHI_CHU_NOI_BO_HS", "assigned_to": A["email"], "updated_at": "2026-10-08"}]
        lich = [{"appointment_date": "2026-10-09", "appointment_time": "10:00", "meeting_kind": "truc_tuyen",
                 "status": "confirmed", "result_note": "GHI_CHU_NOI_BO_LICH", "assigned_to": A["email"]}]
        with patch("app.db.database.list_unassigned_registrations", AsyncMock(return_value=dang_ky)), \
             patch("app.db.job_orders.get_job_order", AsyncMock(return_value={"code": "DH-0001", "internal_note": "GHI_CHU_DON"})), \
             patch("app.db.database.list_appointments_for_session", AsyncMock(return_value=lich)), \
             patch("app.db.support_requests.list_for_session", AsyncMock(return_value=[{"kind": "hoc_tap", "status": "dang_xu_ly", "assigned_to": A["email"]}])):
            khoi = tien_do.render(await tien_do.nap(PHIEN, ho_so(hoc_tap={"trang_thai": "dang_hoc", "muc_tieu": "N3"})))
        for co in ("có chứng chỉ", "Đang xem xét", "DH-0001", "2026-10-09", "đang học hướng tới N3", "nhân viên đang xử lý"):
            self.assertIn(co, khoi)
        for khong in ("GHI_CHU_NOI_BO_HS", "GHI_CHU_NOI_BO_LICH", "GHI_CHU_DON", A["email"], "screening"):
            self.assertNotIn(khong, khoi)

    @unittest.skipUnless(CO_CAY_MA_DAY_DU, LY_DO_BO_QUA)
    def test_chang_khop_trang_khach(self):
        """Trợ lý nói đúng chặng khách thấy ở "Hồ sơ của tôi" — so với bảng của giao diện."""
        from app.consultation import tien_do
        ts = (Path(__file__).resolve().parents[2] / "frontend" / "lib" / "applicationStages.ts").read_text(encoding="utf-8")
        nhan = dict(re.findall(r'key: "(\w+)",\s*label: "([^"]+)"', ts))
        chang = dict(re.findall(r"^\s+(\w+): \"(\w+)\",$", ts.split("const STAGE_OF")[1].split("};")[0], re.M))
        for trang_thai, khoa in chang.items():
            self.assertEqual(tien_do.CHANG_CUA_TRANG_THAI[trang_thai], nhan[khoa], trang_thai)


class GhiChuNoiBoKhongVaoPromptTests(unittest.IsolatedAsyncioTestCase):
    async def test_phong_theo_don(self):
        from fastapi import Request
        from app.api import consultation_room as phong
        from app.services import matching_service
        from scripts.seed_job_orders import build_documents
        from app.matching import engine
        from app.matching.weights import load_weights
        from app.core.timeutil import local_today

        don = {**next(d for d in build_documents() if d["code"] == "DH-0001"), "internal_note": "GHI_CHU_NOI_BO_DON"}
        hs = {"code": "UV-1", "session_id": PHIEN, "status": "confirmed", "version": 1,
              "fields": {"full_name": store.cell("X", "user_confirmed"), "japanese_level": store.cell("N4", "user_confirmed")},
              "preferences": {}}
        item = engine.match_orders([don], engine.build_facts(hs, local_today()), weights=load_weights(), as_of=local_today()).as_dict()["items"][0]
        item = {**item, "hard_rows": [matching_service._bo_nhan_suy_ra(r) for r in item["hard_rows"]]}  # đúng hình nhật ký lưu

        async def _run(profile, *, trigger, chi_don=None, **_):
            return {"code": "RL-1", "as_of": local_today().isoformat(), "profile_version": 1,
                    "items": [item], "total_considered": 1}, True

        goi = AsyncMock(return_value=("Được.", "ok", "m"))
        with patch.object(phong.profiles, "get_by_session", AsyncMock(return_value=hs)), \
             patch.object(phong.job_orders, "get_job_order", AsyncMock(return_value=don)), \
             patch.object(matching_service, "run_matching", _run), \
             patch.object(matching_service, "load_pool", AsyncMock(return_value=[don])), \
             patch.object(phong.courses, "list_published", AsyncMock(return_value=[])), \
             patch.object(phong.advisor_turns, "count_turns", AsyncMock(return_value=0)), \
             patch.object(phong.advisor_turns, "list_turns", AsyncMock(return_value=[])), \
             patch.object(phong.advisor_turns, "add_turn", AsyncMock(return_value={"question": "q"})), \
             patch.object(phong.session_memory, "ghi_moi_quan_tam", AsyncMock()), \
             patch.object(phong.session_memory, "ghi_da_giai_thich", AsyncMock()), \
             patch.object(phong.session_memory, "lay", AsyncMock(return_value={})), \
             patch.object(phong.tien_do, "nap", AsyncMock(return_value={})), \
             patch.object(phong.qa.client, "sinh_van_ban", goi):
            await phong.hoi_them(PHIEN, "DH-0001", phong.CauHoiBody(question="Đơn này có gì cần biết?"),
                                 Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1)}))
        self.assertNotIn("GHI_CHU_NOI_BO_DON", goi.await_args.args[0])


if __name__ == "__main__":
    unittest.main()
