"""Nghiệm thu bộ đối chiếu trên 19 đơn mẫu thật.

Các bộ kiểm thử khác dựng đơn hàng giả để cô lập từng quy tắc. Bộ này chạy trên
đúng dữ liệu sẽ dùng khi demo, vì một quy tắc đúng trên đơn giả mà sai trên đơn
thật thì vẫn là sai. Nó cũng là bản diễn lại kịch bản trong `docs/design/14`:
ứng viên 23 tuổi, Cao đẳng Điều dưỡng, N4, muốn làm viện dưỡng lão ở Tokyo.
"""
import json
import unittest
from datetime import date

from app.db import candidate_profiles as profile_store
from app.matching import catalog, engine, explain
from app.matching.weights import load_weights
from scripts.seed_job_orders import build_documents


AS_OF = date(2026, 9, 15)
WEIGHTS = load_weights()


def pool() -> list[dict]:
    """Kho đơn đem đối chiếu: mọi đơn đã từng công khai, kể cả đơn hết hạn."""
    return [document for document in build_documents() if document.get("published")]


def facts(**fields) -> engine.CandidateFacts:
    profile = {
        "fields": {key: profile_store.cell(value, "user_confirmed") for key, value in fields.items()},
        "preferences": {},
    }
    return engine.build_facts(profile, AS_OF)


def facts_with(fields: dict, preferences: dict) -> engine.CandidateFacts:
    profile = {
        "fields": {key: profile_store.cell(value, "user_confirmed") for key, value in fields.items()},
        "preferences": {
            key: profile_store.cell(value, "user_confirmed") for key, value in preferences.items()
        },
    }
    return engine.build_facts(profile, AS_OF)


# Nhân vật trong kịch bản demo.
AN = {
    "full_name": "Nguyễn Văn An",
    "birth_year": 2003,
    "gender": "nam",
    "education_level": "cao_dang",
    "major": "Điều dưỡng",
    "japanese_level": "N4",
    "experience_years": 1,
    "care_experience": True,
}
AN_WISHES = {
    "desired_prefecture": "Tokyo",
    "desired_region_group": "kanto",
    "desired_employer_type": "vien_duong_lao",
    "salary_expectation_jpy": 190000,
    "budget_vnd": 150_000_000,
}


class SeededPoolTests(unittest.TestCase):
    def test_the_pool_excludes_drafts_but_keeps_expired_and_paused_orders(self):
        codes = {document["code"] for document in pool()}
        statuses = {document["status"] for document in pool()}
        self.assertNotIn("draft", statuses)
        self.assertIn("paused", statuses)
        self.assertGreaterEqual(len(codes), 15)


class DemoScenarioTests(unittest.TestCase):
    """Kịch bản chính, chạy từ đầu tới cuối trên dữ liệu mẫu."""

    @classmethod
    def setUpClass(cls):
        cls.result = engine.match_orders(
            pool(), facts_with(AN, AN_WISHES), weights=WEIGHTS, as_of=AS_OF
        )

    def test_the_candidate_gets_a_real_shortlist(self):
        self.assertGreater(self.result.eligible_count, 3)
        self.assertLess(self.result.eligible_count, self.result.total_considered)

    def test_every_order_considered_is_accounted_for(self):
        """Không đơn nào biến mất giữa chừng: đơn bị loại vẫn có mặt kèm lý do."""
        self.assertEqual(len(self.result.items), len(pool()))
        for item in self.result.items:
            self.assertEqual(len(item.hard_rows), len(engine.HARD_KEYS))

    def test_the_top_order_is_a_nursing_home_near_tokyo(self):
        top = self.result.items[0]
        self.assertTrue(top.eligible)
        self.assertEqual(top.rank, 1)
        self.assertEqual(top.employer_type, "vien_duong_lao")
        self.assertEqual(top.region_group, "kanto")

    def test_the_ranking_never_ties_ambiguously(self):
        eligible = [item for item in self.result.items if item.eligible]
        keys = [(-item.score, item.deadline, item.code) for item in eligible]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual([item.rank for item in eligible], list(range(1, len(eligible) + 1)))

    def test_no_rejected_order_carries_a_score_to_compare(self):
        for item in self.result.items:
            if not item.eligible:
                self.assertEqual(item.score, 0)
                self.assertIsNone(item.rank)

    def test_the_expired_order_is_rejected_for_being_expired(self):
        expired = [
            item
            for item in self.result.items
            if item.deadline < AS_OF.isoformat()
        ]
        self.assertTrue(expired)
        for item in expired:
            self.assertFalse(item.eligible)
            deadline_row = next(row for row in item.hard_rows if row.key == "deadline")
            self.assertEqual(deadline_row.result, engine.KHONG_DAT)

    def test_the_paused_order_is_rejected_for_not_being_open(self):
        paused = [
            item
            for item in self.result.items
            if next(row for row in item.hard_rows if row.key == "status").result
            == engine.KHONG_DAT
        ]
        self.assertTrue(paused)

    def test_orders_above_the_candidates_japanese_level_are_rejected(self):
        """An có N4, nên mọi đơn bị loại vì tiếng Nhật phải là đơn đòi cao hơn N4."""
        an_rank = catalog.JAPANESE_RANK["N4"]
        rejected = 0
        by_code = {document["code"]: document for document in pool()}
        for item in self.result.items:
            row = next(row for row in item.hard_rows if row.key == "japanese")
            if row.result == engine.KHONG_DAT:
                required = by_code[item.code]["requirements"]["japanese_required"]
                self.assertGreater(catalog.JAPANESE_RANK[required], an_rank)
                self.assertFalse(item.eligible)
                rejected += 1
        self.assertGreater(rejected, 0, "Bộ đơn mẫu phải có đơn đòi trên N4")

    def test_a_confirmed_profile_leaves_nothing_to_ask_about(self):
        self.assertEqual(self.result.missing_info, ())

    def test_running_twice_is_byte_identical(self):
        again = engine.match_orders(
            pool(), facts_with(AN, AN_WISHES), weights=WEIGHTS, as_of=AS_OF
        )
        self.assertEqual(
            json.dumps(self.result.as_dict(), ensure_ascii=False, sort_keys=True),
            json.dumps(again.as_dict(), ensure_ascii=False, sort_keys=True),
        )

    def test_a_shuffled_pool_gives_the_same_answer(self):
        again = engine.match_orders(
            list(reversed(pool())), facts_with(AN, AN_WISHES), weights=WEIGHTS, as_of=AS_OF
        )
        self.assertEqual(
            [item.code for item in self.result.items], [item.code for item in again.items]
        )

    def test_every_shortlisted_order_can_explain_itself(self):
        for item in self.result.items[: self.result.eligible_count]:
            block = explain.render_block(item)
            self.assertIn(item.code, block)
            self.assertIn(f"tổng {item.score}/100", block)
            self.assertTrue(explain.render_template_text(item))


class PartialProfileTests(unittest.TestCase):
    """Cái chưa biết không được loại ai."""

    def test_a_profile_with_only_a_name_still_sees_offers(self):
        result = engine.match_orders(
            pool(), facts(full_name="Nguyễn Văn An"), weights=WEIGHTS, as_of=AS_OF
        )
        self.assertGreater(result.eligible_count, 0)

    def test_the_unknowns_become_questions_instead_of_rejections(self):
        result = engine.match_orders(
            pool(), facts(full_name="Nguyễn Văn An"), weights=WEIGHTS, as_of=AS_OF
        )
        self.assertTrue(result.missing_info)
        for item in result.items:
            if item.eligible:
                results = {row.result for row in item.hard_rows}
                self.assertIn(engine.CHUA_RO, results)
                self.assertNotIn(engine.KHONG_DAT, results)

    def test_answering_a_question_narrows_the_list_it_does_not_widen_it(self):
        bare = engine.match_orders(
            pool(), facts(full_name="Nguyễn Văn An"), weights=WEIGHTS, as_of=AS_OF
        )
        answered = engine.match_orders(
            pool(),
            facts(full_name="Nguyễn Văn An", japanese_level="chua_hoc"),
            weights=WEIGHTS,
            as_of=AS_OF,
        )
        self.assertLess(answered.eligible_count, bare.eligible_count)

    def test_having_never_studied_japanese_is_an_answer_not_a_gap(self):
        result = engine.match_orders(
            pool(),
            facts(full_name="Nguyễn Văn An", japanese_level="chua_hoc"),
            weights=WEIGHTS,
            as_of=AS_OF,
        )
        self.assertNotIn("japanese_level", result.missing_info)

    def test_someone_who_never_gave_a_birth_year_is_not_treated_as_too_old(self):
        result = engine.match_orders(
            pool(), facts(full_name="Nguyễn Văn An", japanese_level="N3"), weights=WEIGHTS, as_of=AS_OF
        )
        self.assertGreater(result.eligible_count, 0)
        for item in result.items:
            age_row = next(row for row in item.hard_rows if row.key == "age")
            self.assertNotEqual(age_row.result, engine.KHONG_DAT)


class LevelProgressionTests(unittest.TestCase):
    """Trình độ cao hơn không bao giờ được thấy ít đơn hơn."""

    def _count(self, level: str) -> int:
        return engine.match_orders(
            pool(),
            facts(full_name="A", birth_year=2000, education_level="cao_dang", japanese_level=level),
            weights=WEIGHTS,
            as_of=AS_OF,
        ).eligible_count

    def test_a_higher_level_never_sees_fewer_orders(self):
        counts = [self._count(level) for level in ("chua_hoc", "N5", "N4", "N3", "N2", "N1")]
        self.assertEqual(counts, sorted(counts))
        self.assertGreater(counts[-1], counts[0])

    def test_a_higher_degree_never_sees_fewer_orders(self):
        counts = []
        for education in ("khac", "trung_cap", "cao_dang", "dai_hoc"):
            counts.append(
                engine.match_orders(
                    pool(),
                    facts(
                        full_name="A",
                        birth_year=2000,
                        japanese_level="N3",
                        education_level=education,
                    ),
                    weights=WEIGHTS,
                    as_of=AS_OF,
                ).eligible_count
            )
        self.assertEqual(counts, sorted(counts))


class GenderAndExperienceTests(unittest.TestCase):
    """Hai tiêu chí cứng chưa ca nào soi tới: giới tính và kinh nghiệm.

    Bộ đơn mẫu có đơn chỉ tuyển nữ, nên đây là chỗ duy nhất kiểm được rằng tiêu
    chí giới tính loại đúng người cần loại và không loại nhầm ai khác.
    """

    def _run(self, **fields) -> engine.MatchResult:
        return engine.match_orders(pool(), facts(**fields), weights=WEIGHTS, as_of=AS_OF)

    def _loai_vi(self, result: engine.MatchResult, khoa: str) -> list[str]:
        return [
            item.code
            for item in result.items
            for row in item.hard_rows
            if row.key == khoa and row.result == engine.KHONG_DAT
        ]

    def test_a_woman_is_never_rejected_by_the_gender_criterion(self):
        """Bộ đơn mẫu chỉ có đơn giới hạn nữ, không có đơn giới hạn nam."""
        result = self._run(full_name="Bùi Thị Ngọc", birth_year=2002, gender="nu",
                           education_level="cao_dang", japanese_level="N4")
        self.assertEqual(self._loai_vi(result, "gender"), [])

    def test_a_man_is_rejected_only_by_orders_that_ask_for_women(self):
        result = self._run(full_name="Nguyễn Văn An", birth_year=2003, gender="nam",
                           education_level="cao_dang", japanese_level="N4")
        by_code = {d["code"]: d for d in pool()}
        loai = self._loai_vi(result, "gender")
        self.assertTrue(loai, "Bộ đơn mẫu phải có đơn giới hạn giới tính")
        for code in loai:
            self.assertEqual(by_code[code]["requirements"]["gender_pref"], "nu")

    def test_not_declaring_a_gender_never_rejects_anyone(self):
        """Chưa khai giới tính không phải là sai giới tính."""
        result = self._run(full_name="Vũ Thị Lan", education_level="cao_dang",
                           japanese_level="N4")
        self.assertEqual(self._loai_vi(result, "gender"), [])
        self.assertTrue(any("giới tính" in c.lower() for c in result.missing_info))

    def test_plenty_of_experience_never_rejects_anyone(self):
        """Tiêu chí kinh nghiệm là mức tối thiểu, không phải khoảng."""
        result = self._run(full_name="Phạm Minh Tuấn", birth_year=1988, gender="nam",
                           education_level="cao_dang", japanese_level="N4",
                           experience_years=13, care_experience=True)
        self.assertEqual(self._loai_vi(result, "experience"), [])
        self.assertTrue(self._loai_vi(result, "age"), "38 tuổi phải trượt vài đơn vì tuổi")

    def test_a_complete_profile_leaves_no_unclear_row(self):
        result = engine.match_orders(pool(), facts_with(AN, AN_WISHES),
                                     weights=WEIGHTS, as_of=AS_OF)
        chua_ro = [
            (item.code, row.key)
            for item in result.items if item.eligible
            for row in item.hard_rows if row.result == engine.CHUA_RO
        ]
        self.assertEqual(chua_ro, [])


class PreferenceInfluenceTests(unittest.TestCase):
    """Nguyện vọng chỉ đổi thứ tự, không bao giờ loại đơn."""

    def _run(self, preferences: dict) -> engine.MatchResult:
        return engine.match_orders(
            pool(), facts_with(AN, preferences), weights=WEIGHTS, as_of=AS_OF
        )

    def test_changing_a_wish_never_changes_who_qualifies(self):
        baseline = self._run({})
        for wishes in (
            {"desired_prefecture": "Tokyo", "desired_region_group": "kanto"},
            {"desired_region_group": "kyushu"},
            {"desired_employer_type": "benh_vien"},
            {"salary_expectation_jpy": 250000},
            {"budget_vnd": 1},
        ):
            with self.subTest(wishes=wishes):
                self.assertEqual(self._run(wishes).eligible_count, baseline.eligible_count)

    def test_a_wish_does_change_the_order_of_the_shortlist(self):
        kanto = self._run({"desired_region_group": "kanto"}).items[0]
        kyushu = self._run({"desired_region_group": "kyushu"}).items[0]
        self.assertNotEqual(kanto.code, kyushu.code)
        self.assertEqual(kyushu.region_group, "kyushu")

    def test_no_score_can_exceed_one_hundred(self):
        for item in self._run(AN_WISHES).items:
            self.assertLessEqual(item.score, 100)
            self.assertGreaterEqual(item.score, 0)


if __name__ == "__main__":
    unittest.main()
