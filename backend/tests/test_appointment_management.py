import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.api.appointments import (
    get_appointments,
    get_appointments_stats,
    require_appointment_access,
)
from app.db.database import (
    assign_appointment,
    find_appointment_conflict,
    get_appointment_stats,
    list_appointments,
    list_notifications,
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
                "LH-001",
                "confirmed",
                actor,
                "Đã gọi xác nhận",
                required_assigned_to="manager@example.com",
            )

        self.assertEqual(result, updated)
        event = db.appointment_events.insert_one.await_args.args[0]
        self.assertEqual(event["action"], "status_changed")
        self.assertEqual(event["actor_email"], "manager@example.com")
        self.assertEqual(event["old_status"], "pending")
        self.assertEqual(event["new_status"], "confirmed")
        self.assertEqual(event["note"], "Đã gọi xác nhận")
        update_query = db.consultation_appointments.find_one_and_update.await_args.args[0]
        self.assertEqual(update_query["assigned_to"], "manager@example.com")

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

    async def test_notifications_are_limited_to_assigned_appointments(self):
        db = MagicMock()
        appointment_cursor = MagicMock()
        appointment_cursor.to_list = AsyncMock(
            return_value=[{"appointment_code": "LH-001"}]
        )
        db.consultation_appointments.find.return_value = appointment_cursor
        notification_cursor = make_cursor([{"appointment_code": "LH-001"}])
        db.notifications.find.return_value = notification_cursor

        with patch("app.db.database.get_db", return_value=db):
            rows = await list_notifications(
                unread_only=True,
                assigned_to="consultant@example.com",
                limit=20,
            )

        self.assertEqual(rows, [{"appointment_code": "LH-001"}])
        db.notifications.find.assert_called_once_with(
            {
                "is_read": False,
                "appointment_code": {"$in": ["LH-001"]},
            },
            {"_id": 0},
        )

    async def test_appointment_stats_calculate_status_rates(self):
        db = MagicMock()
        aggregate_cursor = MagicMock()
        aggregate_cursor.to_list = AsyncMock(
            return_value=[
                {"_id": "pending", "count": 2},
                {"_id": "confirmed", "count": 3},
                {"_id": "completed", "count": 4},
                {"_id": "unreachable", "count": 1},
            ]
        )
        db.consultation_appointments.aggregate.return_value = aggregate_cursor
        db.consultation_appointments.count_documents = AsyncMock(return_value=8)

        with patch("app.db.database.get_db", return_value=db):
            stats = await get_appointment_stats(
                date_from="2026-08-01",
                date_to="2026-08-31",
                assigned_to="consultant@example.com",
            )

        self.assertEqual(stats["total"], 10)
        self.assertEqual(stats["confirmation_rate"], 80.0)
        self.assertEqual(stats["completion_rate"], 40.0)
        self.assertEqual(stats["unreachable_rate"], 10.0)
        self.assertEqual(stats["cancellation_rate"], 0.0)
        match_query = db.consultation_appointments.aggregate.call_args.args[0][0]["$match"]
        self.assertEqual(match_query["assigned_to"], "consultant@example.com")


class AppointmentAuthorizationTests(unittest.IsolatedAsyncioTestCase):
    async def test_consultant_list_is_forced_to_their_email(self):
        consultant = {
            "role": "consultant",
            "email": "consultant@example.com",
        }
        with patch(
            "app.api.appointments.list_appointments",
            new=AsyncMock(return_value=[]),
        ) as mocked_list:
            await get_appointments(
                status=None,
                date_from=None,
                date_to=None,
                assigned_to="other@example.com",
                limit=50,
                current_user=consultant,
            )

        self.assertEqual(
            mocked_list.await_args.kwargs["assigned_to"],
            "consultant@example.com",
        )

    async def test_consultant_stats_are_forced_to_their_email(self):
        consultant = {
            "role": "consultant",
            "email": "consultant@example.com",
        }
        with patch(
            "app.api.appointments.get_appointment_stats",
            new=AsyncMock(return_value={}),
        ) as mocked_stats:
            await get_appointments_stats(
                date_from=None,
                date_to=None,
                assigned_to="other@example.com",
                current_user=consultant,
            )

        self.assertEqual(
            mocked_stats.await_args.kwargs["assigned_to"],
            "consultant@example.com",
        )

    async def test_consultant_cannot_access_unassigned_or_other_staff_schedule(self):
        consultant = {
            "role": "consultant",
            "email": "consultant@example.com",
        }
        forbidden_appointments = [
            {"appointment_code": "LH-001", "assigned_to": None},
            {"appointment_code": "LH-002", "assigned_to": "other@example.com"},
        ]
        for appointment in forbidden_appointments:
            with (
                self.subTest(appointment=appointment),
                patch(
                    "app.api.appointments.get_appointment_by_code",
                    new=AsyncMock(return_value=appointment),
                ),
                self.assertRaises(HTTPException) as context,
            ):
                await require_appointment_access(
                    appointment["appointment_code"],
                    consultant,
                )
            self.assertEqual(context.exception.status_code, 403)

    async def test_consultant_can_access_their_assigned_schedule(self):
        appointment = {
            "appointment_code": "LH-001",
            "assigned_to": "consultant@example.com",
        }
        consultant = {
            "role": "consultant",
            "email": "consultant@example.com",
        }
        with patch(
            "app.api.appointments.get_appointment_by_code",
            new=AsyncMock(return_value=appointment),
        ):
            result = await require_appointment_access("LH-001", consultant)

        self.assertEqual(result, appointment)


if __name__ == "__main__":
    unittest.main()
