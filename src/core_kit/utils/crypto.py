"""Module tiện ích mật mã: Băm SHA-256, sinh UUID/ShortID và mã hóa/giải mã đối xứng cấu hình .env (Fernet)."""

import os
import re
import hashlib
import logging
import secrets
import string
import uuid
from typing import Optional, Union
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Tiền tố nhận diện chuỗi đã được mã hóa trong file .env hoặc biến môi trường
PREFIX: str = "enc:"

# Biểu thức chính quy tìm kiếm token mã hóa (kể cả khi lồng trong connection string / URL)
_ENC_REGEX: re.Pattern = re.compile(r"enc:[A-Za-z0-9_\-=]+")

# Tên biến môi trường cho phép ghi đè khóa mã hóa dùng chung
CIPHER_KEY_ENV_VAR: str = "CORE_KIT_CIPHER_KEY"

# Khóa bí mật nội bộ mặc định (32-byte Fernet key, tương thích 100% với các hệ thống hiện hữu)
DEFAULT_CIPHER_KEY: bytes = b"V-IsnOd78iQr4EQiDVahzdtfWRSRqRPOpvBLghyoAgI="


def get_cipher_key(custom_key: Optional[Union[str, bytes]] = None) -> bytes:
    """
    Xác định khóa Fernet để thực hiện mã hóa / giải mã.
    
    Thứ tự ưu tiên:
    1. custom_key (nếu truyền trực tiếp vào hàm).
    2. Biến môi trường CORE_KIT_CIPHER_KEY (nếu có cấu hình).
    3. DEFAULT_CIPHER_KEY (khóa mặc định nội bộ của thư viện).
    """
    if custom_key:
        if isinstance(custom_key, str):
            return custom_key.strip().encode("ascii")
        return custom_key

    env_key = os.environ.get(CIPHER_KEY_ENV_VAR)
    if env_key:
        return env_key.strip().encode("ascii")

    return DEFAULT_CIPHER_KEY


def get_fernet(key: Optional[Union[str, bytes]] = None) -> Fernet:
    """Khởi tạo đối tượng Fernet từ khóa được giải quyết."""
    resolved_key = get_cipher_key(key)
    try:
        return Fernet(resolved_key)
    except Exception as exc:
        raise ValueError(
            f"Khóa Fernet không hợp lệ: {exc}. Khóa phải là chuỗi 32 url-safe base64-encoded bytes."
        ) from exc


def encrypt_val(text: str, key: Optional[Union[str, bytes]] = None) -> str:
    """
    Mã hóa chuỗi văn bản thuần túy và gắn tiền tố enc:.
    
    Args:
        text: Chuỗi cần mã hóa (ví dụ: mật khẩu CSDL, API key, token).
        key: Khóa tùy biến (nếu None sẽ dùng khóa môi trường hoặc mặc định).
        
    Returns:
        Chuỗi mã hóa có định dạng enc:<base64_ciphertext>.
    """
    if not text:
        return ""
    fernet = get_fernet(key)
    encrypted_bytes = fernet.encrypt(text.encode("utf-8"))
    return f"{PREFIX}{encrypted_bytes.decode('ascii')}"


def decrypt_val(val: Optional[str], key: Optional[Union[str, bytes]] = None) -> str:
    """
    Giải mã chuỗi cấu hình môi trường nếu có tiền tố enc: hoặc chứa token enc:.
    Nếu không chứa enc:, giữ nguyên chuỗi (tương thích ngược với mật khẩu thô).
    Hỗ trợ cả trường hợp token enc: được nhúng bên trong connection string (URL).
    
    Args:
        val: Giá trị chuỗi đọc từ file .env hoặc biến môi trường.
        key: Khóa tùy biến (nếu None sẽ dùng khóa môi trường hoặc mặc định).
        
    Returns:
        Chuỗi văn bản thuần sau khi giải mã hoặc chuỗi gốc ban đầu.
        
    Raises:
        ValueError: Nếu chuỗi mang tiền tố enc: nhưng bị hỏng hoặc giải mã thất bại.
    """
    if val is None:
        return ""
    val_str = str(val).strip()
    if not val_str:
        return ""

    if PREFIX not in val_str:
        return val_str

    # 1. Trường hợp toàn bộ chuỗi là enc:<token> đơn thuần
    if val_str.startswith(PREFIX) and not any(ch in val_str for ch in (" ", "@", "://", "?")):
        token = val_str[len(PREFIX):].strip()
        try:
            fernet = get_fernet(key)
            decrypted_bytes = fernet.decrypt(token.encode("ascii"))
            return decrypted_bytes.decode("utf-8")
        except (InvalidToken, Exception) as exc:
            logger.error(f"[CRYPTO_ERROR] Không thể giải mã dữ liệu cấu hình môi trường '{val_str[:10]}...': {exc}")
            raise ValueError(
                "Không thể giải mã dữ liệu cấu hình môi trường: chuỗi không hợp lệ, bị cắt cụt hoặc sai khóa giải mã."
            ) from exc

    # 2. Trường hợp token enc: được nhúng lồng bên trong chuỗi khác (URL, connection string, ...)
    def _sub_token(match: re.Match) -> str:
        token_str = match.group(0)[len(PREFIX):]
        try:
            fernet = get_fernet(key)
            return fernet.decrypt(token_str.encode("ascii")).decode("utf-8")
        except (InvalidToken, Exception) as exc:
            logger.error(f"[CRYPTO_ERROR] Không thể giải mã token lồng '{match.group(0)[:10]}...': {exc}")
            raise ValueError(
                "Không thể giải mã dữ liệu cấu hình môi trường: chuỗi không hợp lệ, bị cắt cụt hoặc sai khóa giải mã."
            ) from exc

    return _ENC_REGEX.sub(_sub_token, val_str)


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
