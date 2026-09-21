"""Kiểm thử đăng ký sơ bộ, phiếu tóm tắt và hàng đợi.

Ba điều được soi kỹ nhất:

1. **Không đăng ký được đơn chưa từng được giới thiệu.** Đây là chốt chặn giữ cho
   câu "hệ thống không tự quyết thay ứng viên" là sự thật trong mã nguồn, chứ
   không chỉ là một dòng trong tài liệu thiết kế.
2. **Phiếu không được sinh ra từ mô hình ngôn ngữ.** Nhân viên đọc phiếu rồi gọi
   điện nói lại; một con số bịa ở đây sẽ đi thẳng ra ngoài qua miệng người thật.
3. **Hai người nhận cùng một hồ sơ thì chỉ một người thắng.** Nếu cả hai cùng
   thắng, ứng viên nhận hai cuộc gọi từ cùng một công ty.
"""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, Request

from app.api import registrations as api
from app.db import candidate_profiles as store
from app.services import registration_service as service
from app.services import report_builder


SESSION = "phien-ung-vien-0001"
ADMIN = {"email": "admin@example.com", "full_name": "Quản trị", "role": "admin"}
CONSULTANT = {"email": "tu.van@example.com", "full_name": "Tư vấn", "role": "consultant"}
OTHER = {"email": "nguoi.khac@example.com", "full_name": "Người khác", "role": "consultant"}


def http_request() -> Request:
    return Request({"type": "http", "headers": [], "client": ("127.0.0.1", 12345)})


def profile_doc(**overrides) -> dict:
    document = {
        "code": "UV-ABC123",
        "session_id": SESSION,
        "status": store.STATUS_CONFIRMED,
        "version": 2,
        "fields": {
            "full_name": store.cell("Trần Thị Mai Hương", "user_confirmed"),
            "japanese_level": store.cell("N3", "cv", "đã thi đỗ JLPT N3"),
            "phone": store.cell("0987654321", "user_confirmed"),
            "education_level": store.cell("cao_dang", "cv", "Tốt nghiệp Cao đẳng Điều dưỡng"),
        },
        "preferences": {"desired_prefecture": store.cell("tokyo", "chat")},
    }
    document.update(overrides)
    return document


def match_item(**overrides) -> dict:
    item = {
        "code": "DH-0016",
        "title": "Hộ lý viện dưỡng lão Sendai",
        "employer_name": "Sendai Care",
        "prefecture": "miyagi",
        "region_group": "tohoku",
        "employer_type": "vien_duong_lao",
        "program": "tokutei",
        "deadline": "2026-12-31",
        "eligible": True,
        "score": 82,
        "rank": 1,
        "hard_rows": [],
        "soft_rows": [],
        "gaps": ["Chưa có chứng chỉ chăm sóc"],
        "missing_info": [],
        "labels": {},
    }
    item.update(overrides)
    return item


def log_doc(items=None) -> dict:
    return {"code": "RL-AAA111", "profile_code": "UV-ABC123", "items": items or [match_item()]}


class GuardrailTests(unittest.IsolatedAsyncioTestCase):
    """Những trường hợp phải bị từ chối."""

    async def _register(self, *, profile, log, job_order_code="DH-0016"):
        with (
            patch.object(service.profiles, "get_by_session", AsyncMock(return_value=profile)),
            patch.object(service.logs, "latest_for_profile", AsyncMock(return_value=log)),
        ):
            return await service.register(
                session_id=SESSION, job_order_code=job_order_code
            )

    async def test_chua_co_ho_so(self):
        with self.assertRaises(service.RegistrationRejected):
            await self._register(profile=None, log=log_doc())

    async def test_ho_so_chua_xac_nhan(self):
        profile = profile_doc(status=store.STATUS_EXTRACTED)
        with self.assertRaises(service.RegistrationRejected) as ctx:
            await self._register(profile=profile, log=log_doc())
        self.assertIn("xác nhận hồ sơ", str(ctx.exception))

    async def test_thieu_so_dien_thoai(self):
        profile = profile_doc()
        del profile["fields"]["phone"]
        with self.assertRaises(service.RegistrationRejected) as ctx:
            await self._register(profile=profile, log=log_doc())
        self.assertIn("số điện thoại", str(ctx.exception))

    async def test_chua_tung_xem_don_nao(self):
        with self.assertRaises(service.RegistrationRejected):
            await self._register(profile=profile_doc(), log=None)

    async def test_don_khong_nam_trong_danh_sach_da_gioi_thieu(self):
        """Gửi thẳng một mã đơn bất kỳ lên đường công khai — phải bị chặn."""
        with self.assertRaises(service.RegistrationRejected) as ctx:
            await self._register(
                profile=profile_doc(), log=log_doc(), job_order_code="DH-9999"
            )
        self.assertIn("không có trong danh sách", str(ctx.exception))

    async def test_don_khong_du_dieu_kien_thi_khong_dang_ky_duoc(self):
        log = log_doc([match_item(eligible=False, score=0, rank=None)])
        with self.assertRaises(service.RegistrationRejected) as ctx:
            await self._register(profile=profile_doc(), log=log)
        self.assertIn("chưa đạt điều kiện", str(ctx.exception))


class RegisterTests(unittest.IsolatedAsyncioTestCase):
    def _patches(self, **overrides):
        created_report = {"code": "PT-BBB222", "text": "PHIẾU TÓM TẮT TƯ VẤN"}
        defaults = {
            "get_by_session": AsyncMock(return_value=profile_doc()),
            "latest_for_profile": AsyncMock(return_value=log_doc()),
            "lead_by_phone": AsyncMock(return_value=None),
            "create_lead": AsyncMock(
                side_effect=lambda doc: {**doc, "phone": doc["phone"]}
            ),
            "create_application": AsyncMock(side_effect=lambda doc: dict(doc)),
            "update_application": AsyncMock(
                side_effect=lambda code, fields, **kw: {"application_code": code, **fields}
            ),
            "create_report": AsyncMock(return_value=created_report),
            "documents": AsyncMock(return_value=[]),
            "attach_lead": AsyncMock(),
            "attach_application": AsyncMock(),
            "create_event": AsyncMock(),
            "notify": AsyncMock(),
        }
        defaults.update(overrides)
        return defaults

    def _stack(self, mocks):
        from contextlib import ExitStack

        stack = ExitStack()
        for target, attribute, mock in (
            (service.profiles, "get_by_session", mocks["get_by_session"]),
            (service.logs, "latest_for_profile", mocks["latest_for_profile"]),
            (service.profiles, "attach_lead", mocks["attach_lead"]),
            (service.logs, "attach_application", mocks["attach_application"]),
            (service.documents, "list_for_profile", mocks["documents"]),
            (service.reports, "create", mocks["create_report"]),
        ):
            stack.enter_context(patch.object(target, attribute, mock))
        for name, mock in (
            ("get_managed_lead_by_phone", mocks["lead_by_phone"]),
            ("create_managed_lead", mocks["create_lead"]),
            ("create_recruitment_application", mocks["create_application"]),
            ("update_recruitment_application", mocks["update_application"]),
            ("create_application_event", mocks["create_event"]),
            ("create_notification", mocks["notify"]),
        ):
            stack.enter_context(patch.object(service, name, mock))
        return stack

    async def test_tao_du_ba_thu_va_nam_trong_hang_doi(self):
        mocks = self._patches()
        with self._stack(mocks):
            result = await service.register(session_id=SESSION, job_order_code="DH-0016")

        document = mocks["create_application"].await_args.args[0]
        self.assertEqual(document["status"], "draft")
        self.assertIsNone(document["assigned_to"], "phải nằm trong hàng đợi, chưa của ai")
        self.assertEqual(document["source"], service.SOURCE_SELF)
        self.assertEqual(document["job_order_code"], "DH-0016")
        self.assertEqual(document["profile_code"], "UV-ABC123")
        self.assertEqual(document["recommendation_log_code"], "RL-AAA111")
        self.assertEqual(result["report"]["code"], "PT-BBB222")
        mocks["create_lead"].assert_awaited_once()
        mocks["attach_application"].assert_awaited_once_with("RL-AAA111", document["application_code"])

        # Đẩy sang hệ thống nội bộ thì phải kèm thông báo, không chỉ nằm im
        # trong hàng đợi chờ ai đó tình cờ mở ra xem.
        notify = mocks["notify"].await_args.kwargs
        self.assertEqual(notify["reference_code"], document["application_code"])
        self.assertEqual(notify["reference_type"], "application")

    async def test_dung_lai_khach_hang_cu_theo_so_dien_thoai(self):
        existing = {"lead_code": "LD-OLD111", "customer_name": "Trần Thị Mai Hương", "phone": "0987654321"}
        mocks = self._patches(lead_by_phone=AsyncMock(return_value=existing))
        with self._stack(mocks):
            await service.register(session_id=SESSION, job_order_code="DH-0016")

        mocks["create_lead"].assert_not_awaited()
        self.assertEqual(
            mocks["create_application"].await_args.args[0]["lead_code"], "LD-OLD111"
        )

    async def test_dang_ky_lan_hai_khi_dang_co_ho_so_hoat_dong(self):
        from pymongo.errors import DuplicateKeyError

        mocks = self._patches(
            create_application=AsyncMock(side_effect=DuplicateKeyError("trùng"))
        )
        with self._stack(mocks):
            with self.assertRaises(service.AlreadyRegistered):
                await service.register(session_id=SESSION, job_order_code="DH-0016")


class ReportBuilderTests(unittest.TestCase):
    """Phiếu tóm tắt — dựng hoàn toàn bằng mã."""

    def setUp(self):
        self.profile = store.decorate(profile_doc())
        self.item = match_item()

    def _text(self) -> str:
        return report_builder.render_text(
            profile=self.profile,
            order_item=self.item,
            explanation_block="đơn DH-0016 · Sendai Care · miyagi\n  → tổng 82/100 · hạng 1",
            documents=[{"code": "CV-AAA111", "filename": "cv.docx", "status": "extracted"}],
        )

    def test_khong_import_mo_hinh_ngon_ngu(self):
        """Ràng buộc kiến trúc, không phải sở thích: phiếu phải kiểm chứng được."""
        import inspect

        source = inspect.getsource(report_builder)
        for forbidden in ("gemini", "generate_response", "llm"):
            self.assertNotIn(forbidden, source.lower())

    def test_co_du_cac_phan_nhan_vien_can(self):
        text = self._text()
        for heading in (
            "PHIẾU TÓM TẮT TƯ VẤN",
            "ỨNG VIÊN",
            "ĐƠN ỨNG VIÊN ĐÃ CHỌN",
            "VÌ SAO HỆ THỐNG CHO LÀ PHÙ HỢP",
        ):
            self.assertIn(heading, text)

    def test_so_muc_lien_tuc_khi_co_muc_bi_bo_trong(self):
        """Hồ sơ không có nguyện vọng thì phiếu không được nhảy từ 1 sang 3."""
        import re

        self.profile["preferences"] = {}
        numbers = [int(n) for n in re.findall(r"^(\d+)\. ", self._text(), re.M)]
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))

    def test_muc_rong_thi_khong_in_tieu_de(self):
        self.profile["preferences"] = {}
        self.assertNotIn("NGUYỆN VỌNG", self._text())

    def test_moi_gia_tri_deu_ghi_ro_nguon(self):
        text = self._text()
        self.assertIn("Trần Thị Mai Hương", text)
        self.assertIn("[ứng viên xác nhận]", text)
        self.assertIn("[đọc từ CV]", text)

    def test_nhan_tieng_viet_thay_cho_ma_danh_muc(self):
        text = self._text()
        self.assertIn("Cao đẳng", text)
        self.assertNotIn("cao_dang", text)

    def test_neu_ro_diem_con_thieu_de_nhan_vien_hoi_them(self):
        self.assertIn("Chưa có chứng chỉ chăm sóc", self._text())

    def test_khong_bia_them_truong_khong_co_trong_ho_so(self):
        text = self._text()
        self.assertNotIn("Năm sinh", text, "hồ sơ không khai năm sinh thì phiếu không được có")

    def test_liet_ke_tai_lieu_da_gui(self):
        self.assertIn("cv.docx", self._text())


class QueueTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.application = {
            "application_code": "HS-CCC333",
            "status": "draft",
            "assigned_to": None,
            "source": "self_registration",
        }

    async def test_nhan_viec_thanh_cong(self):
        updated = {**self.application, "assigned_to": CONSULTANT["email"]}
        with (
            patch.object(api, "get_recruitment_application", AsyncMock(return_value=self.application)),
            patch.object(api, "update_recruitment_application", AsyncMock(return_value=updated)) as update,
            patch.object(api, "create_application_event", AsyncMock()),
            patch.object(api, "audit_action", AsyncMock()),
        ):
            result = await api.accept("HS-CCC333", http_request(), CONSULTANT)

        self.assertEqual(result["assigned_to"], CONSULTANT["email"])
        self.assertTrue(
            update.await_args.kwargs["unassigned_only"],
            "phải khóa theo điều kiện chưa ai nhận",
        )

    async def test_nguoi_thu_hai_bam_nhan_thi_bi_tu_choi(self):
        """Cập nhật trả về None nghĩa là đã có người khác nhận trong tích tắc."""
        with (
            patch.object(api, "get_recruitment_application", AsyncMock(return_value=self.application)),
            patch.object(api, "update_recruitment_application", AsyncMock(return_value=None)),
            patch.object(api, "create_application_event", AsyncMock()),
            patch.object(api, "audit_action", AsyncMock()),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await api.accept("HS-CCC333", http_request(), OTHER)

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("vừa được người khác nhận", ctx.exception.detail)

    async def test_ho_so_da_co_nguoi_nhan_thi_bao_ngay(self):
        taken = {**self.application, "assigned_to": CONSULTANT["email"]}
        with patch.object(api, "get_recruitment_application", AsyncMock(return_value=taken)):
            with self.assertRaises(HTTPException) as ctx:
                await api.accept("HS-CCC333", http_request(), OTHER)
        self.assertEqual(ctx.exception.status_code, 409)

    async def test_ai_cung_doc_duoc_phieu_cua_ho_so_chua_ai_nhan(self):
        report = {"code": "PT-BBB222", "text": "..."}
        with (
            patch.object(api, "get_recruitment_application", AsyncMock(return_value=self.application)),
            patch.object(api.reports, "get_by_application", AsyncMock(return_value=report)),
        ):
            result = await api.registration_report("HS-CCC333", OTHER)
        self.assertEqual(result["code"], "PT-BBB222")

    async def test_ho_so_da_giao_thi_nguoi_ngoai_khong_doc_duoc_phieu(self):
        taken = {**self.application, "assigned_to": CONSULTANT["email"]}
        with patch.object(api, "get_recruitment_application", AsyncMock(return_value=taken)):
            with self.assertRaises(HTTPException) as ctx:
                await api.registration_report("HS-CCC333", OTHER)
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_quan_ly_van_doc_duoc_phieu_cua_ho_so_da_giao(self):
        taken = {**self.application, "assigned_to": CONSULTANT["email"]}
        with (
            patch.object(api, "get_recruitment_application", AsyncMock(return_value=taken)),
            patch.object(api.reports, "get_by_application", AsyncMock(return_value={"code": "PT-X"})),
        ):
            result = await api.registration_report("HS-CCC333", ADMIN)
        self.assertEqual(result["code"], "PT-X")


class PublicApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_khong_xac_nhan_thi_khong_dang_ky(self):
        payload = api.RegisterRequest(job_order_code="DH-0016", confirmed=False)
        with self.assertRaises(HTTPException) as ctx:
            await api.register(payload, http_request(), SESSION)
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_ung_vien_khong_nhan_duoc_noi_dung_phieu(self):
        created = {
            "application": {
                "application_code": "HS-CCC333",
                "job_order_code": "DH-0016",
                "job_order_title": "Hộ lý viện dưỡng lão Sendai",
                "status": "draft",
            },
            "report": {"code": "PT-BBB222", "text": "nội dung nội bộ"},
        }
        payload = api.RegisterRequest(job_order_code="DH-0016", confirmed=True)
        with patch.object(api.registration_service, "register", AsyncMock(return_value=created)):
            result = await api.register(payload, http_request(), SESSION)

        self.assertNotIn("report", result)
        self.assertNotIn("nội dung nội bộ", str(result))
        self.assertEqual(result["application_code"], "HS-CCC333")


if __name__ == "__main__":
    unittest.main()
