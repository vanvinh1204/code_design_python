"""
Module sâu quản lý xác thực và phân quyền: Quản trị token JWT và băm mật khẩu tập trung.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
import jwt

from core_kit.auth.password import hash_password as _hash_password, verify_password as _verify_password


class AuthManager:
    """
    Module sâu quản lý toàn bộ vòng đời xác thực (Token JWT & Password Hashing).
    Đóng gói bí mật secret_key, thuật toán và thời gian sống của token,
    giúp tầng gọi (FastAPI / PySide6) không phải truyền lặp lại các tham số hạ tầng.
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        default_expire_minutes: int = 1440,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.default_expire_minutes = default_expire_minutes

    @classmethod
    def from_settings(cls, settings: Any) -> "AuthManager":
        """Khởi tạo AuthManager tự động từ cấu hình BaseAppSettings hoặc đối tượng tương tự."""
        secret_key = getattr(settings, "secret_key", "default-fallback-secret-key-32bytes")
        algorithm = getattr(settings, "jwt_algorithm", "HS256")
        expire_minutes = getattr(settings, "access_token_expire_minutes", 1440)
        return cls(
            secret_key=secret_key,
            algorithm=algorithm,
            default_expire_minutes=expire_minutes,
        )

    def issue_token(
        self,
        subject: Union[str, int],
        claims: Optional[Dict[str, Any]] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Phát hành JWT access token cho người dùng.

        Args:
            subject: Định danh người dùng (user_id hoặc username).
            claims: Các thông tin bổ sung đính kèm trong token (roles, permissions...).
            expires_delta: Thời gian sống tùy biến (nếu None sẽ dùng default_expire_minutes).
        """
        payload: Dict[str, Any] = {}
        if claims:
            payload.update(claims)

        payload["sub"] = str(subject)

        now = datetime.now(timezone.utc)
        if expires_delta is not None:
            expire_at = now + expires_delta
        else:
            expire_at = now + timedelta(minutes=self.default_expire_minutes)

        payload["exp"] = expire_at
        payload["iat"] = now

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Giải mã và kiểm tra tính toàn vẹn, hạn sử dụng của JWT token.
        Trả về payload dict nếu hợp lệ, None nếu token sai chữ ký, bị sửa đổi hoặc đã hết hạn.
        """
        if not token or not isinstance(token, str):
            return None

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except (jwt.PyJWTError, Exception):
            return None

    def hash_password(self, plain_password: str) -> str:
        """Băm mật khẩu người dùng bằng bcrypt."""
        return _hash_password(plain_password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Kiểm tra mật khẩu nhập vào khớp với chuỗi băm bcrypt."""
        return _verify_password(plain_password, hashed_password)
