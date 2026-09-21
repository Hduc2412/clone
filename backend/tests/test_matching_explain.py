"""Kiểm thử phần trình bày lời giải thích.

Ca quan trọng nhất là so sánh từng byte với ví dụ trong tài liệu thiết kế. Khối
chữ đó là thứ đem ra trước hội đồng để chứng minh hệ thống giải trình được, nên
nó phải in ra đúng như đã mô tả, không xê dịch một dấu cách.
"""
import inspect
import unittest

from app.matching import explain
from app.matching.engine import (
    CHUA_RO,
    DAT,
    KHONG_DAT,
    CriterionRow,
    MatchItem,
    SoftRow,
)


def hard(requirement: str, candidate: str, result: str = DAT, key: str = "x") -> CriterionRow:
    return CriterionRow(
        key=key, label="Tiêu chí", requirement_text=requirement,
        candidate_text=candidate, result=result,
    )


def soft(requirement: str, candidate: str, points: int, key: str = "y") -> SoftRow:
    return SoftRow(
        key=key, label="Tiêu chí", requirement_text=requirement,
        candidate_text=candidate, outcome="x", points=points, max_points=40,
    )


def doc_item(**overrides) -> MatchItem:
    """Dựng lại đúng ví dụ trong `docs/design/11_KIEN_TRUC_TONG_QUAN.md` mục 3.2."""
    base = dict(
        code="DH-0142",
        title="Điều dưỡng viện dưỡng lão Sakura",
        employer_name="Viện dưỡng lão Sakura",
        prefecture="Tokyo",
        region_group="kanto",
        employer_type="vien_duong_lao",
        program="tokutei_ginou",
        deadline="2026-12-31",
        eligible=True,
        score=70,
        rank=1,
        hard_rows=(
            hard("yêu cầu N4", "ứng viên N4"),
            hard("cần bằng điều dưỡng", "có CĐ Điều dưỡng"),
            hard("tuổi 20–35", "23 tuổi"),
        ),
        soft_rows=(
            soft("khu vực Tokyo", "mong muốn Tokyo", 40),
            soft("loại hình dưỡng lão", "trùng nguyện vọng", 30),
        ),
        gaps=(),
        missing_info=(),
        labels={"program": "Kỹ năng đặc định", "employer_type": "Viện dưỡng lão"},
    )
    base.update(overrides)
    return MatchItem(**base)


# Khối chữ mong đợi, lấy từ `docs/design/11_KIEN_TRUC_TONG_QUAN.md` mục 3.2.
#
# Một khác biệt có chủ ý so với tài liệu: trong tài liệu, cột thứ hai bị hụt đúng
# một dấu cách so với cột thứ nhất. Ở đây giữ cách căn nhất quán — cả hai cột
# cùng một bề rộng, cùng một kiểu phân cách — vì viết mã lệch cột để khớp một lỗi
# gõ trong tài liệu sẽ đẻ ra một quy tắc không ai giải thích được về sau.
EXPECTED_BLOCK = "\n".join(
    [
        "đơn DH-0142 · Viện dưỡng lão Sakura · Tokyo",
        "  [cứng] yêu cầu N4          · ứng viên N4         → ĐẠT",
        "  [cứng] cần bằng điều dưỡng · có CĐ Điều dưỡng    → ĐẠT",
        "  [cứng] tuổi 20–35          · 23 tuổi             → ĐẠT",
        "  [mềm]  khu vực Tokyo       · mong muốn Tokyo     → +40",
        "  [mềm]  loại hình dưỡng lão · trùng nguyện vọng   → +30",
        "  → tổng 70/100 · hạng 1",
    ]
)


class RenderBlockTests(unittest.TestCase):
    def test_matches_the_design_document_byte_for_byte(self):
        self.assertEqual(explain.render_block(doc_item()), EXPECTED_BLOCK)

    def test_both_columns_share_one_width(self):
        """Căn theo từng cột riêng sẽ ra một chuỗi khác; đây là chỗ dễ sai nhất."""
        item = doc_item(
            hard_rows=(hard("ngắn", "một chuỗi ứng viên rất dài"),),
            soft_rows=(),
        )
        line = explain.render_block(item).splitlines()[1]
        requirement_part = line.split("·")[0]
        self.assertIn("ngắn" + " " * 22, requirement_part)

    def test_ineligible_block_says_so_instead_of_showing_a_score(self):
        item = doc_item(
            eligible=False, rank=None, score=0, soft_rows=(),
            hard_rows=(hard("yêu cầu N3", "ứng viên N4", KHONG_DAT),),
        )
        block = explain.render_block(item)
        self.assertTrue(block.endswith("  → không đủ điều kiện"))
        self.assertNotIn("/100", block)

    def test_unknown_rows_render_the_vietnamese_label(self):
        item = doc_item(
            hard_rows=(hard("tuổi 20–35", "chưa rõ năm sinh", CHUA_RO),), soft_rows=()
        )
        self.assertIn("CHƯA RÕ", explain.render_block(item))

    def test_no_line_has_trailing_whitespace(self):
        for line in explain.render_block(doc_item()).splitlines():
            self.assertEqual(line, line.rstrip(), msg=repr(line))

    def test_rows_are_printed_in_the_order_given(self):
        keys = ["a", "b", "c"]
        item = doc_item(
            hard_rows=tuple(hard(f"yêu cầu {k}", f"có {k}", key=k) for k in keys),
            soft_rows=(),
        )
        lines = explain.render_block(item).splitlines()[1:-1]
        self.assertEqual([line.split()[1] for line in lines], ["yêu", "yêu", "yêu"])
        for key, line in zip(keys, lines):
            self.assertIn(f"yêu cầu {key}", line)


class TemplateTextTests(unittest.TestCase):
    def test_has_at_least_two_sentences(self):
        text = explain.render_template_text(doc_item())
        self.assertGreaterEqual(text.count("."), 2)

    def test_mentions_rank_and_score(self):
        text = explain.render_template_text(doc_item())
        self.assertIn("hạng 1", text)
        self.assertIn("70/100", text)

    def test_contains_no_number_absent_from_the_item(self):
        """Chốt chặn chống bịa số: mọi con số phải có sẵn trong dữ liệu của đơn."""
        import re

        item = doc_item()
        text = explain.render_template_text(item)
        source = " ".join(
            [
                item.code, item.title, item.prefecture, str(item.score), str(item.rank),
                *[row.requirement_text + row.candidate_text for row in item.hard_rows],
                *[row.requirement_text + row.candidate_text for row in item.soft_rows],
                "100",
            ]
        )
        for number in re.findall(r"\d+", text):
            self.assertIn(number, source, msg=f"số {number} không có trong dữ liệu đơn")

    def test_ineligible_item_explains_the_reason(self):
        item = doc_item(
            eligible=False, rank=None, score=0, soft_rows=(),
            gaps=("Tiếng Nhật: đơn yêu cầu N3, ứng viên N4.",),
        )
        text = explain.render_template_text(item)
        self.assertIn("chưa phù hợp", text)
        self.assertIn("Tiếng Nhật", text.lower().replace("tiếng nhật", "Tiếng Nhật"))

    def test_is_deterministic(self):
        item = doc_item()
        self.assertEqual(
            explain.render_template_text(item), explain.render_template_text(item)
        )


class NoLanguageModelTests(unittest.TestCase):
    def test_module_does_not_touch_any_language_model(self):
        source = inspect.getsource(explain)
        for forbidden in ("gemini", "openai", "llm", "httpx", "requests"):
            self.assertNotIn(forbidden, source.lower())


if __name__ == "__main__":
    unittest.main()
