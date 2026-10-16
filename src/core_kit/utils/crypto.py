import hashlib
import secrets
import string
import uuid


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
