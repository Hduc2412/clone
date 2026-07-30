import unittest

from app.conversation.entity_extractor import extract_name
from app.conversation.intent_classifier import classify


class IntentClassifierTests(unittest.TestCase):
    def test_specific_intents_win_over_generic_phrases(self):
        self.assertEqual(
            classify("Ký túc xá dành cho học viên như thế nào?"),
            "ky_tuc_xa",
        )
        self.assertEqual(
            classify("Tôi muốn đăng ký để được tư vấn"),
            "lead",
        )
        self.assertEqual(
            classify("Trong thời gian học có được hỗ trợ gì không?"),
            "hoc_tap",
        )
        self.assertEqual(
            classify("Điều kiện tham gia chương trình là gì?"),
            "dieu_kien",
        )

    def test_existing_intents_are_not_regressed(self):
        self.assertEqual(
            classify("Quy trình đăng ký gồm những bước nào?"),
            "quy_trinh",
        )
        self.assertEqual(
            classify("Thời gian đào tạo và xuất cảnh mất bao lâu?"),
            "thoi_gian",
        )
        self.assertEqual(
            classify("Mức lương điều dưỡng tại Nhật là bao nhiêu?"),
            "luong_thuong",
        )


class EntityExtractorTests(unittest.TestCase):
    def test_extract_name_is_case_insensitive(self):
        self.assertEqual(
            extract_name("Tôi tên Trần Minh Test"),
            "Trần Minh Test",
        )
        self.assertEqual(
            extract_name("TÊN TÔI LÀ NGUYỄN VĂN AN"),
            "NGUYỄN VĂN AN",
        )


if __name__ == "__main__":
    unittest.main()
