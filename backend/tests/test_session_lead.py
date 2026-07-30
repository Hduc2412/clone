import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.conversation.session_manager import MAX_HISTORY, Session
from app.db.database import close_db, get_db, init_db, save_lead
from app.lead.lead_service import try_capture_lead
from app.services.chat_service import process_message
from app.conversation.session_manager import session_manager


class SessionRestoreTests(unittest.TestCase):
    def test_restore_only_latest_messages(self):
        now = datetime.now(UTC)
        records = [
            {
                "role": "user" if index % 2 == 0 else "assistant",
                "content": f"message-{index}",
                "created_at": now + timedelta(seconds=index),
            }
            for index in range(MAX_HISTORY + 3)
        ]

        session = Session(session_id="restore-test")
        session.restore_history(records)

        self.assertTrue(session.restored_from_db)
        self.assertEqual(len(session.history), MAX_HISTORY)
        self.assertEqual(session.history[0].content, "message-3")
        self.assertEqual(session.history[-1].content, "message-12")


class LeadServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_does_not_capture_outside_lead_flow(self):
        with patch(
            "app.lead.lead_service.save_lead",
            new_callable=AsyncMock,
        ) as mocked_save:
            result = await try_capture_lead(
                "normal-chat",
                "Tôi tên là Nguyễn Văn An",
                "chung",
                awaiting_lead=False,
            )

        self.assertIsNone(result)
        mocked_save.assert_not_awaited()

    async def test_capture_while_session_is_awaiting_lead(self):
        saved = {
            "session_id": "lead-chat",
            "name": "Nguyễn Văn An",
            "phone": "0912345678",
        }
        with patch(
            "app.lead.lead_service.save_lead",
            new_callable=AsyncMock,
            return_value=saved,
        ) as mocked_save:
            result = await try_capture_lead(
                "lead-chat",
                "Số của tôi là 0912345678",
                "chung",
                awaiting_lead=True,
            )

        self.assertEqual(result, saved)
        mocked_save.assert_awaited_once()


class ChatServiceRestoreTests(unittest.IsolatedAsyncioTestCase):
    TEST_SESSION_ID = "__codex_test_restored_lead_flow__"

    async def asyncTearDown(self):
        session_manager.delete(self.TEST_SESSION_ID)

    async def test_restored_lead_flow_captures_phone_and_stops_waiting(self):
        stored_messages = [
            {
                "role": "assistant",
                "content": (
                    "Anh/chị vui lòng để lại tên và số điện thoại "
                    "để được tư vấn."
                ),
                "created_at": datetime.now(UTC),
            }
        ]
        saved_lead = {
            "session_id": self.TEST_SESSION_ID,
            "name": "Nguyễn Văn An",
            "phone": "0912345678",
        }

        with (
            patch(
                "app.services.chat_service.get_messages",
                new_callable=AsyncMock,
                return_value=stored_messages,
            ),
            patch("app.services.chat_service.search", return_value=[]),
            patch(
                "app.services.chat_service.try_capture_lead",
                new_callable=AsyncMock,
                return_value=saved_lead,
            ) as mocked_capture,
            patch(
                "app.services.chat_service._save_exchange",
                new_callable=AsyncMock,
            ),
        ):
            result = await process_message(
                "Số của tôi là 0912345678",
                self.TEST_SESSION_ID,
            )

        session = session_manager.get(self.TEST_SESSION_ID)
        self.assertIsNotNone(session)
        self.assertTrue(session.restored_from_db)
        self.assertFalse(session.awaiting_lead)
        self.assertIn("liên hệ lại", result["answer"])
        self.assertTrue(mocked_capture.await_args.kwargs["awaiting_lead"])


class LeadDatabaseIntegrationTests(unittest.IsolatedAsyncioTestCase):
    TEST_SESSION_ID = "__codex_test_lead_upsert__"

    async def asyncSetUp(self):
        await init_db()
        await get_db().leads.delete_many({"session_id": self.TEST_SESSION_ID})

    async def asyncTearDown(self):
        await get_db().leads.delete_many({"session_id": self.TEST_SESSION_ID})
        await close_db()

    async def test_name_and_phone_are_merged_into_one_lead(self):
        await save_lead(
            self.TEST_SESSION_ID,
            name="Nguyễn Văn An",
            note="name step",
        )
        result = await save_lead(
            self.TEST_SESSION_ID,
            phone="0912345678",
            note="phone step",
        )

        count = await get_db().leads.count_documents(
            {"session_id": self.TEST_SESSION_ID}
        )
        self.assertEqual(count, 1)
        self.assertEqual(result.get("name"), "Nguyễn Văn An")
        self.assertEqual(result.get("phone"), "0912345678")


if __name__ == "__main__":
    unittest.main()
