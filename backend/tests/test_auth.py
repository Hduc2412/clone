import os
import unittest

os.environ.setdefault("JWT_SECRET", "test-secret-that-is-long-enough-for-auth-tests")

from fastapi import FastAPI, HTTPException
from fastapi import Request, Response
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.api.auth import LoginRequest, login, logout, router as auth_router
from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.core.rate_limit import rate_limiter


TEST_JWT_SECRET = "test-secret-that-is-long-enough-for-auth-tests"


class PasswordSecurityTests(unittest.TestCase):
    def test_password_is_hashed_and_verified(self):
        encoded = hash_password("MatKhauAnToan123")
        self.assertNotIn("MatKhauAnToan123", encoded)
        self.assertTrue(verify_password("MatKhauAnToan123", encoded))
        self.assertFalse(verify_password("SaiMatKhau", encoded))


class TokenSecurityTests(unittest.TestCase):
    def setUp(self):
        self.original_secret = settings.jwt_secret
        settings.jwt_secret = TEST_JWT_SECRET

    def tearDown(self):
        settings.jwt_secret = self.original_secret

    def test_access_token_contains_expected_identity(self):
        token = create_access_token(
            {"email": "admin@example.com", "full_name": "Admin", "role": "admin"}
        )
        payload = decode_access_token(token)
        self.assertEqual(payload["sub"], "admin@example.com")
        self.assertEqual(payload["role"], "admin")

    def test_tampered_token_is_rejected(self):
        token = create_access_token(
            {"email": "admin@example.com", "full_name": "Admin", "role": "admin"}
        )
        with self.assertRaises(HTTPException):
            decode_access_token(token[:-1] + ("a" if token[-1] != "a" else "b"))


class CookieAuthenticationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original_secret = settings.jwt_secret
        settings.jwt_secret = TEST_JWT_SECRET

    def tearDown(self):
        settings.jwt_secret = self.original_secret

    async def test_login_sets_httponly_cookie_without_returning_token(self):
        request = Request({"type": "http", "client": ("127.0.0.77", 12345)})
        response = Response()
        user = {
            "email": "admin@example.com",
            "full_name": "Admin",
            "role": "admin",
            "status": "active",
            "password_hash": "stored-hash",
        }
        with (
            patch("app.api.auth.get_staff_user_by_email", new=AsyncMock(return_value=user)),
            patch("app.api.auth.record_staff_login", new=AsyncMock()),
            patch("app.api.auth.record_audit_log", new=AsyncMock()),
            patch("app.api.auth.verify_password", return_value=True),
        ):
            payload = await login(
                LoginRequest(email=user["email"], password="Password123"),
                request,
                response,
            )

        cookie = response.headers["set-cookie"]
        self.assertIn(f"{settings.auth_cookie_name}=", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=lax", cookie)
        self.assertNotIn("access_token", payload)

    async def test_logout_expires_auth_cookie(self):
        request = Request({"type": "http", "client": ("127.0.0.77", 12345)})
        response = Response()
        user = {"email": "admin@example.com", "full_name": "Admin", "role": "admin"}
        with patch("app.api.auth.record_audit_log", new=AsyncMock()):
            await logout(request, response, user)
        cookie = response.headers["set-cookie"]
        self.assertIn(f"{settings.auth_cookie_name}=", cookie)
        self.assertIn("Max-Age=0", cookie)


class LoginRateLimitIntegrationTests(unittest.TestCase):
    EMAIL = "rate-limit-integration@example.com"
    CORRECT_PASSWORD = "CorrectPassword123"

    def setUp(self):
        self.original_secret = settings.jwt_secret
        settings.jwt_secret = TEST_JWT_SECRET
        app = FastAPI()
        app.include_router(auth_router)
        self.client = TestClient(app)
        self.user = {
            "email": self.EMAIL,
            "full_name": "Rate Limit Test",
            "role": "admin",
            "status": "active",
            "password_hash": "stored-hash",
        }
        self._reset_limits()

    def tearDown(self):
        self.client.close()
        self._reset_limits()
        settings.jwt_secret = self.original_secret

    def _reset_limits(self):
        rate_limiter.reset(f"login:testclient:{self.EMAIL}")
        rate_limiter.reset("login-ip:testclient")

    def _post_login(self, password: str):
        return self.client.post(
            "/auth/login",
            json={"email": self.EMAIL, "password": password},
        )

    def _auth_patches(self):
        return (
            patch(
                "app.api.auth.get_staff_user_by_email",
                new=AsyncMock(return_value=self.user),
            ),
            patch("app.api.auth.record_staff_login", new=AsyncMock()),
            patch("app.api.auth.record_audit_log", new=AsyncMock()),
            patch(
                "app.api.auth.verify_password",
                side_effect=lambda password, _: password == self.CORRECT_PASSWORD,
            ),
        )

    def test_returns_429_after_five_failed_logins(self):
        lookup, record, audit, verify = self._auth_patches()
        with lookup, record, audit, verify:
            statuses = [self._post_login("WrongPassword123").status_code for _ in range(6)]

        self.assertEqual(statuses[:5], [401] * 5)
        self.assertEqual(statuses[5], 429)

    def test_successful_login_resets_email_counter(self):
        lookup, record, audit, verify = self._auth_patches()
        with lookup, record, audit, verify:
            before_success = [
                self._post_login("WrongPassword123").status_code for _ in range(4)
            ]
            success = self._post_login(self.CORRECT_PASSWORD)
            after_success = [
                self._post_login("WrongPassword123").status_code for _ in range(6)
            ]

        self.assertEqual(before_success, [401] * 4)
        self.assertEqual(success.status_code, 200)
        self.assertEqual(after_success[:5], [401] * 5)
        self.assertEqual(after_success[5], 429)


if __name__ == "__main__":
    unittest.main()
