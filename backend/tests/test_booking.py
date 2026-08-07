import unittest
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from app.booking.booking_service import _today, process_booking_message
from app.conversation.session_manager import Session


def next_workday():
    value = _today() + timedelta(days=1)
    while value.weekday() == 6:
        value += timedelta(days=1)
    return value


class BookingFlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session = Session(session_id="booking-test")

    @patch(
        "app.booking.booking_service.save_booking_draft",
        new_callable=AsyncMock,
    )
    async def test_collects_required_fields_and_creates_appointment(
        self,
        _,
    ):
        workday = next_workday()
        messages = [
            "đặt lịch",
            "Nguyễn Văn Nam",
            "0912345678",
            workday.strftime("%d/%m/%Y"),
            "09:00",
        ]

        answers = []
        for message in messages:
            answer, created = await process_booking_message(
                self.session,
                message,
            )
            answers.append(answer)
            self.assertFalse(created)

        self.assertIn("họ và tên", answers[0])
        self.assertNotIn("chưa nhận ra", answers[0])
        self.assertEqual(self.session.booking_step, "confirm")
        self.assertIn("Nguyễn Văn Nam", answer)
        self.assertIn("0912345678", answer)

        with patch(
            "app.booking.booking_service.create_appointment",
            new_callable=AsyncMock,
        ) as mocked_create:
            answer, created = await process_booking_message(
                self.session,
                "có",
            )

        self.assertTrue(created)
        self.assertIn("Đặt lịch thành công", answer)
        appointment = mocked_create.await_args.args[0]
        self.assertEqual(appointment["customer_name"], "Nguyễn Văn Nam")
        self.assertEqual(appointment["phone"], "0912345678")
        self.assertEqual(appointment["appointment_time"], "09:00")

    @patch(
        "app.booking.booking_service.save_booking_draft",
        new_callable=AsyncMock,
    )
    async def test_rejects_sunday_and_outside_working_hours(self, _):
        sunday = _today() + timedelta(days=(6 - _today().weekday()) % 7)
        if sunday < _today():
            sunday += timedelta(days=7)

        self.session.booking_step = "date"
        self.session.booking_data = {
            "customer_name": "Nguyễn Văn Nam",
            "phone": "0912345678",
        }
        answer, _ = await process_booking_message(
            self.session,
            sunday.strftime("%d/%m/%Y"),
        )
        self.assertIn("Chủ Nhật", answer)

        self.session.booking_step = "time"
        self.session.booking_data["appointment_date"] = next_workday().isoformat()
        answer, _ = await process_booking_message(self.session, "12:30")
        self.assertIn("08:00–11:30", answer)


if __name__ == "__main__":
    unittest.main()
