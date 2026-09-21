"""Kiểm thử phân công sở hữu: chuyển tay, trả về hàng đợi, và thông báo.

Nguyên tắc của bước này: **một hồ sơ có một người phụ trách tại một thời điểm**.
Mọi ca dưới đây đều nhằm vào cách nguyên tắc đó có thể bị phá:

- hai lệnh chuyển xảy ra sát nhau, cả hai cùng nghĩ mình thành công;
- người ngoài tự nhận hoặc tự buông hồ sơ của người khác;
- hồ sơ bị bỏ lại vì người phụ trách nghỉ mà không ai gỡ ra được.
"""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, Request

from app.api import registrations as api


ADMIN = {"email": "admin@example.com", "full_name": "Quản trị", "role": "admin"}
MANAGER = {"email": "manager@example.com", "full_name": "Quản lý", "role": "manager"}
OWNER = {"email": "chu.ho.so@example.com", "full_name": "Người phụ trách", "role": "consultant"}
OTHER = {"email": "nguoi.khac@example.com", "full_name": "Người khác", "role": "consultant"}


def http_request() -> Request:
    return Request({"type": "http", "headers": [], "client": ("127.0.0.1", 12345)})


def application(**overrides) -> dict:
    document = {
        "application_code": "HS-CCC333",
        "customer_name": "Trần Thị Mai Hương",
        "status": "collecting_documents",
        "assigned_to": OWNER["email"],
        "source": "self_registration",
    }
    document.update(overrides)
    return document


class HandoverTests(unittest.IsolatedAsyncioTestCase):
    def _mocks(self, existing, updated):
        return {
            "get": patch.object(api, "get_recruitment_application", AsyncMock(return_value=existing)),
            "update": patch.object(api, "update_recruitment_application", AsyncMock(return_value=updated)),
            "event": patch.object(api, "create_application_event", AsyncMock()),
            "notify": patch.object(api, "create_notification", AsyncMock()),
            "audit": patch.object(api, "audit_action", AsyncMock()),
            "validate": patch.object(api, "validate_assignee", AsyncMock(side_effect=lambda email: email)),
        }

    async def _handover(self, existing, updated, actor, assigned_to=OTHER["email"]):
        mocks = self._mocks(existing, updated)
        payload = api.HandoverRequest(assigned_to=assigned_to, note="Bạn ấy nghỉ phép dài ngày")
        with (
            mocks["get"] as get,
            mocks["update"] as update,
            mocks["event"] as event,
            mocks["notify"] as notify,
            mocks["audit"],
            mocks["validate"],
        ):
            result = await api.handover("HS-CCC333", payload, http_request(), actor)
            return result, {"get": get, "update": update, "event": event, "notify": notify}

    async def test_quan_ly_chuyen_duoc(self):
        updated = application(assigned_to=OTHER["email"])
        result, mocks = await self._handover(application(), updated, MANAGER)

        self.assertEqual(result["assigned_to"], OTHER["email"])
        kwargs = mocks["update"].await_args.kwargs
        self.assertEqual(
            kwargs["owner_email"],
            OWNER["email"],
            "phải khóa theo người đang giữ, không thì đè lên lần chuyển khác",
        )
        self.assertEqual(kwargs["expected_status"], "collecting_documents")

    async def test_tu_van_vien_khong_duoc_chuyen_cho_nguoi_khac(self):
        with self.assertRaises(HTTPException) as ctx:
            await self._handover(application(), application(), OWNER)
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_chuyen_cho_chinh_nguoi_dang_giu_thi_bao_loi(self):
        with self.assertRaises(HTTPException) as ctx:
            await self._handover(application(), application(), ADMIN, assigned_to=OWNER["email"])
        self.assertEqual(ctx.exception.status_code, 409)

    async def test_hai_lenh_chuyen_sat_nhau_thi_lenh_sau_that_bai(self):
        """Cập nhật trả `None` nghĩa là người giữ đã đổi giữa chừng."""
        with self.assertRaises(HTTPException) as ctx:
            await self._handover(application(), None, ADMIN)
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("tải lại", ctx.exception.detail)

    async def test_ghi_lai_ai_chuyen_cho_ai_va_vi_sao(self):
        _, mocks = await self._handover(application(), application(assigned_to=OTHER["email"]), ADMIN)
        details = mocks["event"].await_args.args[0]["details"]
        self.assertEqual(details["from"], OWNER["email"])
        self.assertEqual(details["to"], OTHER["email"])
        self.assertEqual(details["note"], "Bạn ấy nghỉ phép dài ngày")

    async def test_bao_cho_nguoi_duoc_giao(self):
        _, mocks = await self._handover(application(), application(assigned_to=OTHER["email"]), ADMIN)
        kwargs = mocks["notify"].await_args.kwargs
        self.assertEqual(kwargs["reference_type"], api.REFERENCE_APPLICATION)
        self.assertEqual(kwargs["reference_code"], "HS-CCC333")
        self.assertEqual(kwargs["detail"]["assigned_to"], OTHER["email"])

    async def test_bat_buoc_ghi_ly_do(self):
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            api.HandoverRequest(assigned_to=OTHER["email"], note="")


class ReleaseTests(unittest.IsolatedAsyncioTestCase):
    async def _release(self, existing, updated, actor):
        payload = api.ReleaseRequest(note="Nhận nhầm, trả lại hàng đợi")
        with (
            patch.object(api, "get_recruitment_application", AsyncMock(return_value=existing)),
            patch.object(api, "update_recruitment_application", AsyncMock(return_value=updated)) as update,
            patch.object(api, "create_application_event", AsyncMock()) as event,
            patch.object(api, "create_notification", AsyncMock()),
            patch.object(api, "audit_action", AsyncMock()),
        ):
            result = await api.release("HS-CCC333", payload, http_request(), actor)
            return result, {"update": update, "event": event}

    async def test_chinh_nguoi_phu_trach_tra_duoc_ve_hang_doi(self):
        """Không cần quyền quản lý: chờ quản lý thì hồ sơ nằm chết ở đó."""
        updated = application(assigned_to=None)
        result, mocks = await self._release(application(), updated, OWNER)

        self.assertIsNone(result["assigned_to"])
        self.assertIsNone(mocks["update"].await_args.args[1]["assigned_to"])
        self.assertEqual(mocks["update"].await_args.kwargs["owner_email"], OWNER["email"])

    async def test_quan_ly_cung_tra_duoc(self):
        result, _ = await self._release(application(), application(assigned_to=None), ADMIN)
        self.assertIsNone(result["assigned_to"])

    async def test_nguoi_ngoai_khong_tra_duoc_ho_so_cua_nguoi_khac(self):
        with self.assertRaises(HTTPException) as ctx:
            await self._release(application(), application(), OTHER)
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_ho_so_chua_ai_nhan_thi_khong_co_gi_de_tra(self):
        with self.assertRaises(HTTPException) as ctx:
            await self._release(application(assigned_to=None), None, ADMIN)
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("chưa ai nhận", ctx.exception.detail)

    async def test_ghi_lai_ly_do_tra_ve(self):
        _, mocks = await self._release(application(), application(assigned_to=None), OWNER)
        event = mocks["event"].await_args.args[0]
        self.assertEqual(event["action"], "released")
        self.assertEqual(event["details"]["note"], "Nhận nhầm, trả lại hàng đợi")


class NotificationRoutingTests(unittest.IsolatedAsyncioTestCase):
    """Thông báo của nghiệp vụ khác phải tắt được — đây là lý do phải gỡ nó ra."""

    async def test_tat_duoc_thong_bao_ho_so_chua_ai_nhan(self):
        from app.api import appointments

        notification = {"reference_type": "application", "reference_code": "HS-CCC333"}
        with (
            patch.object(appointments, "get_notification_by_reference", AsyncMock(return_value=notification)),
            patch.object(appointments, "get_recruitment_application", AsyncMock(return_value=application(assigned_to=None))),
            patch.object(appointments, "mark_notification_read", AsyncMock(return_value=True)),
        ):
            result = await appointments.read_notification("HS-CCC333", OTHER)
        self.assertTrue(result["is_read"])

    async def test_nguoi_ngoai_khong_tat_duoc_thong_bao_ho_so_da_giao(self):
        from app.api import appointments

        notification = {"reference_type": "application", "reference_code": "HS-CCC333"}
        with (
            patch.object(appointments, "get_notification_by_reference", AsyncMock(return_value=notification)),
            patch.object(appointments, "get_recruitment_application", AsyncMock(return_value=application())),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await appointments.read_notification("HS-CCC333", OTHER)
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_thong_bao_lich_hen_van_theo_quy_tac_cu(self):
        from app.api import appointments

        notification = {"reference_type": "appointment", "reference_code": "LH-001"}
        with (
            patch.object(appointments, "get_notification_by_reference", AsyncMock(return_value=notification)),
            patch.object(appointments, "require_appointment_access", AsyncMock()) as guard,
            patch.object(appointments, "mark_notification_read", AsyncMock(return_value=True)),
        ):
            await appointments.read_notification("LH-001", OWNER)
        guard.assert_awaited_once()

    async def test_khong_co_thong_bao_thi_bao_404(self):
        from app.api import appointments

        with patch.object(appointments, "get_notification_by_reference", AsyncMock(return_value=None)):
            with self.assertRaises(HTTPException) as ctx:
                await appointments.read_notification("HS-KHONG-CO", ADMIN)
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
