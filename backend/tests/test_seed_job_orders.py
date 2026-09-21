"""Kiểm thử bộ đơn tuyển dụng mẫu.

Dữ liệu mẫu là thứ hội đồng nhìn thấy khi demo, nên nó phải đúng và phải đủ đa
dạng để chứng minh bộ lọc điều kiện hoạt động. Một bộ dữ liệu mà đơn nào cũng
yêu cầu N4 thì không chứng minh được điều gì.
"""
import unittest
from datetime import date

from app.matching import catalog
from scripts.seed_data.job_orders_seed import JOB_ORDERS_SEED
from scripts.seed_job_orders import build_documents, summarize


class SeedDataShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = build_documents()

    def test_every_entry_builds_and_gets_a_unique_sequential_code(self):
        codes = [document["code"] for document in self.documents]
        self.assertEqual(len(codes), len(JOB_ORDERS_SEED))
        self.assertEqual(len(set(codes)), len(codes))
        self.assertEqual(codes[0], "DH-0001")
        self.assertEqual(codes[-1], f"DH-{len(codes):04d}")

    def test_enums_are_stored_as_codes_not_labels(self):
        for document in self.documents:
            self.assertIn(document["employer_type"], catalog.EMPLOYER_TYPE_LABELS)
            self.assertIn(document["program"], catalog.PROGRAM_LABELS)
            self.assertIn(document["status"], catalog.JOB_ORDER_STATUS_LABELS)
            self.assertIn(
                document["requirements"]["japanese_required"],
                catalog.JAPANESE_LEVEL_LABELS,
            )

    def test_region_is_derived_for_every_order(self):
        for document in self.documents:
            self.assertEqual(
                document["region_group"],
                catalog.region_for_prefecture(document["prefecture"]),
            )

    def test_dates_are_iso_strings_so_they_compare_in_queries(self):
        for document in self.documents:
            date.fromisoformat(document["deadline"])
            interview = document["reference"]["interview_date"]
            if interview:
                date.fromisoformat(interview)

    def test_ranges_are_coherent(self):
        for document in self.documents:
            requirements = document["requirements"]
            reference = document["reference"]
            self.assertGreaterEqual(document["quota"], 1)
            self.assertLessEqual(requirements["age_min"], requirements["age_max"])
            if reference["salary_min"] and reference["salary_max"]:
                self.assertLessEqual(reference["salary_min"], reference["salary_max"])


class SeedCoverageTests(unittest.TestCase):
    """Bộ dữ liệu phải tạo ra được sự tương phản, nếu không thì demo vô nghĩa."""

    @classmethod
    def setUpClass(cls):
        cls.documents = build_documents()
        cls.report = summarize(cls.documents)

    def test_covers_all_three_programs_and_employer_types(self):
        self.assertEqual(len(self.report["theo_chuong_trinh"]), 3)
        self.assertEqual(len(self.report["theo_loai_hinh"]), 3)

    def test_spreads_across_at_least_four_regions(self):
        self.assertGreaterEqual(len(self.report["theo_vung"]), 4)

    def test_japanese_requirement_varies_so_the_hard_filter_can_be_shown(self):
        """Hồ sơ N4 phải vừa đạt đơn này vừa trượt đơn kia mới chứng minh được bộ lọc."""
        self.assertEqual(set(self.report["muc_tieng_nhat"]), {"N5", "N4", "N3"})

    def test_some_orders_require_experience_and_some_do_not(self):
        experience = {
            document["requirements"]["experience_min"] for document in self.documents
        }
        self.assertIn(0.0, experience)
        self.assertTrue(any(value > 0 for value in experience))

    def test_some_order_restricts_gender(self):
        genders = {
            document["requirements"]["gender_pref"] for document in self.documents
        }
        self.assertIn("khong_yeu_cau", genders)
        self.assertTrue(genders - {"khong_yeu_cau"})


class SeedVisibilityTests(unittest.TestCase):
    """Ba đơn cố ý bị ẩn, mỗi đơn một lý do, để kiểm tra bộ lọc công khai."""

    @classmethod
    def setUpClass(cls):
        cls.documents = build_documents()
        cls.today = date.today().isoformat()

    def _hidden(self) -> list[dict]:
        return [
            document
            for document in self.documents
            if not (
                document["published"]
                and document["status"] == "open"
                and document["deadline"] >= self.today
            )
        ]

    def test_exactly_three_orders_are_hidden_from_the_website(self):
        self.assertEqual(len(self._hidden()), 3)

    def test_hidden_orders_cover_three_different_reasons(self):
        hidden = self._hidden()
        statuses = {document["status"] for document in hidden}
        self.assertIn("draft", statuses)
        self.assertIn("paused", statuses)
        self.assertTrue(
            any(
                document["status"] == "open" and document["deadline"] < self.today
                for document in hidden
            ),
            "Cần một đơn đang tuyển nhưng đã quá hạn để kiểm tra bộ lọc hạn nộp.",
        )

    def test_seed_orders_are_marked_so_reset_never_touches_real_data(self):
        for document in self.documents:
            self.assertEqual(document["created_by"], "seed")


if __name__ == "__main__":
    unittest.main()
