import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("JWT_SECRET", "test-secret-that-is-long-enough-for-audit-tests")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.audit import router as audit_router
from app.auth.security import create_access_token
from app.core.config import settings
from app.db.database import _sanitize_audit_details, list_audit_logs, record_audit_log
from app.services.audit_service import audit_action


class AuditSanitizationTests(unittest.TestCase):
    def test_sensitive_values_are_redacted_recursively(self):
        details = {
            "email": "admin@example.com",
            "password": "secret",
            "nested": {"token": "jwt", "status": "active"},
            "items": [{"authorization": "Bearer secret"}],
        }
        sanitized = _sanitize_audit_details(details)
        self.assertEqual(sanitized["email"], "admin@example.com")
        self.assertEqual(sanitized["password"], "[REDACTED]")
        self.assertEqual(sanitized["nested"]["token"], "[REDACTED]")
        self.assertEqual(sanitized["nested"]["status"], "active")
        self.assertEqual(sanitized["items"][0]["authorization"], "[REDACTED]")


class AuditPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_audit_failure_does_not_break_business_flow(self):
        request = MagicMock()
        request.client.host = "127.0.0.1"
        with patch(
            "app.services.audit_service.record_audit_log",
            new=AsyncMock(side_effect=RuntimeError("database unavailable")),
        ):
            await audit_action(request, "lead.updated", actor_email="admin@example.com")

    async def test_record_audit_log_never_persists_secret(self):
        database = MagicMock()
        database.audit_logs.insert_one = AsyncMock()
        with patch("app.db.database.get_db", return_value=database):
            await record_audit_log(
                action="staff_user.created",
                outcome="success",
                actor_email="admin@example.com",
                details={"role": "manager", "password": "NeverStoreThis"},
            )
        document = database.audit_logs.insert_one.await_args.args[0]
        self.assertEqual(document["details"]["role"], "manager")
        self.assertEqual(document["details"]["password"], "[REDACTED]")
        self.assertNotIn("NeverStoreThis", str(document))

    async def test_list_audit_logs_builds_filters_and_limit(self):
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.to_list = AsyncMock(return_value=[{"action": "auth.login"}])
        database = MagicMock()
        database.audit_logs.find.return_value = cursor
        with patch("app.db.database.get_db", return_value=database):
            result = await list_audit_logs(
                actor_email=" ADMIN@EXAMPLE.COM ",
                action="auth.login",
                outcome="success",
                limit=25,
            )
        query = database.audit_logs.find.call_args.args[0]
        self.assertEqual(query["actor_email"], "admin@example.com")
        self.assertEqual(query["action"], "auth.login")
        self.assertEqual(query["outcome"], "success")
        cursor.limit.assert_called_once_with(25)
        self.assertEqual(result, [{"action": "auth.login"}])


class AuditAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.original_secret = settings.jwt_secret
        settings.jwt_secret = "test-secret-that-is-long-enough-for-audit-tests"
        app = FastAPI()
        app.include_router(audit_router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        settings.jwt_secret = self.original_secret

    def _token(self, role: str) -> str:
        return create_access_token(
            {"email": f"{role}@example.com", "full_name": role.title(), "role": role}
        )

    def test_consultant_cannot_read_audit_logs(self):
        user = {
            "email": "consultant@example.com",
            "full_name": "Consultant",
            "role": "consultant",
            "status": "active",
        }
        with patch(
            "app.auth.security.get_staff_user_by_email", new=AsyncMock(return_value=user)
        ):
            response = self.client.get(
                "/audit-logs",
                cookies={settings.auth_cookie_name: self._token("consultant")},
            )
        self.assertEqual(response.status_code, 403)

    def test_manager_can_filter_audit_logs(self):
        user = {
            "email": "manager@example.com",
            "full_name": "Manager",
            "role": "manager",
            "status": "active",
        }
        with (
            patch("app.auth.security.get_staff_user_by_email", new=AsyncMock(return_value=user)),
            patch("app.api.audit.list_audit_logs", new=AsyncMock(return_value=[])) as listing,
        ):
            response = self.client.get(
                "/audit-logs?action=auth.login&outcome=success&limit=25",
                cookies={settings.auth_cookie_name: self._token("manager")},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        self.assertEqual(listing.await_args.kwargs["action"], "auth.login")
        self.assertEqual(listing.await_args.kwargs["outcome"], "success")
        self.assertEqual(listing.await_args.kwargs["limit"], 25)


if __name__ == "__main__":
    unittest.main()
