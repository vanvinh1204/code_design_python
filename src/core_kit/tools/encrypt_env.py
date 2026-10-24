"""
Công cụ dòng lệnh dành cho IT/Admin/Dev: Mã hóa thông tin xác thực CSDL và cấu hình nhạy cảm cho file .env.

Cách sử dụng:
    1. Nhập trực tiếp qua dòng lệnh:
       encrypt-env "MatKhauCanMaHoa"
       # hoặc qua module:
       py -m core_kit.tools.encrypt_env "MatKhauCanMaHoa"

    2. Chạy không có tham số để nhập trực tiếp từ bàn phím (không hiện mật khẩu trên màn hình):
       encrypt-env

    3. Tùy biến khóa mã hóa riêng biệt (nếu không muốn dùng khóa mặc định):
       encrypt-env "MatKhauCanMaHoa" --key "32_URLSAFE_BASE64_BYTES_KEY="
"""

import sys
import getpass
import argparse
from typing import Optional, Sequence

# Đảm bảo in tiếng Việt trên console Windows không bị UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from core_kit.utils.crypto import encrypt_val, decrypt_val, PREFIX, CIPHER_KEY_ENV_VAR


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="encrypt-env",
        description="Công cụ mã hóa dữ liệu nhạy cảm (.env) dùng chung cho các dự án hệ thống.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "text",
        nargs="?",
        default=None,
        help="Chuỗi cần mã hóa (mật khẩu CSDL, API key...). Nếu bỏ trống, chương trình sẽ yêu cầu nhập ẩn từ bàn phím.",
    )
    parser.add_argument(
        "--key",
        "-k",
        dest="custom_key",
        default=None,
        help=f"Khóa Fernet 32-byte tùy biến (nếu không cung cấp, sẽ đọc từ biến môi trường {CIPHER_KEY_ENV_VAR} hoặc dùng khóa mặc định).",
    )

    args = parser.parse_args(argv)

    print("=" * 65)
    print("  CORE-KIT: CÔNG CỤ MÃ HÓA THÔNG TIN CẤU HÌNH .ENV CHO IT/DEV")
    print("=" * 65)

    raw_text = args.text
    if raw_text is None:
        try:
            raw_text = getpass.getpass("Nhập mật khẩu / chuỗi cần mã hóa: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[ĐÃ HỦY] Thao tác bị gián đoạn bởi người dùng.")
            return 1
    else:
        raw_text = str(raw_text).strip()

    if not raw_text:
        print("[LỖI] Chuỗi nhập vào không được để trống!")
        return 1

    try:
        # Tiến hành mã hóa
        encrypted = encrypt_val(raw_text, key=args.custom_key)

        # Tự động kiểm tra giải mã ngược để đảm bảo tính toàn vẹn 100%
        decrypted = decrypt_val(encrypted, key=args.custom_key)
        assert decrypted == raw_text, "Dữ liệu sau khi giải mã không khớp với chuỗi gốc!"
    except Exception as exc:
        print(f"[LỖI] Quá trình mã hóa hoặc tự kiểm tra giải mã thất bại: {exc}")
        return 1

    print("\n[THÀNH CÔNG] Chuỗi đã được mã hóa an toàn:")
    print("-" * 65)
    print(f"{encrypted}")
    print("-" * 65)
    print("\nHướng dẫn sử dụng trong file .env:")
    print("  - Nếu là mật khẩu CSDL:")
    print(f"    DB_PASSWORD={encrypted}")
    print("  - Hoặc đường dẫn kết nối CSDL (database_url):")
    print(f"    DATABASE_URL={encrypted}")
    print("  - Nếu là tài khoản CSDL (tùy chọn):")
    print(f"    DB_USER={encrypted}")
    if args.custom_key:
        print("\n* Chú ý: Bạn đang dùng khóa tùy biến. Hãy đảm bảo dự án có khai báo biến:")
        print(f"  {CIPHER_KEY_ENV_VAR}={args.custom_key}")
    print("=" * 65)

    return 0


if __name__ == "__main__":
    sys.exit(main())
