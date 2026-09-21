"""Kiểm thử danh mục đơn tuyển dụng: chuẩn hóa, ràng buộc và vòng đời trạng thái."""
import unittest
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, Request
from pydantic import ValidationError

from app.api.job_orders import (
    JobOrderCreateRequest,
    JobOrderPublishRequest,
    JobOrderStatusRequest,
    JobOrderUpdateRequest,
    change_job_order_status,
    create_job_order,
    delete_job_order,
    publish_job_order,
    public_job_orders,
    update_job_order,
)
from app.core.timeutil import age_on, local_today
from app.db import job_orders as store
from app.matching import catalog


def http_request() -> Request:
    return Request({"type": "http", "headers": [], "client": ("127.0.0.1", 12345)})


MANAGER = {"email": "manager@example.com", "full_name": "Quản lý", "role": "manager"}
ADMIN = {"email": "admin@example.com", "full_name": "Quản trị", "role": "admin"}


def valid_payload(**overrides) -> dict:
    data = {
        "title": "Điều dưỡng viện dưỡng lão Tokyo",
        "employer_name": "Viện dưỡng lão Sakura",
        "employer_type": "Viện dưỡng lão",
        "program": "Tokutei Ginou",
        "prefecture": "Tokyo",
        "quota": 5,
        "deadline": (local_today() + timedelta(days=60)).isoformat(),
        "requirements": {
            "japanese_required": "N4",
            "education_required": "Cao đẳng",
            "experience_min": 0,
            "age_min": 20,
            "age_max": 35,
            "gender_pref": "Không yêu cầu",
        },
        "reference": {"salary_min": 190000, "salary_max": 210000},
    }
    data.update(overrides)
    return data


class CatalogNormalizationTests(unittest.TestCase):
    def test_employer_type_accepts_label_and_code(self):
        for raw in ("Viện dưỡng lão", "vien duong lao", "VIEN_DUONG_LAO", "  Viện Dưỡng Lão  "):
            self.assertEqual(catalog.normalize_employer_type(raw), "vien_duong_lao")

    def test_prefecture_accepts_macrons_and_aliases(self):
        self.assertEqual(catalog.normalize_prefecture("Tōkyō"), "Tokyo")
        self.assertEqual(catalog.normalize_prefecture("Ōsaka"), "Osaka")
        self.assertEqual(catalog.normalize_prefecture("hyogo ken"), "Hyogo")

    def test_all_47_prefectures_map_to_a_region(self):
        self.assertEqual(len(catalog.PREFECTURE_REGION), 47)
        self.assertTrue(
            set(catalog.PREFECTURE_REGION.values()) <= set(catalog.REGION_LABELS)
        )

    def test_region_is_derived_from_prefecture(self):
        self.assertEqual(catalog.region_for_prefecture("Tokyo"), "kanto")
        self.assertEqual(catalog.region_for_prefecture("Fukuoka"), "kyushu")

    def test_ambiguous_japanese_requirement_takes_the_minimum(self):
        """"N4 trở lên, ưu tiên N3" là bắt buộc N4; lấy N3 sẽ loại oan ứng viên N4."""
        self.assertEqual(catalog.normalize_japanese_level("N4 trở lên, ưu tiên N3"), "N4")
        self.assertEqual(
            catalog.find_japanese_levels("N4 trở lên, ưu tiên N3"), ["N4", "N3"]
        )

    def test_japanese_level_inside_a_sentence(self):
        self.assertEqual(catalog.normalize_japanese_level("Trình độ N4"), "N4")
        self.assertEqual(catalog.normalize_japanese_level("Chưa học"), "chua_hoc")
        self.assertIsNone(catalog.normalize_japanese_level("không rõ"))

    def test_unknown_value_returns_none_instead_of_guessing(self):
        self.assertIsNone(catalog.normalize_employer_type("nhà hàng"))
        self.assertIsNone(catalog.normalize_prefecture("Hà Nội"))


class JobOrderStatusGraphTests(unittest.TestCase):
    def test_graph_matches_the_report(self):
        transitions = catalog.JOB_ORDER_TRANSITIONS
        self.assertEqual(transitions["draft"], frozenset({"open", "closed"}))
        self.assertEqual(
            transitions["open"], frozenset({"paused", "filled", "expired", "closed"})
        )
        self.assertEqual(transitions["closed"], frozenset())

    def test_every_status_has_a_vietnamese_label(self):
        self.assertEqual(
            set(catalog.JOB_ORDER_TRANSITIONS), set(catalog.JOB_ORDER_STATUS_LABELS)
        )


class JobOrderValidationTests(unittest.TestCase):
    def test_valid_payload_normalizes_labels_to_codes(self):
        payload = JobOrderCreateRequest(**valid_payload())
        self.assertEqual(payload.employer_type, "vien_duong_lao")
        self.assertEqual(payload.program, "tokutei_ginou")
        self.assertEqual(payload.requirements.education_required, "cao_dang")
        self.assertEqual(payload.requirements.gender_pref, "khong_yeu_cau")

    def test_age_range_must_be_ordered(self):
        with self.assertRaises(ValidationError):
            JobOrderCreateRequest(
                **valid_payload(
                    requirements={"japanese_required": "N4", "age_min": 40, "age_max": 25}
                )
            )

    def test_salary_range_must_be_ordered(self):
        with self.assertRaises(ValidationError):
            JobOrderCreateRequest(
                **valid_payload(reference={"salary_min": 300000, "salary_max": 100000})
            )

    def test_unknown_employer_type_is_rejected(self):
        with self.assertRaises(ValidationError):
            JobOrderCreateRequest(**valid_payload(employer_type="quán ăn"))

    def test_new_order_cannot_start_in_a_closed_status(self):
        with self.assertRaises(ValidationError):
            JobOrderCreateRequest(**valid_payload(status="Đã đóng"))

    def test_partial_update_only_touches_sent_fields(self):
        payload = JobOrderUpdateRequest(requirements={"age_min": 25})
        fields = payload.model_dump(exclude_unset=True)
        self.assertEqual(fields, {"requirements": {"age_min": 25}})


class JobOrderStoreTests(unittest.TestCase):
    def test_public_filter_requires_published_open_and_not_expired(self):
        criteria = store.public_filter(today="2026-09-11")
        self.assertEqual(criteria["published"], True)
        self.assertEqual(criteria["status"], "open")
        self.assertEqual(criteria["deadline"], {"$gte": "2026-09-11"})

    def test_public_projection_hides_internal_fields(self):
        for field in ("internal_note", "created_by", "updated_by", "hired_count"):
            self.assertEqual(store.PUBLIC_PROJECTION[field], 0)

    def test_nested_update_uses_dotted_paths(self):
        from app.db.common import flatten_update

        flat = flatten_update({"requirements": {"age_min": 20}, "quota": 4})
        self.assertEqual(flat, {"requirements.age_min": 20, "quota": 4})


class JobOrderApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_assigns_sequential_code_and_derives_region(self):
        created = {"code": "DH-0001", "status": "draft", "published": False}
        with (
            patch.object(store, "next_job_order_code", new=AsyncMock(return_value="DH-0001")),
            patch.object(store, "create_job_order", new=AsyncMock(return_value=created)) as creating,
            patch.object(store, "record_event", new=AsyncMock()) as event,
            patch("app.api.job_orders.audit_action", new=AsyncMock()) as audit,
        ):
            await create_job_order(
                JobOrderCreateRequest(**valid_payload()), http_request(), MANAGER
            )
        document = creating.await_args.args[0]
        self.assertEqual(document["code"], "DH-0001")
        self.assertEqual(document["region_group"], "kanto")
        self.assertEqual(document["hired_count"], 0)
        self.assertEqual(document["created_by"], MANAGER["email"])
        self.assertIsInstance(document["deadline"], str)
        event.assert_awaited_once()
        audit.assert_awaited_once()

    async def test_create_rejects_a_deadline_in_the_past(self):
        payload = JobOrderCreateRequest(
            **valid_payload(deadline=(local_today() - timedelta(days=1)).isoformat())
        )
        with self.assertRaises(HTTPException) as raised:
            await create_job_order(payload, http_request(), MANAGER)
        self.assertEqual(raised.exception.status_code, 400)

    async def test_illegal_status_transition_is_refused(self):
        existing = {"code": "DH-0001", "status": "closed", "published": False}
        with patch.object(store, "get_job_order", new=AsyncMock(return_value=existing)):
            with self.assertRaises(HTTPException) as raised:
                await change_job_order_status(
                    "DH-0001", JobOrderStatusRequest(status="Đang tuyển"), http_request(), MANAGER
                )
        self.assertEqual(raised.exception.status_code, 409)

    async def test_status_change_uses_the_current_status_as_a_lock(self):
        existing = {"code": "DH-0001", "status": "open", "published": True}
        updated = {"code": "DH-0001", "status": "paused", "published": False}
        with (
            patch.object(store, "get_job_order", new=AsyncMock(return_value=existing)),
            patch.object(store, "change_status", new=AsyncMock(return_value=updated)) as changing,
            patch.object(store, "record_event", new=AsyncMock()),
            patch("app.api.job_orders.audit_action", new=AsyncMock()),
        ):
            await change_job_order_status(
                "DH-0001", JobOrderStatusRequest(status="Tạm dừng"), http_request(), MANAGER
            )
        kwargs = changing.await_args.kwargs
        self.assertEqual(kwargs["expected_status"], "open")
        self.assertEqual(kwargs["new_status"], "paused")
        # Đơn rời trạng thái Đang tuyển thì phải biến mất khỏi website ngay.
        self.assertTrue(kwargs["unpublish"])

    async def test_concurrent_status_change_returns_conflict(self):
        existing = {"code": "DH-0001", "status": "open", "published": True}
        with (
            patch.object(store, "get_job_order", new=AsyncMock(return_value=existing)),
            patch.object(store, "change_status", new=AsyncMock(return_value=None)),
        ):
            with self.assertRaises(HTTPException) as raised:
                await change_job_order_status(
                    "DH-0001", JobOrderStatusRequest(status="Tạm dừng"), http_request(), MANAGER
                )
        self.assertEqual(raised.exception.status_code, 409)

    async def test_publishing_a_draft_reports_it_is_not_visible_yet(self):
        existing = {"code": "DH-0002", "status": "draft", "published": False}
        published = {
            "code": "DH-0002",
            "status": "draft",
            "published": True,
            "deadline": (local_today() + timedelta(days=30)).isoformat(),
        }
        with (
            patch.object(store, "get_job_order", new=AsyncMock(return_value=existing)),
            patch.object(store, "set_published", new=AsyncMock(return_value=published)),
            patch.object(store, "record_event", new=AsyncMock()),
            patch("app.api.job_orders.audit_action", new=AsyncMock()),
        ):
            result = await publish_job_order(
                "DH-0002", JobOrderPublishRequest(published=True), http_request(), MANAGER
            )
        self.assertFalse(result["visible_publicly"])

    async def test_only_draft_orders_can_be_deleted(self):
        existing = {"code": "DH-0003", "status": "open"}
        with patch.object(store, "get_job_order", new=AsyncMock(return_value=existing)):
            with self.assertRaises(HTTPException) as raised:
                await delete_job_order("DH-0003", http_request(), ADMIN)
        self.assertEqual(raised.exception.status_code, 409)

    async def test_closed_order_cannot_be_edited(self):
        existing = {"code": "DH-0004", "status": "closed"}
        with patch.object(store, "get_job_order", new=AsyncMock(return_value=existing)):
            with self.assertRaises(HTTPException) as raised:
                await update_job_order(
                    "DH-0004", JobOrderUpdateRequest(quota=9), http_request(), MANAGER
                )
        self.assertEqual(raised.exception.status_code, 409)

    async def test_update_rejects_an_age_range_that_becomes_inverted(self):
        """Sửa lẻ một đầu của khoảng tuổi vẫn phải kiểm tra với đầu còn lại đang lưu."""
        existing = {
            "code": "DH-0005",
            "status": "open",
            "requirements": {"age_min": 20, "age_max": 35},
        }
        with patch.object(store, "get_job_order", new=AsyncMock(return_value=existing)):
            with self.assertRaises(HTTPException) as raised:
                await update_job_order(
                    "DH-0005",
                    JobOrderUpdateRequest(requirements={"age_min": 40}),
                    http_request(),
                    MANAGER,
                )
        self.assertEqual(raised.exception.status_code, 400)

    async def test_public_listing_never_leaves_the_public_filter(self):
        with patch.object(store, "list_job_orders", new=AsyncMock(return_value=[])) as listing:
            await public_job_orders(prefecture="Tōkyō")
        query = listing.await_args.args[0]
        self.assertEqual(query["published"], True)
        self.assertEqual(query["status"], "open")
        self.assertIn("$gte", query["deadline"])
        self.assertEqual(query["prefecture"], "Tokyo")
        self.assertTrue(listing.await_args.kwargs["public"])


class TimeUtilTests(unittest.TestCase):
    def test_age_uses_birth_year_difference(self):
        self.assertEqual(age_on(2003, as_of=date(2026, 9, 11)), 23)

    def test_missing_birth_year_gives_unknown_not_zero(self):
        """Bộ đối chiếu phải phân biệt "không đạt" với "chưa rõ"."""
        self.assertIsNone(age_on(None))


if __name__ == "__main__":
    unittest.main()
