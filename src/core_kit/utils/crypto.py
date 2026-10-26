"""Module tiện ích mật mã: Băm SHA-256, sinh UUID/ShortID và mã hóa/giải mã đối xứng cấu hình .env (Fernet)."""

import hashlib
import secrets
import string
import uuid
from typing import Optional, Union
from cryptography.fernet import Fernet

from core_kit.config.vault import vault, ConfigVault

# Tiền tố nhận diện chuỗi đã được mã hóa trong file .env hoặc biến môi trường
PREFIX: str = vault.PREFIX

# Biểu thức chính quy tìm kiếm token mã hóa (kể cả khi lồng trong connection string / URL)
_ENC_REGEX = vault._ENC_REGEX

# Tên biến môi trường cho phép ghi đè khóa mã hóa dùng chung
CIPHER_KEY_ENV_VAR: str = vault.CIPHER_KEY_ENV_VAR

# Khóa bí mật nội bộ mặc định (32-byte Fernet key, tương thích 100% với các hệ thống hiện hữu)
DEFAULT_CIPHER_KEY: bytes = vault.DEFAULT_CIPHER_KEY


def get_cipher_key(custom_key: Optional[Union[str, bytes]] = None) -> bytes:
    """Xác định khóa Fernet để thực hiện mã hóa / giải mã qua ConfigVault."""
    return vault.get_cipher_key(custom_key)


def get_fernet(key: Optional[Union[str, bytes]] = None) -> Fernet:
    """Khởi tạo đối tượng Fernet từ khóa được giải quyết."""
    return vault.get_fernet(key)


def encrypt_val(text: str, key: Optional[Union[str, bytes]] = None) -> str:
    """Mã hóa chuỗi văn bản thuần túy và gắn tiền tố enc: qua ConfigVault."""
    return vault.encrypt(text, key=key)


def decrypt_val(val: Optional[str], key: Optional[Union[str, bytes]] = None) -> str:
    """Giải mã chuỗi cấu hình môi trường nếu có tiền tố enc: hoặc chứa token enc: qua ConfigVault."""
    return vault.decrypt(val, key=key)


def generate_uuid() -> str:
    """Sinh chuỗi UUID4 ngẫu nhiên."""
    return str(uuid.uuid4())


def generate_short_id(length: int = 8) -> str:
    """Sinh chuỗi ID ngắn gồm chữ và số ngẫu nhiên (thường dùng cho mã đơn, mã phiếu)."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def hash_sha256(text: str) -> str:
    """Băm chuỗi văn bản bằng thuật toán SHA-256."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
