import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.conversation.response_validator import RATE_LIMIT_FALLBACK, validate
from app.conversation.session_manager import MAX_HISTORY_CHARS, Session
from app.llm.gemini import _post_with_retry, generate_response
from app.rag.retriever import search


class GeminiResilienceTests(unittest.TestCase):
    @patch("app.llm.gemini.time.sleep")
    @patch("app.llm.gemini.requests.post")
    def test_generate_rate_limit_fails_fast(self, mocked_post, mocked_sleep):
        response = Mock(status_code=429)
        response.json.return_value = {
            "error": {
                "code": 429,
                "message": "RESOURCE_EXHAUSTED: quota exceeded",
            }
        }
        mocked_post.return_value = response

        result = _post_with_retry(
            "https://example.invalid",
            {},
            "test",
            max_retries=3,
            retry_rate_limit=False,
        )

        self.assertEqual(result["error"]["code"], 429)
        mocked_post.assert_called_once()
        mocked_sleep.assert_not_called()

    @patch("app.llm.gemini._post_with_retry")
    def test_max_tokens_is_retried_once(self, mocked_post):
        mocked_post.side_effect = [
            {
                "candidates": [
                    {
                        "finishReason": "MAX_TOKENS",
                        "content": {"parts": [{"text": "Câu bị cắt"}]},
                    }
                ]
            },
            {
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {"parts": [{"text": "Câu trả lời đầy đủ"}]},
                    }
                ]
            },
        ]

        self.assertEqual(generate_response("prompt"), "Câu trả lời đầy đủ")
        self.assertEqual(mocked_post.call_count, 2)

    @patch("app.llm.gemini._post_with_retry")
    def test_cau_tra_loi_nhieu_part_duoc_gop_du(self, mocked_post):
        """Đo trên gemini-3.8-flash ngày 21/09/2026: model chia câu trả lời thành
        nhiều part. Bản cũ lấy mỗi `parts[0]` nên khách nhận được một câu cụt —
        hỏng mà không báo lỗi, vì mẩu còn lại vẫn đúng ngữ pháp."""
        mocked_post.return_value = {
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {
                        "parts": [
                            {"text": "Nơi làm việc do từng đơn hàng quy định"},
                            {"text": " và không phụ thuộc nơi bạn học tiếng."},
                        ]
                    },
                }
            ]
        }

        self.assertEqual(
            generate_response("prompt"),
            "Nơi làm việc do từng đơn hàng quy định và không phụ thuộc nơi bạn học tiếng.",
        )

    @patch("app.llm.gemini._post_with_retry")
    def test_phan_suy_luan_khong_lot_vao_cau_tra_loi(self, mocked_post):
        """Part `thought` là phần nháp của model, không phải lời nói với khách."""
        mocked_post.return_value = {
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {
                        "parts": [
                            {"text": "Người dùng đang hỏi về...", "thought": True},
                            {"text": "Chương trình yêu cầu tiếng Nhật từ N4."},
                        ]
                    },
                }
            ]
        }

        self.assertEqual(
            generate_response("prompt"),
            "Chương trình yêu cầu tiếng Nhật từ N4.",
        )

    def test_rate_limit_has_friendly_message(self):
        valid, answer = validate(
            "Lỗi Gemini: RESOURCE_EXHAUSTED quota exceeded",
        )
        self.assertFalse(valid)
        self.assertEqual(answer, RATE_LIMIT_FALLBACK)


class RetrievalThresholdTests(unittest.TestCase):
    @patch("app.rag.retriever.get_qdrant_client")
    @patch("app.rag.retriever.create_embedding", return_value=[0.1, 0.2])
    def test_low_score_hits_are_removed(self, _, mocked_client):
        high = SimpleNamespace(score=0.8, payload={"topic": "chi_phi"})
        low = SimpleNamespace(score=0.64, payload={"topic": "chi_phi"})
        mocked_client.return_value.query_points.return_value = SimpleNamespace(
            points=[high, low]
        )

        self.assertEqual(search("chi phí", "chi_phi"), [high])


class HistoryLimitTests(unittest.TestCase):
    def test_prompt_history_has_character_limit(self):
        session = Session(session_id="history-limit")
        for index in range(10):
            session.add_message("user", f"{index}-" + ("x" * 600))

        history = session.get_history_text()

        self.assertLessEqual(len(history), MAX_HISTORY_CHARS)
        self.assertIn("9-", history)
        self.assertNotIn("0-", history)


if __name__ == "__main__":
    unittest.main()
