"""Kiểm thử module sâu AuthManager: phát hành/giải mã token JWT và băm mật khẩu bcrypt."""

from datetime import timedelta
import pytest
from core_kit.auth import AuthManager
from core_kit.config.settings import BaseAppSettings


def test_auth_manager_issue_and_verify_token():
    auth = AuthManager(secret_key="my-super-secret-key-for-test-32b", default_expire_minutes=60)

    token = auth.issue_token(subject="user_123", claims={"role": "admin"})
    assert isinstance(token, str)
    assert len(token) > 20

    payload = auth.verify_token(token)
    assert payload is not None
    assert payload["sub"] == "user_123"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_auth_manager_verify_tampered_token_returns_none():
    auth = AuthManager(secret_key="key-one-with-at-least-32-bytes-long-secret!")
    other_auth = AuthManager(secret_key="key-two-with-at-least-32-bytes-long-secret!")

    token = auth.issue_token(subject="user_admin")
    # Token ký bởi key-one giải mã bằng key-two phải trả về None
    assert other_auth.verify_token(token) is None
    assert auth.verify_token("invalid.token.payload") is None


def test_auth_manager_expired_token():
    auth = AuthManager(secret_key="my-key-with-at-least-32-bytes-long-secret!", default_expire_minutes=-10)

    # Token hết hạn ngay khi tạo
    token = auth.issue_token(subject="expired_user", expires_delta=timedelta(seconds=-1))
    assert auth.verify_token(token) is None


def test_auth_manager_from_settings():
    class TestSettings(BaseAppSettings):
        secret_key: str = "custom-secret-from-settings-key-at-least-32bytes!"
        jwt_algorithm: str = "HS256"
        access_token_expire_minutes: int = 120

    settings = TestSettings()
    auth = AuthManager.from_settings(settings)

    token = auth.issue_token(subject="settings_user")
    payload = auth.verify_token(token)
    assert payload is not None
    assert payload["sub"] == "settings_user"


def test_auth_manager_password_hashing_and_verification():
    auth = AuthManager(secret_key="dummy-key")

    plain = "SuperPassword123!"
    hashed = auth.hash_password(plain)

    assert hashed != plain
    assert auth.verify_password(plain, hashed) is True
    assert auth.verify_password("WrongPassword", hashed) is False
