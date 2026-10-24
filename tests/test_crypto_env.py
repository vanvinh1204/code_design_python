"""Kiểm thử tính năng mã hóa, giải mã cấu hình .env và tích hợp vào BaseAppSettings của core_kit."""

import os
import pytest
from cryptography.fernet import Fernet
from core_kit.utils.crypto import (
    PREFIX,
    CIPHER_KEY_ENV_VAR,
    DEFAULT_CIPHER_KEY,
    encrypt_val,
    decrypt_val,
    get_cipher_key,
)
from core_kit.config.settings import BaseAppSettings
from core_kit.tools.encrypt_env import main as cli_main


def test_encrypt_decrypt_default_key():
    plain = "SuperSecretPassword123!@#"
    encrypted = encrypt_val(plain)

    assert encrypted.startswith(PREFIX)
    assert encrypted != plain

    decrypted = decrypt_val(encrypted)
    assert decrypted == plain


def test_decrypt_unencrypted_raw_text():
    raw_plain = "PlainTextPassword"
    # Chuỗi không có tiền tố enc: thì giữ nguyên
    assert decrypt_val(raw_plain) == raw_plain
    assert decrypt_val("") == ""
    assert decrypt_val(None) == ""


def test_custom_key_encryption_and_decryption():
    custom_key = Fernet.generate_key()
    plain = "CustomKeySecretData"

    encrypted = encrypt_val(plain, key=custom_key)
    assert encrypted.startswith(PREFIX)

    decrypted = decrypt_val(encrypted, key=custom_key)
    assert decrypted == plain

    # Thử giải mã bằng khóa mặc định (sai khóa) phải văng ValueError
    with pytest.raises(ValueError, match="Không thể giải mã dữ liệu"):
        decrypt_val(encrypted, key=DEFAULT_CIPHER_KEY)


def test_env_var_key_override(monkeypatch):
    custom_key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv(CIPHER_KEY_ENV_VAR, custom_key)

    assert get_cipher_key() == custom_key.encode("ascii")

    plain = "SecretUnderEnvKey"
    encrypted = encrypt_val(plain)
    decrypted = decrypt_val(encrypted)
    assert decrypted == plain


def test_base_app_settings_auto_decrypt(monkeypatch):
    secret_db_pass = "MySecretPass_XYZ"
    encrypted_pass = encrypt_val(secret_db_pass)

    class CustomSettings(BaseAppSettings):
        db_password: str = "default_pass"
        api_token: str = "default_token"

    # Giả lập biến môi trường nạp từ .env
    monkeypatch.setenv("DATABASE_URL", f"postgresql://admin:{encrypted_pass}@localhost:5432/db")
    monkeypatch.setenv("DB_PASSWORD", encrypted_pass)
    monkeypatch.setenv("API_TOKEN", "plain_unencrypted_token")

    settings = CustomSettings()

    # Kiểm tra tự động giải mã
    assert settings.db_password == secret_db_pass
    assert settings.database_url == f"postgresql://admin:{secret_db_pass}@localhost:5432/db"
    # Chuỗi không mã hóa vẫn giữ nguyên
    assert settings.api_token == "plain_unencrypted_token"


def test_cli_encrypt_env(capsys):
    test_secret = "CLI_Admin_Pass_456"
    exit_code = cli_main([test_secret])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "[THÀNH CÔNG]" in captured.out
    assert "enc:" in captured.out
    assert "DB_PASSWORD=enc:" in captured.out


def test_cli_encrypt_env_custom_key(capsys):
    custom_key = Fernet.generate_key().decode("ascii")
    test_secret = "CustomSecretCLI"
    exit_code = cli_main([test_secret, "--key", custom_key])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "[THÀNH CÔNG]" in captured.out
    assert custom_key in captured.out
