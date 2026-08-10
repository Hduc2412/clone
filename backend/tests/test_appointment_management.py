import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.db.database import (
    assign_appointment,
    find_appointment_conflict,
    list_appointments,
    reschedule_appointment,
    update_appointment_status,
)


def make_cursor(rows):
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=rows)
    return cursor


class AppointmentManagementTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_appointments_combines_all_filters(self):
        db = MagicMock()
        cursor = make_cursor([{"appointment_code": "LH-001"}])
        db.consultation_appointments.find.return_value = cursor

        with patch("app.db.database.get_db", return_value=db):
            rows = await list_appointments(
                status="confirmed",
                date_from="2026-08-10",
                date_to="2026-08-20",
                assigned_to=" Consultant@Example.com ",
                limit=25,
            )

        self.assertEqual(rows, [{"appointment_code": "LH-001"}])
        db.consultation_appointments.find.assert_called_once_with(
            {
                "status": "confirmed",
                "assigned_to": "consultant@example.com",
                "appointment_date": {"$gte": "2026-08-10", "$lte": "2026-08-20"},
            },
            {"_id": 0, "booking_key": 0},
        )
        cursor.limit.assert_called_once_with(25)
        cursor.to_list.assert_awaited_once_with(length=25)

    async def test_status_change_uses_authenticated_actor_and_records_event(self):
        db = MagicMock()
        previous = {"appointment_code": "LH-001", "status": "pending"}
        updated = {"appointment_code": "LH-001", "status": "confirmed"}
        db.consultation_appointments.find_one_and_update = AsyncMock(return_value=previous)
        db.consultation_appointments.find_one = AsyncMock(return_value=updated)
        db.appointment_events.insert_one = AsyncMock()
        actor = {"full_name": "Quản lý A", "email": "manager@example.com"}

        with patch("app.db.database.get_db", return_value=db):
            result = await update_appointment_status(
                "LH-001", "confirmed", actor, "Đã gọi xác nhận"
            )

        self.assertEqual(result, updated)
        event = db.appointment_events.insert_one.await_args.args[0]
        self.assertEqual(event["action"], "status_changed")
        self.assertEqual(event["actor_email"], "manager@example.com")
        self.assertEqual(event["old_status"], "pending")
        self.assertEqual(event["new_status"], "confirmed")
        self.assertEqual(event["note"], "Đã gọi xác nhận")

    async def test_assignment_records_previous_and_new_assignee(self):
        db = MagicMock()
        previous = {
            "appointment_code": "LH-001",
            "status": "confirmed",
            "assigned_to": "old@example.com",
        }
        updated = {
            "appointment_code": "LH-001",
            "status": "confirmed",
            "assigned_to": "new@example.com",
        }
        db.consultation_appointments.find_one_and_update = AsyncMock(return_value=previous)
        db.consultation_appointments.find_one = AsyncMock(return_value=updated)
        db.appointment_events.insert_one = AsyncMock()
        actor = {"full_name": "Admin", "email": "admin@example.com"}
        assignee = {"full_name": "Tư vấn viên", "email": "new@example.com"}

        with patch("app.db.database.get_db", return_value=db):
            result = await assign_appointment("LH-001", assignee, actor)

        self.assertEqual(result, updated)
        event = db.appointment_events.insert_one.await_args.args[0]
        self.assertEqual(event["action"], "assigned")
        self.assertEqual(event["actor_email"], "admin@example.com")
        self.assertEqual(event["details"]["previous_assigned_to"], "old@example.com")
        self.assertEqual(event["details"]["assigned_to"], "new@example.com")

    async def test_conflict_checks_customer_and_assigned_employee(self):
        db = MagicMock()
        target = {
            "appointment_code": "LH-001",
            "phone": "0912345678",
            "assigned_to": "consultant@example.com",
        }
        conflict = {"appointment_code": "LH-002"}
        db.consultation_appointments.find_one = AsyncMock(
            side_effect=[target, conflict]
        )

        with patch("app.db.database.get_db", return_value=db):
            result = await find_appointment_conflict(
                "LH-001", "2026-08-12", "09:00"
            )

        self.assertEqual(result, conflict)
        conflict_query = db.consultation_appointments.find_one.await_args_list[1].args[0]
        self.assertEqual(
            conflict_query["$or"],
            [
                {"phone": "0912345678"},
                {"assigned_to": "consultant@example.com"},
            ],
        )

    async def test_reschedule_preserves_phone_booking_key_and_records_times(self):
        db = MagicMock()
        previous = {
            "appointment_code": "LH-001",
            "phone": "0912345678",
            "status": "confirmed",
            "appointment_date": "2026-08-11",
            "appointment_time": "09:00",
        }
        updated = {
            **previous,
            "appointment_date": "2026-08-12",
            "appointment_time": "14:00",
        }
        db.consultation_appointments.find_one = AsyncMock(
            side_effect=[{"phone": "0912345678"}, updated]
        )
        db.consultation_appointments.find_one_and_update = AsyncMock(
            return_value=previous
        )
        db.appointment_events.insert_one = AsyncMock()
        actor = {"full_name": "Tư vấn viên", "email": "staff@example.com"}

        with patch("app.db.database.get_db", return_value=db):
            result = await reschedule_appointment(
                "LH-001", "2026-08-12", "14:00", actor, "Khách yêu cầu đổi"
            )

        self.assertEqual(result, updated)
        update = db.consultation_appointments.find_one_and_update.await_args.args[1]
        self.assertEqual(
            update["$set"]["booking_key"],
            "0912345678|2026-08-12|14:00",
        )
        event = db.appointment_events.insert_one.await_args.args[0]
        self.assertEqual(event["action"], "rescheduled")
        self.assertEqual(event["details"]["previous_time"], "09:00")
        self.assertEqual(event["details"]["appointment_time"], "14:00")


if __name__ == "__main__":
    unittest.main()
