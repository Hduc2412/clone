"""Kiểm thử luồng điều phối chat: fallback, nguồn tham khảo và phân loại ý định."""
import os
import unittest
from contextlib import ExitStack, contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("JWT_SECRET", "test-secret-that-is-long-enough-for-chat-tests")

from app.services import chat_service
from app.rag.retriever import search


def make_hit(score: float = 0.88, url: str = "https://example.test/chi-phi"):
    return SimpleNamespace(
        score=score,
        payload={
            "title": "Chi phí chương trình",
            "text": "Tổng chi phí gồm phí dịch vụ, đào tạo tiếng Nhật...",
            "url": url,
            "image": "",
            "topic": "chi_phi",
        },
    )


class ChatFallbackTests(unittest.IsolatedAsyncioTestCase):
    """Khi câu trả lời bị chặn thì không được kèm nguồn tham khảo."""

    @contextmanager
    def _patches(self, hits, gemini_answer):
        with ExitStack() as stack:
            for patcher in (
                patch.object(chat_service, "get_messages", new=AsyncMock(return_value=[])),
                patch.object(
                    chat_service, "get_booking_draft", new=AsyncMock(return_value=None)
                ),
                patch.object(chat_service, "save_message", new=AsyncMock()),
                patch.object(chat_service, "search", new=lambda query, intent: hits),
                patch.object(
                    chat_service, "generate_response", new=lambda prompt: gemini_answer
                ),
            ):
                stack.enter_context(patcher)
            yield

    async def test_blocked_answer_returns_no_sources(self):
        with self._patches([make_hit()], "Lỗi Gemini: RESOURCE_EXHAUSTED quota exceeded"):
            result = await chat_service.process_message("Chi phí bao nhiêu ạ?", "sess-block")

        self.assertTrue(result["is_fallback"])
        self.assertEqual(result["sources"], [])

    async def test_valid_answer_keeps_sources(self):
        answer = "Tổng chi phí chương trình gồm phí dịch vụ và đào tạo tiếng Nhật."
        with self._patches([make_hit()], answer):
            result = await chat_service.process_message("Chi phí bao nhiêu ạ?", "sess-ok")

        self.assertFalse(result["is_fallback"])
        self.assertEqual(len(result["sources"]), 1)
        self.assertTrue(result["sources"][0]["is_primary"])

    async def test_no_hit_is_marked_as_fallback(self):
        with self._patches([], "không được dùng tới"):
            result = await chat_service.process_message("Hỏi gì đó lạ", "sess-empty")

        self.assertTrue(result["is_fallback"])
        self.assertEqual(result["sources"], [])


class IntentFromResolvedQueryTests(unittest.IsolatedAsyncioTestCase):
    """Câu hỏi nối tiếp không có từ khóa vẫn phải lấy được ý định từ ngữ cảnh."""

    async def test_follow_up_question_inherits_intent_from_context(self):
        history = [
            {"role": "user", "content": "Chi phí đi điều dưỡng Nhật hết bao nhiêu ạ?"},
            {"role": "assistant", "content": "Tổng chi phí chương trình khoảng ..."},
        ]
        seen = {}

        def fake_search(query, intent):
            seen["intent"] = intent
            return [make_hit()]

        with (
            patch.object(chat_service, "get_messages", new=AsyncMock(return_value=history)),
            patch.object(chat_service, "get_booking_draft", new=AsyncMock(return_value=None)),
            patch.object(chat_service, "save_message", new=AsyncMock()),
            patch.object(chat_service, "search", new=fake_search),
            patch.object(
                chat_service,
                "generate_response",
                new=lambda prompt: "Chi phí đã bao gồm vé máy bay một chiều.",
            ),
        ):
            await chat_service.process_message(
                "Thế cái đó đã gồm vé máy bay chưa ạ?", "sess-follow"
            )

        self.assertEqual(seen["intent"], "chi_phi")


class RetrieverRankingTests(unittest.TestCase):
    """Chủ đề không được can thiệp vào việc chọn đoạn — đo thật cho thấy làm hỏng."""

    @staticmethod
    def _hit(score, topic, title=""):
        return SimpleNamespace(score=score, payload={"topic": topic, "title": title})

    @patch("app.rag.retriever.get_qdrant_client")
    @patch("app.rag.retriever.create_embedding", return_value=[0.1, 0.2])
    def test_searches_whole_collection_without_filter(self, _, mocked_client):
        found = self._hit(0.9, "chi_phi")
        mocked_client.return_value.query_points.return_value = SimpleNamespace(points=[found])

        self.assertEqual(search("chi phí bao nhiêu", "chi_phi"), [found])

        self.assertEqual(mocked_client.return_value.query_points.call_count, 1)
        kwargs = mocked_client.return_value.query_points.call_args.kwargs
        self.assertIsNone(kwargs.get("query_filter"))

    @patch("app.rag.retriever.get_qdrant_client")
    @patch("app.rag.retriever.create_embedding", return_value=[0.1, 0.2])
    def test_wrong_intent_does_not_bury_the_right_chunk(self, _, mocked_client):
        """Ca thật: "Khi bắt đầu thì tiền cọc bao nhiêu?" bị phân loại nhầm.

        Đoạn chứa con số nằm ở chủ đề `chi_phi` và có điểm cao hơn. Dù ý định
        bị đoán thành `quy_trinh`, nó vẫn phải đứng đầu.
        """
        has_answer = self._hit(0.706, "chi_phi", "Quy trình đóng phí")
        off_topic = self._hit(0.679, "quy_trinh", "Cách đăng ký đơn hàng")
        mocked_client.return_value.query_points.return_value = SimpleNamespace(
            points=[has_answer, off_topic]
        )

        self.assertEqual(search("khi bắt đầu tiền cọc bao nhiêu", "quy_trinh")[0], has_answer)

    @patch("app.rag.retriever.get_qdrant_client")
    @patch("app.rag.retriever.create_embedding", return_value=[0.1, 0.2])
    def test_order_follows_similarity_not_topic(self, _, mocked_client):
        first = self._hit(0.80, "hoc_tap")
        second = self._hit(0.75, "chi_phi")
        mocked_client.return_value.query_points.return_value = SimpleNamespace(
            points=[first, second]
        )

        self.assertEqual(search("câu hỏi", "chi_phi"), [first, second])

    @patch("app.rag.retriever.get_qdrant_client")
    @patch("app.rag.retriever.create_embedding", return_value=[0.1, 0.2])
    def test_topic_is_backfilled_for_legacy_points(self, _, mocked_client):
        legacy = SimpleNamespace(
            score=0.8,
            payload={"section": "chi_phi", "title": "Chi phí đơn điều dưỡng"},
        )
        mocked_client.return_value.query_points.return_value = SimpleNamespace(points=[legacy])

        result = search("chi phí", "chi_phi")

        self.assertEqual(result[0].payload["topic"], "chi_phi")


if __name__ == "__main__":
    unittest.main()
