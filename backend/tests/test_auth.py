import os
import unittest

os.environ.setdefault("JWT_SECRET", "test-secret-that-is-long-enough-for-auth-tests")

from fastapi import HTTPException
from fastapi import Request, Response
from unittest.mock import AsyncMock, patch

from app.api.auth import LoginRequest, login, logout
from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.core.config import settings


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
        response = Response()
        await logout(response)
        cookie = response.headers["set-cookie"]
        self.assertIn(f"{settings.auth_cookie_name}=", cookie)
        self.assertIn("Max-Age=0", cookie)


if __name__ == "__main__":
    unittest.main()
