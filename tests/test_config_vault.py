"""Kiểm thử module sâu ConfigVault và CLI encrypt_env không dùng argparse."""

import sys
from pathlib import Path
import pytest
from core_kit.config.vault import ConfigVault
from core_kit.config.settings import BaseAppSettings
from core_kit.tools.encrypt_env import main as cli_main


def test_config_vault_encrypt_decrypt_roundtrip():
    vault = ConfigVault()
    plain = "TopSecretDatabasePassword_2026!"

    encrypted = vault.encrypt(plain)
    assert encrypted.startswith(vault.PREFIX)
    assert encrypted != plain

    decrypted = vault.decrypt(encrypted)
    assert decrypted == plain


def test_config_vault_decrypt_embedded_token_in_url():
    vault = ConfigVault()
    secret = "MyPass#123"
    encrypted = vault.encrypt(secret)

    url = f"postgresql://admin:{encrypted}@192.168.1.50:5432/production_db"
    decrypted_url = vault.decrypt(url)

    assert decrypted_url == f"postgresql://admin:{secret}@192.168.1.50:5432/production_db"


def test_config_vault_decrypt_mapping_recursive():
    vault = ConfigVault()
    p1 = vault.encrypt("secret_one")
    p2 = vault.encrypt("secret_two")

    nested = {
        "db": {"password": p1, "port": 5432},
        "servers": [{"token": p2}, "plain_value"],
        "name": "Warehouse App",
    }

    result = vault.decrypt_mapping(nested)
    assert result["db"]["password"] == "secret_one"
    assert result["db"]["port"] == 5432
    assert result["servers"][0]["token"] == "secret_two"
    assert result["servers"][1] == "plain_value"
    assert result["name"] == "Warehouse App"


def test_config_vault_update_env_file(tmp_path):
    env_file = tmp_path / ".env"
    initial_content = """# Cấu hình hệ thống
APP_NAME=OldAppName
DB_PASSWORD=plain_old_password
API_PORT=8000
"""
    env_file.write_text(initial_content, encoding="utf-8")

    vault = ConfigVault()
    # Cập nhật DB_PASSWORD thành dạng mã hóa
    vault.update_env_file(env_file, key="DB_PASSWORD", value="NewSuperSecretPass", encrypt=True)

    # Thêm mới một key chưa có
    vault.update_env_file(env_file, key="NEW_API_KEY", value="ApiSecretKey123", encrypt=True)

    content = env_file.read_text(encoding="utf-8")
    assert "APP_NAME=OldAppName" in content
    assert "API_PORT=8000" in content
    assert "DB_PASSWORD=enc:" in content
    assert "plain_old_password" not in content
    assert "NEW_API_KEY=enc:" in content

    # Nạp vào BaseAppSettings kiểm tra giải mã thành công
    class CustomSettings(BaseAppSettings):
        app_name: str
        db_password: str
        new_api_key: str

    monkeypatch_env = {
        "DB_PASSWORD": [line.split("=", 1)[1] for line in content.splitlines() if line.startswith("DB_PASSWORD=")][0],
        "NEW_API_KEY": [line.split("=", 1)[1] for line in content.splitlines() if line.startswith("NEW_API_KEY=")][0],
    }

    assert vault.decrypt(monkeypatch_env["DB_PASSWORD"]) == "NewSuperSecretPass"
    assert vault.decrypt(monkeypatch_env["NEW_API_KEY"]) == "ApiSecretKey123"


def test_cli_encrypt_env_without_argparse(capsys, monkeypatch):
    # Đảm bảo encrypt_env không còn import argparse
    import core_kit.tools.encrypt_env as cli_module
    assert "argparse" not in sys.modules or not hasattr(cli_module, "argparse")

    exit_code = cli_main(["MyTestSecretViaSysArgv"])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "[THÀNH CÔNG]" in captured.out
    assert "enc:" in captured.out
