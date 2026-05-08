"""Tests for password hashing service."""

import pytest

from services.password import hash_password, verify_password


class TestPasswordHashing:
    """Test Argon2id password hashing."""

    def test_hash_password_returns_string(self):
        hashed = hash_password("mysecret123")
        assert isinstance(hashed, str)
        assert len(hashed) > 20

    def test_hash_password_different_each_time(self):
        h1 = hash_password("mysecret123")
        h2 = hash_password("mysecret123")
        # Argon2id includes random salt, so hashes differ
        assert h1 != h2

    def test_verify_correct_password(self):
        hashed = hash_password("mysecret123")
        assert verify_password("mysecret123", hashed) is True

    def test_verify_incorrect_password(self):
        hashed = hash_password("mysecret123")
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False

    def test_verify_unicode_password(self):
        password = "пароль123🔐"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_long_password(self):
        password = "a" * 1000
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_different_hash_format_fails_gracefully(self):
        # Should not crash on garbage hash — pwdlib raises UnknownHashError
        from pwdlib.exceptions import UnknownHashError
        try:
            verify_password("password", "not-a-valid-hash")
            assert False, "Expected UnknownHashError"
        except UnknownHashError:
            assert True

    def test_hash_and_verify_roundtrip_various_passwords(self):
        passwords = [
            "short",
            "A" * 100,
            "Mix3d!@#Chars",
            "password with spaces",
            "1234567890",
        ]
        for pwd in passwords:
            hashed = hash_password(pwd)
            assert verify_password(pwd, hashed) is True
