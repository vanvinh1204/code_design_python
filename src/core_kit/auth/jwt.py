from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt


def create_access_token(
    data: Dict[str, Any],
    secret_key: str,
    algorithm: str = "HS256",
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Tạo chuỗi JWT token cho người dùng đăng nhập.
    Áp dụng cho FastAPI xuất token và PySide6 giải mã/lưu trữ.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=60 * 24)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


def decode_access_token(
    token: str,
    secret_key: str,
    algorithms: Optional[list[str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Giải mã và kiểm tra tính hợp lệ của token JWT.
    Trả về payload nếu hợp lệ, None nếu hết hạn hoặc sai chữ ký.
    """
    if algorithms is None:
        algorithms = ["HS256"]

    try:
        payload = jwt.decode(token, secret_key, algorithms=algorithms)
        return payload
    except jwt.PyJWTError:
        return None
