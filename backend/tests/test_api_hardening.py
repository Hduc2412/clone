import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from pydantic import ValidationError

from app.api.appointments import AppointmentStatusRequest
from app.api.chat import ChatRequest
from app.conversation.session_manager import session_manager
from app.core.rate_limit import InMemoryRateLimiter
from app.services.chat_service import process_message


class ChatRequestValidationTests(unittest.TestCase):
    def test_message_is_trimmed_and_session_is_uuid(self):
        session_id = uuid.uuid4()
        request = ChatRequest(message="  Xin chào  ", session_id=str(session_id))
        self.assertEqual(request.message, "Xin chào")
        self.assertEqual(request.session_id, session_id)

    def test_blank_long_and_invalid_session_are_rejected(self):
        invalid_payloads = [
            {"message": "   "},
            {"message": "x" * 2001},
            {"message": "Xin chào", "session_id": "not-a-uuid"},
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                ChatRequest(**payload)

    def test_employee_name_is_not_accepted_as_appointment_input(self):
        with self.assertRaises(ValidationError):
            AppointmentStatusRequest(
                status="confirmed",
                employee_name="Người giả mạo",
            )


class RateLimiterTests(unittest.TestCase):
    def test_sliding_window_and_reset(self):
        limiter = InMemoryRateLimiter()
        limiter.check("test", limit=2, window_seconds=60, now=0)
        limiter.check("test", limit=2, window_seconds=60, now=1)
        with self.assertRaises(HTTPException) as context:
            limiter.check("test", limit=2, window_seconds=60, now=2)
        self.assertEqual(context.exception.status_code, 429)
        self.assertEqual(context.exception.headers["Retry-After"], "58")

        limiter.reset("test")
        limiter.check("test", limit=2, window_seconds=60, now=2)


class ThreadpoolTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_and_generation_run_in_threadpool(self):
        session_id = str(uuid.uuid4())
        hit = SimpleNamespace(
            score=0.91,
            payload={"url": "https://example.com", "title": "Điều kiện"},
        )

        async def run_sync(function, *args):
            return function(*args)

        try:
            with (
                patch("app.services.chat_service.get_messages", new_callable=AsyncMock, return_value=[]),
                patch("app.services.chat_service.get_booking_draft", new_callable=AsyncMock, return_value=None),
                patch("app.services.chat_service.save_message", new_callable=AsyncMock),
                patch("app.services.chat_service.resolve", return_value="query"),
                patch("app.services.chat_service.classify", return_value="dieu_kien"),
                patch("app.services.chat_service.search", return_value=[hit]) as search_mock,
                patch("app.services.chat_service.generate_response", return_value="Câu trả lời") as generate_mock,
                patch("app.services.chat_service.validate", return_value=(True, "Câu trả lời")),
                patch("app.services.chat_service.run_in_threadpool", new=AsyncMock(side_effect=run_sync)) as pool_mock,
            ):
                result = await process_message("Điều kiện là gì?", session_id)

            self.assertEqual(result["answer"], "Câu trả lời")
            self.assertEqual(pool_mock.await_count, 2)
            search_mock.assert_called_once_with("query", "dieu_kien")
            generate_mock.assert_called_once()
        finally:
            session_manager.delete(session_id)


if __name__ == "__main__":
    unittest.main()
