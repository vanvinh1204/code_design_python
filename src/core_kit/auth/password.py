import bcrypt


def hash_password(password: str) -> str:
    """
    Băm mật khẩu người dùng trước khi lưu trữ vào Database bằng bcrypt trực tiếp.
    Chuẩn hóa tương thích tốt với Python 3.12+.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    So khớp mật khẩu dạng plain text với chuỗi hash đã lưu.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False
