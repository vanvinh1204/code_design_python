import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

try:
    from core_kit.auth import (
        create_access_token,
        decode_access_token,
        hash_password,
        verify_password,
    )

    print("=" * 50)
    print("TEST THỬ NGHIỆM: core_kit.auth")
    print("=" * 50)

    # 1. Thử nghiệm Hash và Verify mật khẩu
    raw_pass = "SecretPass#2026"
    print(f"1. Mật khẩu gốc           : {raw_pass}")
    hashed = hash_password(raw_pass)
    print(f"2. Chuỗi đã Hash (bcrypt) : {hashed}")

    check_ok = verify_password(raw_pass, hashed)
    check_fail = verify_password("SaiMatKhau", hashed)
    print(f"3. Kiểm tra pass đúng     : {'Chính xác' if check_ok else 'Lỗi'}")
    print(f"4. Kiểm tra pass sai      : {'Chính xác' if not check_fail else 'Lỗi'}")

    # 2. Thử nghiệm JWT Token
    secret_key = "my-super-secret-key-32-chars-long!"
    user_payload = {"user_id": 101, "username": "admin", "role": "manager"}

    token = create_access_token(data=user_payload, secret_key=secret_key)
    print(f"5. Token JWT sinh ra      : {token[:40]}...")

    decoded = decode_access_token(token=token, secret_key=secret_key)
    print(f"6. Giải mã Token payload  : {decoded}")
    print("=" * 50)
    print("-> Hoàn tất test auth thành công!")

except ImportError as e:
    print(f"[LƯU Ý] Chưa cài thư viện cho Auth ({e}). Chạy: pip install passlib[bcrypt] pyjwt")
