"""Kiểm thử API đối chiếu và nhật ký giới thiệu.

Hai chốt chặn quan trọng nhất ở tầng này:

- Hồ sơ **chưa xác nhận thì không được đối chiếu**. Giới thiệu đơn dựa trên dữ
  liệu máy đọc mà ứng viên chưa xem lại là cách chắc chắn để chào sai đơn.
- Nhân viên tư vấn chỉ xem được nhật ký của hồ sơ mình phụ trách.
"""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, Request
from pydantic import ValidationError

from app.api.matching import (
    RerunRequest,
    latest_for_profile,
    match_detail,
    matches_for_session,
    recommendation_log_detail,
    recommendation_logs_list,
    rerun_matching,
)
from app.db import candidate_profiles as profile_store
from app.db import recommendation_logs as log_store


def http_request() -> Request:
    return Request({"type": "http", "headers": [], "client": ("127.0.0.1", 12345)})


ADMIN = {"email": "admin@example.com", "full_name": "Quản trị", "role": "admin"}
MANAGER = {"email": "manager@example.com", "full_name": "Quản lý", "role": "manager"}
CONSULTANT = {"email": "tu.van@example.com", "full_name": "Tư vấn", "role": "consultant"}

SESSION = "phien-ung-vien-0001"


def profile(**overrides) -> dict:
    document = {
        "code": "UV-ABC123",
        "session_id": SESSION,
        "version": 2,
        "status": profile_store.STATUS_CONFIRMED,
        "assigned_to": CONSULTANT["email"],
        "fields": {},
        "preferences": {},
    }
    document.update(overrides)
    return document


def log(**overrides) -> dict:
    document = {
        "code": "RL-ABC123",
        "profile_code": "UV-ABC123",
        "profile_version": 2,
        "session_id": SESSION,
        "assigned_to": CONSULTANT["email"],
        "as_of": "2026-09-15",
        "total_considered": 4,
        "eligible_count": 2,
        "missing_info": [],
        "top_codes": ["DH-0001"],
        "items": [
            {
                "code": "DH-0001",
                "title": "Điều dưỡng Tokyo",
                "employer_name": "Sakura",
                "prefecture": "Tokyo",
                "region_group": "kanto",
                "employer_type": "vien_duong_lao",
                "program": "tokutei_ginou",
                "deadline": "2026-12-31",
                "eligible": True,
                "score": 70,
                "rank": 1,
                "hard_rows": [],
                "soft_rows": [],
                "gaps": [],
                "missing_info": [],
                "labels": {},
            },
            {
                "code": "DH-0004",
                "title": "Điều dưỡng Osaka",
                "employer_name": "Kikyo",
                "prefecture": "Osaka",
                "region_group": "kansai",
                "employer_type": "benh_vien",
                "program": "epa",
                "deadline": "2026-11-30",
                "eligible": False,
                "score": 0,
                "rank": None,
                "hard_rows": [],
                "soft_rows": [],
                "gaps": [],
                "missing_info": [],
                "labels": {},
            },
        ],
    }
    document.update(overrides)
    return document


class PublicMatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_session_without_a_profile_gets_404(self):
        with patch.object(profile_store, "get_by_session", new=AsyncMock(return_value=None)):
            with self.assertRaises(HTTPException) as caught:
                await matches_for_session(SESSION, http_request(), limit=5, refresh=False)
        self.assertEqual(caught.exception.status_code, 404)

    async def test_an_unconfirmed_profile_is_not_matched(self):
        """Máy có thể đọc nhầm N4 thành N3; đối chiếu trước khi ứng viên xem lại
        là chào một danh sách đơn không liên quan tới họ."""
        unconfirmed = profile(status=profile_store.STATUS_EXTRACTED)
        with patch.object(profile_store, "get_by_session", new=AsyncMock(return_value=unconfirmed)):
            with self.assertRaises(HTTPException) as caught:
                await matches_for_session(SESSION, http_request(), limit=5, refresh=False)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertIn("chưa được xác nhận", caught.exception.detail)

    async def test_a_confirmed_profile_gets_only_the_orders_it_qualifies_for(self):
        with patch.object(
            profile_store, "get_by_session", new=AsyncMock(return_value=profile())
        ), patch(
            "app.services.matching_service.run_matching",
            new=AsyncMock(return_value=(log(), False)),
        ):
            result = await matches_for_session(SESSION, http_request(), limit=5, refresh=False)
        self.assertEqual([item["code"] for item in result["matches"]], ["DH-0001"])
        self.assertFalse(result["from_cache"])

    async def test_the_response_says_whether_the_result_was_reused(self):
        with patch.object(
            profile_store, "get_by_session", new=AsyncMock(return_value=profile())
        ), patch(
            "app.services.matching_service.run_matching",
            new=AsyncMock(return_value=(log(), True)),
        ):
            result = await matches_for_session(SESSION, http_request(), limit=5, refresh=False)
        self.assertTrue(result["from_cache"])

    async def test_refresh_forces_a_fresh_run(self):
        run = AsyncMock(return_value=(log(), False))
        with patch.object(
            profile_store, "get_by_session", new=AsyncMock(return_value=profile())
        ), patch("app.services.matching_service.run_matching", new=run):
            await matches_for_session(SESSION, http_request(), limit=5, refresh=True)
        self.assertTrue(run.await_args.kwargs["force"])

    async def test_the_public_run_is_marked_as_coming_from_the_candidate(self):
        run = AsyncMock(return_value=(log(), False))
        with patch.object(
            profile_store, "get_by_session", new=AsyncMock(return_value=profile())
        ), patch("app.services.matching_service.run_matching", new=run):
            await matches_for_session(SESSION, http_request(), limit=5, refresh=False)
        self.assertEqual(run.await_args.kwargs["trigger"], "public")

    async def test_detail_of_an_order_outside_the_last_run_gives_404(self):
        with patch.object(
            profile_store, "get_by_session", new=AsyncMock(return_value=profile())
        ), patch.object(log_store, "latest_for_profile", new=AsyncMock(return_value=log())):
            with self.assertRaises(HTTPException) as caught:
                await match_detail(SESSION, "DH-9999")
        self.assertEqual(caught.exception.status_code, 404)

    async def test_detail_before_any_matching_gives_404(self):
        with patch.object(
            profile_store, "get_by_session", new=AsyncMock(return_value=profile())
        ), patch.object(log_store, "latest_for_profile", new=AsyncMock(return_value=None)):
            with self.assertRaises(HTTPException) as caught:
                await match_detail(SESSION, "DH-0001")
        self.assertEqual(caught.exception.status_code, 404)

    async def test_detail_returns_the_reason_block(self):
        with patch.object(
            profile_store, "get_by_session", new=AsyncMock(return_value=profile())
        ), patch.object(log_store, "latest_for_profile", new=AsyncMock(return_value=log())):
            result = await match_detail(SESSION, "DH-0001")
        self.assertEqual(result["code"], "DH-0001")
        self.assertIn("explanation_block", result)
        self.assertIn("explanation_text", result)


class RecommendationLogApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_consultant_only_lists_their_own_logs(self):
        captured = {}

        async def fake_list(query, *, limit):
            captured["query"] = query
            return []

        with patch.object(log_store, "list_logs", new=AsyncMock(side_effect=fake_list)):
            await recommendation_logs_list(
                profile_code=None,
                session_id=None,
                trigger=None,
                date_from=None,
                date_to=None,
                limit=50,
                current_user=CONSULTANT,
            )
        self.assertEqual(captured["query"]["assigned_to"], CONSULTANT["email"])

    async def test_a_manager_lists_everything(self):
        captured = {}

        async def fake_list(query, *, limit):
            captured["query"] = query
            return []

        with patch.object(log_store, "list_logs", new=AsyncMock(side_effect=fake_list)):
            await recommendation_logs_list(
                profile_code=None,
                session_id=None,
                trigger=None,
                date_from=None,
                date_to=None,
                limit=50,
                current_user=MANAGER,
            )
        self.assertNotIn("assigned_to", captured["query"])

    async def test_the_date_filter_becomes_a_window_on_as_of(self):
        query = log_store.build_query(date_from="2026-09-01", date_to="2026-09-30")
        self.assertEqual(query["as_of"], {"$gte": "2026-09-01", "$lte": "2026-09-30"})

    async def test_the_list_does_not_drag_the_whole_criteria_table_along(self):
        """Mỗi bản ghi chứa bảng tiêu chí của hàng chục đơn; danh sách không cần."""
        self.assertEqual(log_store.LIST_PROJECTION["items"], 0)

    async def test_the_detail_shows_the_rejected_orders_too(self):
        with patch.object(log_store, "get_log", new=AsyncMock(return_value=log())):
            result = await recommendation_log_detail("RL-ABC123", current_user=ADMIN)
        self.assertEqual(len(result["items"]), 2)
        self.assertFalse(result["items"][1]["eligible"])

    async def test_an_unknown_log_gives_404(self):
        with patch.object(log_store, "get_log", new=AsyncMock(return_value=None)):
            with self.assertRaises(HTTPException) as caught:
                await recommendation_log_detail("RL-KHONG-CO", current_user=ADMIN)
        self.assertEqual(caught.exception.status_code, 404)

    async def test_a_consultant_cannot_open_someone_elses_log(self):
        other = log(assigned_to="nguoi.khac@example.com")
        with patch.object(log_store, "get_log", new=AsyncMock(return_value=other)):
            with self.assertRaises(HTTPException) as caught:
                await recommendation_log_detail("RL-ABC123", current_user=CONSULTANT)
        self.assertEqual(caught.exception.status_code, 403)

    async def test_rerunning_on_an_unknown_profile_gives_404(self):
        with patch.object(profile_store, "get_by_code", new=AsyncMock(return_value=None)):
            with self.assertRaises(HTTPException) as caught:
                await rerun_matching(
                    RerunRequest(profile_code="UV-KHONG-CO"), http_request(), current_user=ADMIN
                )
        self.assertEqual(caught.exception.status_code, 404)

    async def test_a_consultant_cannot_rerun_someone_elses_profile(self):
        other = profile(assigned_to="nguoi.khac@example.com")
        with patch.object(profile_store, "get_by_code", new=AsyncMock(return_value=other)):
            with self.assertRaises(HTTPException) as caught:
                await rerun_matching(
                    RerunRequest(profile_code="UV-ABC123"), http_request(), current_user=CONSULTANT
                )
        self.assertEqual(caught.exception.status_code, 403)

    async def test_a_staff_rerun_bypasses_the_cache_and_is_audited(self):
        run = AsyncMock(return_value=(log(), False))
        with patch.object(
            profile_store, "get_by_code", new=AsyncMock(return_value=profile())
        ), patch("app.services.matching_service.run_matching", new=run), patch(
            "app.api.matching.audit_action", new=AsyncMock()
        ) as audit:
            result = await rerun_matching(
                RerunRequest(profile_code="UV-ABC123"), http_request(), current_user=ADMIN
            )
        self.assertTrue(run.await_args.kwargs["force"])
        self.assertEqual(run.await_args.kwargs["trigger"], "staff_rerun")
        self.assertEqual(run.await_args.kwargs["actor_email"], ADMIN["email"])
        self.assertEqual(audit.await_args.args[1], "recommendation.rerun")
        self.assertEqual(result["code"], "RL-ABC123")

    async def test_a_profile_never_matched_says_so_plainly(self):
        with patch.object(
            profile_store, "get_by_code", new=AsyncMock(return_value=profile())
        ), patch.object(log_store, "latest_for_profile", new=AsyncMock(return_value=None)):
            with self.assertRaises(HTTPException) as caught:
                await latest_for_profile("UV-ABC123", current_user=ADMIN)
        self.assertEqual(caught.exception.status_code, 404)

    async def test_the_latest_log_for_a_profile_is_returned(self):
        with patch.object(
            profile_store, "get_by_code", new=AsyncMock(return_value=profile())
        ), patch.object(log_store, "latest_for_profile", new=AsyncMock(return_value=log())):
            result = await latest_for_profile("UV-ABC123", current_user=CONSULTANT)
        self.assertEqual(result["code"], "RL-ABC123")

    async def test_the_rerun_payload_rejects_anything_extra(self):
        with self.assertRaises(ValidationError):
            RerunRequest(profile_code="UV-ABC123", force=True)


if __name__ == "__main__":
    unittest.main()
