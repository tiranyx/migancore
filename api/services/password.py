"""
Password hashing and verification using Argon2id (OWASP 2024 recommendation).
Replaces bcrypt with pwdlib + Argon2id.
"""

from pwdlib import PasswordHash

# Argon2id with recommended parameters
password_hash = PasswordHash.recommended()


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    return password_hash.verify(plain_password, hashed_password)
