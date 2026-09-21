"""Kiểm thử bộ đối chiếu.

Đây là bộ kiểm thử quan trọng nhất của đồ án. Bộ đối chiếu quyết định ứng viên nào
được giới thiệu đơn nào, nên mọi tính chất của nó phải chứng minh được bằng số chứ
không phải bằng lời:

- **Tất định**: chạy hai lần ra kết quả giống hệt từng byte, kể cả khi đảo thứ tự
  danh sách đơn đầu vào.
- **Chỉ loại khi chắc chắn**: thiếu dữ liệu không được phép loại đơn.
- **Không đọc đồng hồ**: thời điểm là tham số truyền vào, không phải thứ hàm tự lấy.
"""
import json
import random
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from app.matching import catalog
from app.matching.engine import (
    CHUA_RO,
    DAT,
    HARD_KEYS,
    KHONG_DAT,
    SOFT_KEYS,
    build_facts,
    evaluate_hard,
    evaluate_soft,
    format_years,
    is_eligible,
    match_orders,
)
from app.matching.weights import load_weights


AS_OF = date(2026, 9, 15)
WEIGHTS = load_weights()


def order(**overrides) -> dict:
    """Một đơn hàng đầy đủ; ghi đè từng trường để dựng ca kiểm thử."""
    base = {
        "code": "DH-0001",
        "title": "Điều dưỡng viện dưỡng lão Tokyo",
        "employer_name": "Viện dưỡng lão Sakura",
        "employer_type": "vien_duong_lao",
        "program": "tokutei_ginou",
        "prefecture": "Tokyo",
        "region_group": "kanto",
        "quota": 5,
        "status": "open",
        "deadline": "2026-12-31",
        "requirements": {
            "japanese_required": "N4",
            "education_required": "cao_dang",
            "experience_min": 0,
            "age_min": 20,
            "age_max": 35,
            "gender_pref": "khong_yeu_cau",
        },
        "reference": {
            "salary_min": 195000,
            "salary_max": 215000,
            "cost_total_vnd": 110_000_000,
            "allowances": [],
            "highlights": [],
        },
    }
    requirements = {**base["requirements"], **overrides.pop("requirements", {})}
    reference = {**base["reference"], **overrides.pop("reference", {})}
    return {**base, **overrides, "requirements": requirements, "reference": reference}


def profile(fields: dict | None = None, preferences: dict | None = None) -> dict:
    """Hồ sơ dạng lưu trong database: mỗi trường là một ô có nguồn và độ tin cậy."""
    def cell(value):
        return {"value": value, "source": "user_confirmed", "confidence": 1.0, "evidence": None}

    return {
        "code": "UV-TEST01",
        "version": 1,
        "fields": {key: cell(value) for key, value in (fields or {}).items()},
        "preferences": {key: cell(value) for key, value in (preferences or {}).items()},
    }


def facts_for(fields: dict | None = None, preferences: dict | None = None):
    return build_facts(profile(fields, preferences), AS_OF)


FULL_FIELDS = {
    "full_name": "Nguyễn Thị Mai",
    "birth_year": 2003,
    "gender": "nu",
    "education_level": "cao_dang",
    "japanese_level": "N4",
    "experience_years": 0,
}
FULL_PREFERENCES = {
    "desired_prefecture": "Tokyo",
    "desired_employer_type": "vien_duong_lao",
    "salary_expectation_jpy": 180000,
    "budget_vnd": 120_000_000,
}


def row_by_key(rows, key):
    return next(row for row in rows if row.key == key)


# --- Điều kiện bắt buộc ---


class HardCriteriaShapeTests(unittest.TestCase):
    def test_always_seven_rows_in_a_fixed_order(self):
        for fields in (FULL_FIELDS, {}):
            rows = evaluate_hard(order(), facts_for(fields), AS_OF)
            self.assertEqual(tuple(row.key for row in rows), HARD_KEYS)

    def test_every_row_has_vietnamese_texts(self):
        for row in evaluate_hard(order(), facts_for(FULL_FIELDS), AS_OF):
            self.assertTrue(row.requirement_text)
            self.assertTrue(row.candidate_text)
            self.assertIn(row.result, (DAT, KHONG_DAT, CHUA_RO))


class StatusAndDeadlineTests(unittest.TestCase):
    def test_open_order_passes(self):
        rows = evaluate_hard(order(), facts_for(FULL_FIELDS), AS_OF)
        self.assertEqual(row_by_key(rows, "status").result, DAT)

    def test_non_open_statuses_are_refused(self):
        for status in ("draft", "paused", "filled", "expired", "closed"):
            rows = evaluate_hard(order(status=status), facts_for(FULL_FIELDS), AS_OF)
            self.assertEqual(row_by_key(rows, "status").result, KHONG_DAT, msg=status)

    def test_status_is_never_unknown(self):
        """Đơn hàng thiếu dữ liệu thì hỏng là loại, khác với hồ sơ ứng viên."""
        rows = evaluate_hard(order(status=None), facts_for(FULL_FIELDS), AS_OF)
        self.assertEqual(row_by_key(rows, "status").result, KHONG_DAT)

    def test_expired_order_is_eliminated(self):
        rows = evaluate_hard(
            order(deadline=(AS_OF - timedelta(days=1)).isoformat()),
            facts_for(FULL_FIELDS),
            AS_OF,
        )
        self.assertEqual(row_by_key(rows, "deadline").result, KHONG_DAT)
        self.assertFalse(is_eligible(rows))

    def test_deadline_today_still_counts(self):
        rows = evaluate_hard(order(deadline=AS_OF.isoformat()), facts_for(FULL_FIELDS), AS_OF)
        self.assertEqual(row_by_key(rows, "deadline").result, DAT)

    def test_unparsable_deadline_is_refused(self):
        rows = evaluate_hard(order(deadline="cuối năm"), facts_for(FULL_FIELDS), AS_OF)
        self.assertEqual(row_by_key(rows, "deadline").result, KHONG_DAT)


class JapaneseCriterionTests(unittest.TestCase):
    def test_equal_level_passes(self):
        rows = evaluate_hard(order(), facts_for({"japanese_level": "N4"}), AS_OF)
        self.assertEqual(row_by_key(rows, "japanese").result, DAT)

    def test_higher_level_passes(self):
        rows = evaluate_hard(order(), facts_for({"japanese_level": "N2"}), AS_OF)
        self.assertEqual(row_by_key(rows, "japanese").result, DAT)

    def test_lower_level_is_refused(self):
        rows = evaluate_hard(order(), facts_for({"japanese_level": "N5"}), AS_OF)
        self.assertEqual(row_by_key(rows, "japanese").result, KHONG_DAT)

    def test_missing_level_is_unknown_and_asks(self):
        row = row_by_key(evaluate_hard(order(), facts_for({}), AS_OF), "japanese")
        self.assertEqual(row.result, CHUA_RO)
        self.assertEqual(row.missing_field, "japanese_level")

    def test_chua_hoc_is_below_n5(self):
        requirement = {"japanese_required": "N5"}
        rows = evaluate_hard(
            order(requirements=requirement), facts_for({"japanese_level": "chua_hoc"}), AS_OF
        )
        self.assertEqual(row_by_key(rows, "japanese").result, KHONG_DAT)

    def test_chua_hoc_passes_an_order_that_requires_nothing(self):
        rows = evaluate_hard(
            order(requirements={"japanese_required": "chua_hoc"}),
            facts_for({"japanese_level": "chua_hoc"}),
            AS_OF,
        )
        self.assertEqual(row_by_key(rows, "japanese").result, DAT)


class EducationCriterionTests(unittest.TestCase):
    def test_requirement_none_passes_even_without_candidate_data(self):
        rows = evaluate_hard(
            order(requirements={"education_required": None}), facts_for({}), AS_OF
        )
        row = row_by_key(rows, "education")
        self.assertEqual(row.result, DAT)
        self.assertIsNone(row.missing_field)

    def test_higher_degree_passes(self):
        rows = evaluate_hard(order(), facts_for({"education_level": "dai_hoc"}), AS_OF)
        self.assertEqual(row_by_key(rows, "education").result, DAT)

    def test_lower_degree_is_refused(self):
        rows = evaluate_hard(order(), facts_for({"education_level": "trung_cap"}), AS_OF)
        self.assertEqual(row_by_key(rows, "education").result, KHONG_DAT)

    def test_missing_degree_is_unknown_when_required(self):
        row = row_by_key(evaluate_hard(order(), facts_for({}), AS_OF), "education")
        self.assertEqual(row.result, CHUA_RO)
        self.assertEqual(row.missing_field, "education_level")


class ExperienceCriterionTests(unittest.TestCase):
    def test_zero_requirement_passes_with_unknown_candidate(self):
        row = row_by_key(evaluate_hard(order(), facts_for({}), AS_OF), "experience")
        self.assertEqual(row.result, DAT)
        self.assertIsNone(row.missing_field)

    def test_enough_experience_passes(self):
        rows = evaluate_hard(
            order(requirements={"experience_min": 2}),
            facts_for({"experience_years": 2}),
            AS_OF,
        )
        self.assertEqual(row_by_key(rows, "experience").result, DAT)

    def test_not_enough_experience_is_refused(self):
        rows = evaluate_hard(
            order(requirements={"experience_min": 2}),
            facts_for({"experience_years": 1}),
            AS_OF,
        )
        self.assertEqual(row_by_key(rows, "experience").result, KHONG_DAT)

    def test_unknown_experience_is_unknown_when_required(self):
        rows = evaluate_hard(order(requirements={"experience_min": 2}), facts_for({}), AS_OF)
        row = row_by_key(rows, "experience")
        self.assertEqual(row.result, CHUA_RO)
        self.assertEqual(row.missing_field, "experience_years")


class AgeCriterionTests(unittest.TestCase):
    def test_no_bounds_passes(self):
        rows = evaluate_hard(
            order(requirements={"age_min": None, "age_max": None}), facts_for({}), AS_OF
        )
        self.assertEqual(row_by_key(rows, "age").result, DAT)

    def test_inside_range_passes(self):
        rows = evaluate_hard(order(), facts_for({"birth_year": 2003}), AS_OF)
        self.assertEqual(row_by_key(rows, "age").result, DAT)

    def test_above_maximum_is_refused(self):
        rows = evaluate_hard(order(), facts_for({"birth_year": 1988}), AS_OF)
        self.assertEqual(row_by_key(rows, "age").result, KHONG_DAT)

    def test_below_minimum_is_refused(self):
        rows = evaluate_hard(order(), facts_for({"birth_year": 2012}), AS_OF)
        self.assertEqual(row_by_key(rows, "age").result, KHONG_DAT)

    def test_only_lower_bound_leaves_upper_side_unchecked(self):
        rows = evaluate_hard(
            order(requirements={"age_min": 20, "age_max": None}),
            facts_for({"birth_year": 1970}),
            AS_OF,
        )
        self.assertEqual(row_by_key(rows, "age").result, DAT)

    def test_missing_birth_year_is_unknown_and_asks(self):
        row = row_by_key(evaluate_hard(order(), facts_for({}), AS_OF), "age")
        self.assertEqual(row.result, CHUA_RO)
        self.assertEqual(row.missing_field, "birth_year")


class GenderCriterionTests(unittest.TestCase):
    def test_no_preference_passes_with_unknown_gender(self):
        row = row_by_key(evaluate_hard(order(), facts_for({}), AS_OF), "gender")
        self.assertEqual(row.result, DAT)
        self.assertIsNone(row.missing_field)

    def test_matching_gender_passes(self):
        rows = evaluate_hard(
            order(requirements={"gender_pref": "nu"}), facts_for({"gender": "nu"}), AS_OF
        )
        self.assertEqual(row_by_key(rows, "gender").result, DAT)

    def test_other_gender_is_refused(self):
        rows = evaluate_hard(
            order(requirements={"gender_pref": "nu"}), facts_for({"gender": "nam"}), AS_OF
        )
        self.assertEqual(row_by_key(rows, "gender").result, KHONG_DAT)

    def test_unknown_gender_is_unknown_when_required(self):
        rows = evaluate_hard(order(requirements={"gender_pref": "nu"}), facts_for({}), AS_OF)
        row = row_by_key(rows, "gender")
        self.assertEqual(row.result, CHUA_RO)
        self.assertEqual(row.missing_field, "gender")


class UnknownNeverEliminatesTests(unittest.TestCase):
    """Quy tắc trung tâm: cái chưa biết không được phép loại đơn."""

    def test_an_almost_empty_profile_still_gets_eligible_orders(self):
        rows = evaluate_hard(order(), facts_for({"full_name": "Nguyễn Văn A"}), AS_OF)
        self.assertTrue(is_eligible(rows))
        self.assertTrue(any(row.result == CHUA_RO for row in rows))
        self.assertFalse(any(row.result == KHONG_DAT for row in rows))

    def test_unknowns_become_questions_not_gaps(self):
        result = match_orders(
            [order()], facts_for({}), weights=WEIGHTS, as_of=AS_OF
        )
        item = result.items[0]
        self.assertTrue(item.eligible)
        self.assertEqual(item.gaps, ())
        self.assertTrue(item.missing_info)


# --- Xếp hạng mềm ---


class SoftScoringTests(unittest.TestCase):
    def _row(self, key, fields=None, preferences=None, **order_overrides):
        rows = evaluate_soft(
            order(**order_overrides), facts_for(fields, preferences), WEIGHTS
        )
        return row_by_key(rows, key)

    def test_always_four_rows_in_a_fixed_order(self):
        rows = evaluate_soft(order(), facts_for(FULL_FIELDS, FULL_PREFERENCES), WEIGHTS)
        self.assertEqual(tuple(row.key for row in rows), SOFT_KEYS)

    def test_same_prefecture_scores_forty(self):
        row = self._row("region", preferences={"desired_prefecture": "Tokyo"})
        self.assertEqual((row.outcome, row.points), ("same_prefecture", 40))

    def test_same_region_other_prefecture_scores_twenty_five(self):
        row = self._row("region", preferences={"desired_prefecture": "Chiba"})
        self.assertEqual((row.outcome, row.points), ("same_region", 25))

    def test_other_region_scores_zero(self):
        row = self._row("region", preferences={"desired_prefecture": "Fukuoka"})
        self.assertEqual((row.outcome, row.points), ("different", 0))

    def test_unknown_region_scores_zero_and_asks(self):
        row = self._row("region")
        self.assertEqual((row.outcome, row.points), ("unknown", 0))
        self.assertEqual(row.missing_field, "desired_prefecture")

    def test_employer_type_match_scores_thirty(self):
        row = self._row("employer_type", preferences={"desired_employer_type": "vien_duong_lao"})
        self.assertEqual((row.outcome, row.points), ("match", 30))

    def test_employer_type_mismatch_scores_zero(self):
        row = self._row("employer_type", preferences={"desired_employer_type": "benh_vien"})
        self.assertEqual((row.outcome, row.points), ("different", 0))

    def test_salary_meeting_expectation_scores_twenty(self):
        row = self._row("salary", preferences={"salary_expectation_jpy": 180000})
        self.assertEqual((row.outcome, row.points), ("meets", 20))

    def test_salary_within_ten_percent_scores_ten(self):
        """Đơn trả 215.000 với kỳ vọng 230.000: thiếu dưới mười phần trăm."""
        row = self._row("salary", preferences={"salary_expectation_jpy": 230000})
        self.assertEqual((row.outcome, row.points), ("near", 10))

    def test_salary_further_below_scores_zero(self):
        row = self._row("salary", preferences={"salary_expectation_jpy": 300000})
        self.assertEqual((row.outcome, row.points), ("below", 0))

    def test_cost_within_budget_scores_ten(self):
        row = self._row("cost", preferences={"budget_vnd": 120_000_000})
        self.assertEqual((row.outcome, row.points), ("within", 10))

    def test_cost_over_budget_scores_zero(self):
        row = self._row("cost", preferences={"budget_vnd": 50_000_000})
        self.assertEqual((row.outcome, row.points), ("over", 0))

    def test_unknown_cost_scores_five(self):
        """Đơn chưa rõ chi phí không nên bị đẩy xuống dưới đơn đã biết là quá khả năng."""
        row = self._row("cost")
        self.assertEqual((row.outcome, row.points), ("unknown", 5))

    def test_perfect_match_scores_one_hundred(self):
        rows = evaluate_soft(order(), facts_for(FULL_FIELDS, FULL_PREFERENCES), WEIGHTS)
        self.assertEqual(sum(row.points for row in rows), 100)

    def test_eliminated_order_has_no_soft_rows_and_no_score(self):
        result = match_orders(
            [order(status="closed")],
            facts_for(FULL_FIELDS, FULL_PREFERENCES),
            weights=WEIGHTS,
            as_of=AS_OF,
        )
        item = result.items[0]
        self.assertFalse(item.eligible)
        self.assertEqual(item.soft_rows, ())
        self.assertEqual(item.score, 0)
        self.assertIsNone(item.rank)


# --- Đối chiếu toàn danh mục ---


class MatchOrdersTests(unittest.TestCase):
    def _pool(self):
        return [
            order(code="DH-0001", prefecture="Tokyo", region_group="kanto"),
            order(code="DH-0002", prefecture="Osaka", region_group="kansai"),
            order(code="DH-0003", prefecture="Chiba", region_group="kanto"),
            order(code="DH-0004", status="closed"),
            order(code="DH-0005", requirements={"japanese_required": "N2"}),
        ]

    def test_running_twice_gives_byte_identical_output(self):
        facts = facts_for(FULL_FIELDS, FULL_PREFERENCES)
        first = json.dumps(
            match_orders(self._pool(), facts, weights=WEIGHTS, as_of=AS_OF).as_dict(),
            ensure_ascii=False, sort_keys=True,
        )
        second = json.dumps(
            match_orders(self._pool(), facts, weights=WEIGHTS, as_of=AS_OF).as_dict(),
            ensure_ascii=False, sort_keys=True,
        )
        self.assertEqual(first, second)

    def test_shuffling_the_input_does_not_change_the_output(self):
        """Thứ tự MongoDB trả về không được ảnh hưởng tới kết quả xếp hạng."""
        facts = facts_for(FULL_FIELDS, FULL_PREFERENCES)
        expected = json.dumps(
            match_orders(self._pool(), facts, weights=WEIGHTS, as_of=AS_OF).as_dict(),
            ensure_ascii=False, sort_keys=True,
        )
        shuffled = self._pool()
        random.Random(7).shuffle(shuffled)
        actual = json.dumps(
            match_orders(shuffled, facts, weights=WEIGHTS, as_of=AS_OF).as_dict(),
            ensure_ascii=False, sort_keys=True,
        )
        self.assertEqual(expected, actual)

    def test_ranks_only_go_to_eligible_orders_and_start_at_one(self):
        result = match_orders(
            self._pool(), facts_for(FULL_FIELDS, FULL_PREFERENCES),
            weights=WEIGHTS, as_of=AS_OF,
        )
        ranks = [item.rank for item in result.items if item.eligible]
        self.assertEqual(ranks, list(range(1, len(ranks) + 1)))
        self.assertTrue(all(item.rank is None for item in result.items if not item.eligible))

    def test_eliminated_orders_come_after_eligible_ones(self):
        result = match_orders(
            self._pool(), facts_for(FULL_FIELDS, FULL_PREFERENCES),
            weights=WEIGHTS, as_of=AS_OF,
        )
        flags = [item.eligible for item in result.items]
        self.assertEqual(flags, sorted(flags, reverse=True))

    def test_tie_break_prefers_the_earlier_deadline(self):
        pool = [
            order(code="DH-0009", deadline="2026-11-01"),
            order(code="DH-0008", deadline="2026-10-01"),
        ]
        result = match_orders(
            pool, facts_for(FULL_FIELDS, FULL_PREFERENCES), weights=WEIGHTS, as_of=AS_OF
        )
        self.assertEqual([item.code for item in result.items], ["DH-0008", "DH-0009"])

    def test_tie_break_falls_back_to_code(self):
        pool = [order(code="DH-0009"), order(code="DH-0002")]
        result = match_orders(
            pool, facts_for(FULL_FIELDS, FULL_PREFERENCES), weights=WEIGHTS, as_of=AS_OF
        )
        self.assertEqual([item.code for item in result.items], ["DH-0002", "DH-0009"])

    def test_eliminated_order_keeps_all_seven_hard_rows(self):
        result = match_orders(
            [order(status="closed")], facts_for(FULL_FIELDS), weights=WEIGHTS, as_of=AS_OF
        )
        self.assertEqual(len(result.items[0].hard_rows), len(HARD_KEYS))

    def test_gaps_explain_every_failed_criterion(self):
        result = match_orders(
            [order(requirements={"japanese_required": "N2"})],
            facts_for(FULL_FIELDS, FULL_PREFERENCES),
            weights=WEIGHTS, as_of=AS_OF,
        )
        gaps = result.items[0].gaps
        self.assertTrue(gaps)
        self.assertTrue(any("Tiếng Nhật" in gap for gap in gaps))

    def test_global_missing_info_is_deduplicated_and_ordered(self):
        result = match_orders(
            self._pool(), facts_for({}), weights=WEIGHTS, as_of=AS_OF
        )
        self.assertEqual(len(result.missing_info), len(set(result.missing_info)))
        self.assertTrue(result.missing_info)

    def test_result_records_engine_and_weights_versions(self):
        result = match_orders(
            [order()], facts_for(FULL_FIELDS), weights=WEIGHTS, as_of=AS_OF
        )
        self.assertEqual(result.as_of, AS_OF.isoformat())
        self.assertTrue(result.engine_version)
        self.assertTrue(result.weights_fingerprint.startswith("sha256:"))

    def test_engine_never_reads_the_clock(self):
        """Đọc đồng hồ bên trong sẽ phá tính tái lập; thời điểm phải là tham số."""
        with patch("app.core.timeutil.local_today", side_effect=AssertionError("đã gọi đồng hồ")):
            match_orders(
                self._pool(), facts_for(FULL_FIELDS, FULL_PREFERENCES),
                weights=WEIGHTS, as_of=AS_OF,
            )


class FactsAndFormattingTests(unittest.TestCase):
    def test_region_is_derived_when_only_prefecture_is_given(self):
        facts = facts_for(preferences={"desired_prefecture": "Osaka"})
        self.assertEqual(facts.desired_region_group, "kansai")

    def test_absent_field_is_unknown(self):
        facts = facts_for({})
        self.assertIsNone(facts.japanese_level)
        self.assertIsNone(facts.age)

    def test_chua_hoc_is_a_known_answer_not_a_missing_one(self):
        """"Chưa học" là câu trả lời đã có, khác hẳn với chưa khai."""
        facts = facts_for({"japanese_level": "chua_hoc"})
        self.assertEqual(facts.japanese_level, "chua_hoc")
        self.assertEqual(facts.japanese_rank, 0)

    def test_year_formatting_uses_vietnamese_decimal_comma(self):
        self.assertEqual(format_years(2.0), "2")
        self.assertEqual(format_years(1.5), "1,5")

    def test_result_labels_cover_every_outcome(self):
        for result in (DAT, KHONG_DAT, CHUA_RO):
            self.assertIn(result, catalog.RESULT_LABELS)


if __name__ == "__main__":
    unittest.main()
