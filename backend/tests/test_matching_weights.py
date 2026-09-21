"""Kiểm thử cấu hình trọng số xếp hạng.

Trọng số là thứ quyết định đơn nào xếp trên đơn nào. Một lỗi gõ nhầm ở đây không
làm hệ thống đổ, nó chỉ âm thầm cho ra thứ tự sai. Nên phần kiểm tra cấu hình
phải chặt và phải báo lỗi bằng tiếng Việt cho người vận hành đọc được.
"""
import copy
import json
import unittest
from pathlib import Path

from app.matching.weights import (
    DEFAULT_WEIGHTS_PATH,
    TOTAL_POINTS,
    WeightsError,
    clear_cache,
    load_weights,
    parse_weights,
)


def raw_config() -> dict:
    return json.loads(DEFAULT_WEIGHTS_PATH.read_text(encoding="utf-8"))


class DefaultConfigTests(unittest.TestCase):
    def test_default_file_loads(self):
        weights = load_weights()
        self.assertTrue(weights.version)
        self.assertTrue(weights.fingerprint.startswith("sha256:"))

    def test_weight_table_matches_the_report(self):
        weights = load_weights()
        self.assertEqual(
            dict(weights.weights),
            {"region": 40, "employer_type": 30, "salary": 20, "cost": 10},
        )

    def test_sub_rules_match_the_report(self):
        weights = load_weights()
        self.assertEqual(weights.points("region", "same_prefecture"), 40)
        self.assertEqual(weights.points("region", "same_region"), 25)
        self.assertEqual(weights.points("employer_type", "match"), 30)
        self.assertEqual(weights.points("salary", "meets"), 20)
        self.assertEqual(weights.points("salary", "near"), 10)
        self.assertEqual(weights.points("cost", "within"), 10)
        self.assertEqual(weights.points("cost", "unknown"), 5)

    def test_total_is_one_hundred(self):
        self.assertEqual(sum(load_weights().weights.values()), TOTAL_POINTS)

    def test_salary_near_ratio_is_ninety_percent(self):
        self.assertEqual(load_weights().salary_near_ratio, (9, 10))


class ValidationTests(unittest.TestCase):
    def _expect_error(self, mutate, fragment: str):
        config = raw_config()
        mutate(config)
        with self.assertRaises(WeightsError) as raised:
            parse_weights(config)
        self.assertIn(fragment, str(raised.exception))

    def test_total_other_than_one_hundred_is_refused(self):
        def mutate(config):
            config["weights"]["region"] = 50
            config["rules"]["region"]["same_prefecture"] = 50
        self._expect_error(mutate, "100")

    def test_sub_rule_below_its_weight_is_refused(self):
        """Trọng số 40 mà luật cao nhất 35 thì tiêu chí đó không bao giờ đạt tối đa."""
        self._expect_error(
            lambda config: config["rules"]["region"].update({"same_prefecture": 35}),
            "phải bằng nhau",
        )

    def test_missing_criterion_is_refused(self):
        self._expect_error(lambda config: config["weights"].pop("cost"), "Thiếu tiêu chí")

    def test_extra_criterion_is_refused(self):
        self._expect_error(
            lambda config: config["weights"].update({"mau_mat": 0}), "tiêu chí lạ"
        )

    def test_float_weight_is_refused(self):
        """Điểm phải là số nguyên, nếu không tổng điểm không tái lập được từng byte."""
        def mutate(config):
            config["weights"]["region"] = 40.0
        self._expect_error(mutate, "số nguyên")

    def test_negative_weight_is_refused(self):
        def mutate(config):
            config["weights"]["region"] = -40
        self._expect_error(mutate, "không được âm")

    def test_missing_rules_table_is_refused(self):
        self._expect_error(lambda config: config["rules"].pop("salary"), "Thiếu bảng luật")

    def test_bad_salary_ratio_is_refused(self):
        self._expect_error(
            lambda config: config["params"].update({"salary_near_numerator": 0}),
            "salary_near_numerator",
        )

    def test_unknown_outcome_raises_a_readable_error(self):
        weights = load_weights()
        with self.assertRaises(WeightsError) as raised:
            weights.points("region", "khong_ton_tai")
        self.assertIn("khong_ton_tai", str(raised.exception))


class LoadingTests(unittest.TestCase):
    def setUp(self):
        clear_cache()
        self.addCleanup(clear_cache)

    def test_missing_file_raises_instead_of_falling_back(self):
        """Một bộ số dự phòng giấu trong mã nguồn sẽ phá tính giải trình được."""
        with self.assertRaises(WeightsError) as raised:
            load_weights(Path("khong/co/that/weights.json"))
        self.assertIn("Không tìm thấy", str(raised.exception))

    def test_invalid_json_raises(self):
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "weights.json"
            path.write_text("{ đây không phải json", encoding="utf-8")
            with self.assertRaises(WeightsError) as raised:
                load_weights(path)
        self.assertIn("JSON", str(raised.exception))

    def test_same_file_returns_the_cached_object(self):
        self.assertIs(load_weights(), load_weights())

    def test_fingerprint_changes_when_a_weight_changes(self):
        original = parse_weights(raw_config())
        changed_config = copy.deepcopy(raw_config())
        changed_config["weights"]["region"] = 45
        changed_config["weights"]["cost"] = 5
        changed_config["rules"]["region"]["same_prefecture"] = 45
        changed_config["rules"]["cost"]["within"] = 5
        changed = parse_weights(changed_config)
        self.assertNotEqual(original.fingerprint, changed.fingerprint)

    def test_fingerprint_is_stable_across_runs(self):
        self.assertEqual(
            parse_weights(raw_config()).fingerprint,
            parse_weights(raw_config()).fingerprint,
        )


if __name__ == "__main__":
    unittest.main()
