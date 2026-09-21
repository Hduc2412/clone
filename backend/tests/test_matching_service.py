"""Kiểm thử tầng điều phối đối chiếu: kho đơn, dấu vân tay, bộ nhớ đệm, nhật ký.

Bộ đối chiếu thuần đã được kiểm ở `test_matching_engine.py`. Ở đây kiểm phần bao
quanh nó: lấy đúng kho đơn nào, khi nào được phép dùng lại kết quả cũ, và nhật ký
ghi lại đủ thứ cần để trả lời câu hỏi "vì sao đơn kia không được giới thiệu".
"""
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from app.db import candidate_profiles as profile_store
from app.matching.weights import load_weights
from app.services import matching_service


AS_OF = date(2026, 9, 15)
WEIGHTS = load_weights()


def order(code: str, **overrides) -> dict:
    base = {
        "code": code,
        "title": f"Điều dưỡng {code}",
        "employer_name": "Viện dưỡng lão Sakura",
        "employer_type": "vien_duong_lao",
        "program": "tokutei_ginou",
        "prefecture": "Tokyo",
        "region_group": "kanto",
        "status": "open",
        "published": True,
        "deadline": "2026-12-31",
        "updated_at": datetime(2026, 9, 1, tzinfo=timezone.utc),
        "requirements": {
            "japanese_required": "N4",
            "education_required": "cao_dang",
            "experience_min": 0,
            "age_min": 20,
            "age_max": 35,
            "gender_pref": "khong_yeu_cau",
        },
        "reference": {"salary_min": 195000, "salary_max": 215000, "cost_total_vnd": 110_000_000},
    }
    requirements = {**base["requirements"], **overrides.pop("requirements", {})}
    return {**base, **overrides, "requirements": requirements}


POOL = [
    order("DH-0001"),
    order("DH-0002", prefecture="Fukuoka", region_group="kyushu"),
    # Đơn hết hạn: vẫn nằm trong kho để nhật ký chứng minh được là nó bị loại.
    order("DH-0003", deadline="2026-01-31"),
    # Đơn yêu cầu N2: ứng viên N4 trượt ở bộ lọc cứng.
    order("DH-0004", requirements={"japanese_required": "N2"}),
]


def profile(**overrides) -> dict:
    document = {
        "code": "UV-ABC123",
        "session_id": "phien-ung-vien-0001",
        "version": 3,
        "status": profile_store.STATUS_CONFIRMED,
        "assigned_to": "tu.van@example.com",
        "fields": {
            "full_name": profile_store.cell("Nguyễn Văn An", "user_confirmed"),
            "japanese_level": profile_store.cell("N4", "user_confirmed"),
            "education_level": profile_store.cell("cao_dang", "user_confirmed"),
            "birth_year": profile_store.cell(2003, "user_confirmed"),
        },
        "preferences": {
            "desired_prefecture": profile_store.cell("Tokyo", "user_confirmed"),
            "desired_region_group": profile_store.cell("kanto", "user_confirmed"),
            "desired_employer_type": profile_store.cell("vien_duong_lao", "user_confirmed"),
        },
    }
    document.update(overrides)
    return document


class FingerprintTests(unittest.TestCase):
    def test_the_order_the_database_returns_does_not_change_the_fingerprint(self):
        self.assertEqual(
            matching_service.orders_fingerprint(POOL),
            matching_service.orders_fingerprint(list(reversed(POOL))),
        )

    def test_editing_an_order_invalidates_the_cache_immediately(self):
        """Sửa một điều kiện phải làm dấu vân tay đổi, nếu không sẽ dùng lại kết
        quả tính theo điều kiện cũ."""
        edited = [{**POOL[0], "updated_at": datetime(2026, 9, 2, tzinfo=timezone.utc)}, *POOL[1:]]
        self.assertNotEqual(
            matching_service.orders_fingerprint(POOL),
            matching_service.orders_fingerprint(edited),
        )

    def test_removing_an_order_changes_the_fingerprint(self):
        self.assertNotEqual(
            matching_service.orders_fingerprint(POOL),
            matching_service.orders_fingerprint(POOL[:-1]),
        )

    def test_the_fingerprint_is_short_and_labelled(self):
        value = matching_service.orders_fingerprint(POOL)
        self.assertTrue(value.startswith("sha256:"))
        self.assertEqual(len(value), len("sha256:") + 16)


class PoolTests(unittest.IsolatedAsyncioTestCase):
    async def test_the_pool_keeps_expired_and_paused_orders(self):
        """Không dùng `public_filter()`: nhật ký phải chứng minh được bộ lọc cứng
        đã chạy, mà muốn thế thì đơn bị loại phải có mặt trong danh sách đã xét."""
        self.assertEqual(matching_service.POOL_QUERY, {"published": True})
        self.assertNotIn("status", matching_service.POOL_QUERY)
        self.assertNotIn("deadline", matching_service.POOL_QUERY)

    async def test_a_draft_order_never_reaches_the_pool(self):
        captured = {}

        async def fake_list(query, *, limit):
            captured.update(query)
            return []

        with patch("app.db.job_orders.list_job_orders", new=AsyncMock(side_effect=fake_list)):
            await matching_service.load_pool()
        self.assertTrue(captured["published"])


class RunMatchingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.created: list[dict] = []

    def _patches(self, cached=None):
        async def fake_create(document):
            self.created.append(document)
            return document

        return (
            patch.object(matching_service, "load_pool", new=AsyncMock(return_value=list(POOL))),
            patch(
                "app.db.recommendation_logs.find_cached", new=AsyncMock(return_value=cached)
            ),
            patch(
                "app.db.recommendation_logs.create_log", new=AsyncMock(side_effect=fake_create)
            ),
        )

    async def _run(self, cached=None, **kwargs):
        pool_patch, find_patch, create_patch = self._patches(cached)
        with pool_patch, find_patch as find, create_patch:
            log, from_cache = await matching_service.run_matching(
                profile(), trigger="public", as_of=AS_OF, **kwargs
            )
        return log, from_cache, find

    async def test_the_log_records_every_order_considered_including_the_rejected_ones(self):
        log, from_cache, _ = await self._run()
        self.assertFalse(from_cache)
        self.assertEqual(log["total_considered"], 4)
        self.assertEqual(len(log["items"]), 4)
        self.assertEqual({item["code"] for item in log["items"]}, {o["code"] for o in POOL})

    async def test_the_rejected_orders_carry_the_reason_they_were_rejected(self):
        log, _, _ = await self._run()
        by_code = {item["code"]: item for item in log["items"]}

        expired = by_code["DH-0003"]
        self.assertFalse(expired["eligible"])
        self.assertIn("KHONG_DAT", [row["result"] for row in expired["hard_rows"]])

        too_hard = by_code["DH-0004"]
        japanese = next(row for row in too_hard["hard_rows"] if row["key"] == "japanese")
        self.assertEqual(japanese["result"], "KHONG_DAT")

    async def test_a_rejected_order_has_no_score_to_compare(self):
        log, _, _ = await self._run()
        for item in log["items"]:
            if not item["eligible"]:
                self.assertEqual(item["score"], 0)
                self.assertIsNone(item["rank"])
                self.assertEqual(item["soft_rows"], [])

    async def test_the_log_carries_everything_needed_to_reproduce_the_run(self):
        log, _, _ = await self._run()
        for key in (
            "orders_fingerprint",
            "weights_fingerprint",
            "weights_version",
            "engine_version",
            "as_of",
            "pool_query",
            "profile_version",
        ):
            self.assertIn(key, log)
        self.assertEqual(log["as_of"], AS_OF.isoformat())
        self.assertEqual(log["profile_version"], 3)
        self.assertEqual(log["weights_fingerprint"], WEIGHTS.fingerprint)

    async def test_the_log_inherits_the_assignment_so_staff_only_see_their_own(self):
        log, _, _ = await self._run()
        self.assertEqual(log["assigned_to"], "tu.van@example.com")
        self.assertEqual(log["session_id"], "phien-ung-vien-0001")

    async def test_the_preferred_prefecture_is_ranked_first(self):
        log, _, _ = await self._run()
        self.assertEqual(log["top_codes"][0], "DH-0001")

    async def test_top_codes_holds_at_most_the_default_page(self):
        log, _, _ = await self._run()
        self.assertLessEqual(len(log["top_codes"]), matching_service.DEFAULT_TOP_N)

    async def test_a_matching_recent_run_is_reused(self):
        cached = {"code": "RL-CACHED", "items": []}
        log, from_cache, _ = await self._run(cached=cached)
        self.assertTrue(from_cache)
        self.assertEqual(log["code"], "RL-CACHED")
        self.assertEqual(self.created, [])

    async def test_the_cache_is_looked_up_on_all_four_inputs(self):
        _, _, find = await self._run()
        kwargs = find.await_args.kwargs
        self.assertEqual(kwargs["profile_code"], "UV-ABC123")
        self.assertEqual(kwargs["profile_version"], 3)
        self.assertEqual(kwargs["orders_fingerprint"], matching_service.orders_fingerprint(POOL))
        self.assertEqual(kwargs["weights_fingerprint"], WEIGHTS.fingerprint)

    async def test_the_cache_window_is_ten_minutes(self):
        self.assertEqual(matching_service.CACHE_TTL_SECONDS, 600)
        _, _, find = await self._run()
        age = datetime.now(timezone.utc) - find.await_args.kwargs["since"]
        self.assertAlmostEqual(age.total_seconds(), 600, delta=30)

    async def test_forcing_a_rerun_skips_the_cache_entirely(self):
        cached = {"code": "RL-CACHED", "items": []}
        log, from_cache, find = await self._run(cached=cached, force=True)
        self.assertFalse(from_cache)
        find.assert_not_awaited()
        self.assertNotEqual(log["code"], "RL-CACHED")

    async def test_running_twice_gives_byte_identical_results(self):
        first, _, _ = await self._run()
        second, _, _ = await self._run()
        self.assertEqual(first["items"], second["items"])
        self.assertEqual(first["top_codes"], second["top_codes"])

    async def test_a_shuffled_pool_gives_the_same_ranking(self):
        pool_patch, find_patch, create_patch = self._patches()
        with pool_patch, find_patch, create_patch:
            baseline, _ = await matching_service.run_matching(
                profile(), trigger="public", as_of=AS_OF
            )
        with patch.object(
            matching_service, "load_pool", new=AsyncMock(return_value=list(reversed(POOL)))
        ), patch(
            "app.db.recommendation_logs.find_cached", new=AsyncMock(return_value=None)
        ), patch(
            "app.db.recommendation_logs.create_log", new=AsyncMock(side_effect=lambda d: d)
        ):
            shuffled, _ = await matching_service.run_matching(
                profile(), trigger="public", as_of=AS_OF
            )
        self.assertEqual(baseline["items"], shuffled["items"])

    async def test_a_profile_with_only_a_name_still_gets_offers(self):
        """Cái chưa biết không được loại ai: hồ sơ mới điền một nửa vẫn phải có đơn."""
        bare = profile(
            fields={"full_name": profile_store.cell("Nguyễn Văn An", "user_confirmed")},
            preferences={},
        )
        pool_patch, find_patch, create_patch = self._patches()
        with pool_patch, find_patch, create_patch:
            log, _ = await matching_service.run_matching(bare, trigger="public", as_of=AS_OF)
        self.assertGreater(log["eligible_count"], 0)
        self.assertTrue(log["missing_info"])

    async def test_the_trigger_and_the_actor_are_recorded(self):
        pool_patch, find_patch, create_patch = self._patches()
        with pool_patch, find_patch, create_patch:
            log, _ = await matching_service.run_matching(
                profile(),
                trigger="staff_rerun",
                actor_email="admin@example.com",
                as_of=AS_OF,
                force=True,
            )
        self.assertEqual(log["trigger"], "staff_rerun")
        self.assertEqual(log["actor_email"], "admin@example.com")


class PublicPayloadTests(unittest.IsolatedAsyncioTestCase):
    async def _log(self) -> dict:
        with patch.object(
            matching_service, "load_pool", new=AsyncMock(return_value=list(POOL))
        ), patch(
            "app.db.recommendation_logs.find_cached", new=AsyncMock(return_value=None)
        ), patch(
            "app.db.recommendation_logs.create_log", new=AsyncMock(side_effect=lambda d: d)
        ):
            log, _ = await matching_service.run_matching(
                profile(), trigger="public", as_of=AS_OF
            )
        return log

    async def test_the_candidate_only_sees_orders_they_qualify_for(self):
        payload = matching_service.to_public_payload(await self._log(), limit=5)
        self.assertTrue(payload["matches"])
        self.assertTrue(all(item["eligible"] for item in payload["matches"]))
        self.assertLess(len(payload["matches"]), payload["total_considered"])

    async def test_the_limit_is_respected(self):
        payload = matching_service.to_public_payload(await self._log(), limit=1)
        self.assertEqual(len(payload["matches"]), 1)

    async def test_every_public_result_carries_a_disclaimer(self):
        payload = matching_service.to_public_payload(await self._log(), limit=5)
        self.assertIn("không phải cam kết trúng tuyển", payload["disclaimer"])

    async def test_each_result_comes_with_a_reason_the_candidate_can_read(self):
        payload = matching_service.to_public_payload(await self._log(), limit=5)
        first = payload["matches"][0]
        self.assertTrue(first["explanation_text"])
        self.assertIn("[cứng] yêu cầu N4", first["explanation_block"])
        self.assertIn("→ tổng 75/100 · hạng 1", first["explanation_block"])

    async def test_the_reason_block_is_rebuilt_from_the_stored_log(self):
        """Khối lý do hiển thị hôm nay phải đúng bằng khối đã sinh lúc đối chiếu,
        kể cả khi đơn hàng đã đổi từ đó tới giờ."""
        log = await self._log()
        stored = next(item for item in log["items"] if item["eligible"])
        rebuilt = matching_service.public_item(stored)
        self.assertEqual(rebuilt["score"], stored["score"])
        self.assertEqual(rebuilt["hard_rows"], stored["hard_rows"])

    async def test_missing_info_is_passed_through_so_the_form_can_ask(self):
        payload = matching_service.to_public_payload(await self._log(), limit=5)
        self.assertIn("missing_info", payload)


if __name__ == "__main__":
    unittest.main()
