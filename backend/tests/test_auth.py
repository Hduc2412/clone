import os
import unittest

os.environ.setdefault("JWT_SECRET", "test-secret-that-is-long-enough-for-auth-tests")

from fastapi import HTTPException

from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class PasswordSecurityTests(unittest.TestCase):
    def test_password_is_hashed_and_verified(self):
        encoded = hash_password("MatKhauAnToan123")
        self.assertNotIn("MatKhauAnToan123", encoded)
        self.assertTrue(verify_password("MatKhauAnToan123", encoded))
        self.assertFalse(verify_password("SaiMatKhau", encoded))


class TokenSecurityTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
