"""
Module sâu quản lý mật mã cấu hình: Mã hóa/giải mã đối xứng cấu hình .env (Fernet),
tự động giải mã đệ quy mapping cấu hình và cập nhật file .env an toàn.
"""

import os
import re
import logging
from pathlib import Path
from typing import Any, Optional, Union
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class ConfigVault:
    """
    Module sâu quản lý toàn bộ chu trình bảo mật thông tin cấu hình (.env).
    Tập trung giải mã trong suốt cho BaseAppSettings, mã hóa dữ liệu nhạy cảm
    và cung cấp API cập nhật file .env an toàn mà không làm mất comment.
    """

    PREFIX: str = "enc:"
    CIPHER_KEY_ENV_VAR: str = "CORE_KIT_CIPHER_KEY"
    DEFAULT_CIPHER_KEY: bytes = b"V-IsnOd78iQr4EQiDVahzdtfWRSRqRPOpvBLghyoAgI="
    _ENC_REGEX: re.Pattern = re.compile(r"enc:[A-Za-z0-9_\-=]+")

    def __init__(self, default_key: Optional[Union[str, bytes]] = None):
        self._default_key = default_key

    def get_cipher_key(self, custom_key: Optional[Union[str, bytes]] = None) -> bytes:
        """
        Xác định khóa Fernet để thực hiện mã hóa / giải mã.
        Thứ tự ưu tiên: custom_key -> self._default_key -> Biến môi trường -> Khóa mặc định.
        """
        key_candidate = custom_key or self._default_key
        if key_candidate:
            if isinstance(key_candidate, str):
                return key_candidate.strip().encode("ascii")
            return key_candidate

        env_key = os.environ.get(self.CIPHER_KEY_ENV_VAR)
        if env_key:
            return env_key.strip().encode("ascii")

        return self.DEFAULT_CIPHER_KEY

    def get_fernet(self, key: Optional[Union[str, bytes]] = None) -> Fernet:
        """Khởi tạo đối tượng Fernet từ khóa được giải quyết."""
        resolved_key = self.get_cipher_key(key)
        try:
            return Fernet(resolved_key)
        except Exception as exc:
            raise ValueError(
                f"Khóa Fernet không hợp lệ: {exc}. Khóa phải là chuỗi 32 url-safe base64-encoded bytes."
            ) from exc

    def encrypt(self, text: str, key: Optional[Union[str, bytes]] = None) -> str:
        """Mã hóa chuỗi văn bản thuần túy và gắn tiền tố enc:."""
        if not text:
            return ""
        fernet = self.get_fernet(key)
        encrypted_bytes = fernet.encrypt(text.encode("utf-8"))
        return f"{self.PREFIX}{encrypted_bytes.decode('ascii')}"

    def decrypt(self, val: Optional[str], key: Optional[Union[str, bytes]] = None) -> str:
        """
        Giải mã chuỗi cấu hình môi trường nếu có tiền tố enc: hoặc chứa token enc:.
        Hỗ trợ cả trường hợp token enc: được nhúng lồng bên trong URL / connection string.
        """
        if val is None:
            return ""
        val_str = str(val).strip()
        if not val_str:
            return ""

        if self.PREFIX not in val_str:
            return val_str

        # 1. Toàn bộ chuỗi là enc:<token> đơn thuần
        if val_str.startswith(self.PREFIX) and not any(ch in val_str for ch in (" ", "@", "://", "?")):
            token = val_str[len(self.PREFIX):].strip()
            try:
                fernet = self.get_fernet(key)
                decrypted_bytes = fernet.decrypt(token.encode("ascii"))
                return decrypted_bytes.decode("utf-8")
            except (InvalidToken, Exception) as exc:
                logger.error(f"[VAULT_ERROR] Giải mã cấu hình '{val_str[:10]}...' thất bại: {exc}")
                raise ValueError(
                    "Không thể giải mã dữ liệu cấu hình môi trường: chuỗi không hợp lệ, bị cắt cụt hoặc sai khóa giải mã."
                ) from exc

        # 2. Token enc: được nhúng lồng bên trong connection string / URL
        def _sub_token(match: re.Match) -> str:
            token_str = match.group(0)[len(self.PREFIX):]
            try:
                fernet = self.get_fernet(key)
                return fernet.decrypt(token_str.encode("ascii")).decode("utf-8")
            except (InvalidToken, Exception) as exc:
                logger.error(f"[VAULT_ERROR] Giải mã token lồng '{match.group(0)[:10]}...' thất bại: {exc}")
                raise ValueError(
                    "Không thể giải mã dữ liệu cấu hình môi trường: chuỗi không hợp lệ, bị cắt cụt hoặc sai khóa giải mã."
                ) from exc

        return self._ENC_REGEX.sub(_sub_token, val_str)

    def decrypt_mapping(self, data: Any, key: Optional[Union[str, bytes]] = None) -> Any:
        """Tự động duyệt đệ quy dictionary hoặc list để giải mã toàn bộ các token enc:."""
        if isinstance(data, dict):
            return {k: self.decrypt_mapping(v, key=key) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.decrypt_mapping(item, key=key) for item in data]
        elif isinstance(data, str) and self.PREFIX in data:
            return self.decrypt(data, key=key)
        return data

    def update_env_file(
        self,
        env_path: Union[str, Path],
        key: str,
        value: str,
        encrypt: bool = True,
        custom_key: Optional[Union[str, bytes]] = None,
    ) -> bool:
        """
        Cập nhật an toàn một biến môi trường vào file .env, bảo tồn cấu trúc comment hiện có.
        Nếu biến đã tồn tại, thay thế giá trị; nếu chưa có, thêm mới vào cuối file.
        """
        path_obj = Path(env_path)
        val_to_write = self.encrypt(value, key=custom_key) if encrypt else value

        if path_obj.exists():
            content = path_obj.read_text(encoding="utf-8")
        else:
            content = ""

        key_pattern = re.compile(rf"^({re.escape(key)}\s*=).*$", re.MULTILINE)

        if key_pattern.search(content):
            new_content = key_pattern.sub(rf"\g<1>{val_to_write}", content)
        else:
            if content and not content.endswith("\n"):
                content += "\n"
            new_content = content + f"{key}={val_to_write}\n"

        path_obj.write_text(new_content, encoding="utf-8")
        return True


# Singleton instance dùng chung
vault = ConfigVault()

# Hằng số cấp module tiện ích
PREFIX: str = ConfigVault.PREFIX
CIPHER_KEY_ENV_VAR: str = ConfigVault.CIPHER_KEY_ENV_VAR
DEFAULT_CIPHER_KEY: bytes = ConfigVault.DEFAULT_CIPHER_KEY
