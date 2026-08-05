import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.conversation.session_manager import MAX_HISTORY, Session, session_manager
from app.db.database import close_db, get_db, init_db, save_lead
from app.services.chat_service import process_message


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


class ChatServiceRestoreTests(unittest.IsolatedAsyncioTestCase):
    TEST_SESSION_ID = "__codex_test_restored_booking_flow__"

    async def asyncTearDown(self):
        session_manager.delete(self.TEST_SESSION_ID)

    async def test_restored_booking_flow_continues_from_saved_step(self):
        with (
            patch(
                "app.services.chat_service.get_messages",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.chat_service.get_booking_draft",
                new_callable=AsyncMock,
                return_value={
                    "booking_step": "phone",
                    "booking_data": {"customer_name": "Nguyễn Văn An"},
                },
            ),
            patch(
                "app.services.chat_service.process_booking_message",
                new_callable=AsyncMock,
                return_value=("Bạn vui lòng chọn ngày.", False),
            ) as mocked_booking,
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
        self.assertEqual(session.booking_step, "phone")
        self.assertEqual(result["intent"], "booking")
        mocked_booking.assert_awaited_once()


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
