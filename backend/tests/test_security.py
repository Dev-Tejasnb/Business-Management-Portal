"""Tests for password hashing and policy."""

from __future__ import annotations

import pytest

from app.core.security import (
    PasswordPolicyError,
    hash_password,
    validate_password_policy,
    verify_password,
)


def test_password_is_hashed_not_plaintext() -> None:
    hashed = hash_password("Password123!")
    assert "Password123!" not in hashed
    assert hashed.startswith("$argon2")


def test_password_verification_succeeds() -> None:
    hashed = hash_password("Password123!")
    assert verify_password("Password123!", hashed) is True


def test_password_verification_fails_on_wrong_password() -> None:
    hashed = hash_password("Password123!")
    assert verify_password("WrongPassword1", hashed) is False


def test_each_hash_is_salted() -> None:
    assert hash_password("Password123!") != hash_password("Password123!")


@pytest.mark.parametrize(
    "password",
    ["short1", "nouppercase1", "NOLOWERCASE1", "NoDigitsHere", ""],
)
def test_password_policy_rejects_weak_passwords(password: str) -> None:
    with pytest.raises(PasswordPolicyError):
        hash_password(password)


def test_password_policy_accepts_strong_password() -> None:
    validate_password_policy("Str0ngPass!")


def test_verify_password_is_safe_on_malformed_hash() -> None:
    assert verify_password("Password123!", "not-a-valid-hash") is False