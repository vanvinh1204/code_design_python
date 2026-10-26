"""
Công cụ dòng lệnh dành cho IT/Admin/Dev: Mã hóa thông tin xác thực CSDL và cấu hình nhạy cảm cho file .env.
Tuân thủ nghiêm ngặt quy tắc dự án: Không sử dụng thư viện argparse.

Cách sử dụng:
    1. Nhập trực tiếp qua dòng lệnh:
       py -m core_kit.tools.encrypt_env "MatKhauCanMaHoa"

    2. Chạy không có tham số để nhập ẩn từ bàn phím (không lộ mật khẩu trên màn hình):
       py -m core_kit.tools.encrypt_env

    3. Tùy biến khóa mã hóa riêng biệt (nếu không muốn dùng khóa mặc định):
       py -m core_kit.tools.encrypt_env "MatKhauCanMaHoa" --key "32_URLSAFE_BASE64_BYTES_KEY="
"""

import sys
import getpass
from typing import Optional, Sequence

# Đảm bảo in tiếng Việt trên console Windows không bị UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from core_kit.config.vault import vault, CIPHER_KEY_ENV_VAR


def print_help():
    print("Sử dụng: encrypt-env [CHUOICANMAHOA] [--key KHOA_TUY_BIEN]")
    print("\nCông cụ mã hóa dữ liệu nhạy cảm (.env) dùng chung cho các dự án hệ thống.")
    print("Tùy chọn:")
    print("  -h, --help            Hiển thị trợ giúp này")
    print(f"  -k, --key KHOA        Khóa Fernet 32-byte (mặc định đọc từ {CIPHER_KEY_ENV_VAR})")


def main(argv: Optional[Sequence[str]] = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)

    # Phân tích tham số dòng lệnh thủ công không dùng argparse
    custom_key: Optional[str] = None
    raw_text: Optional[str] = None

    idx = 0
    while idx < len(raw_args):
        arg = raw_args[idx]
        if arg in ("-h", "--help"):
            print_help()
            return 0
        elif arg in ("-k", "--key"):
            idx += 1
            if idx < len(raw_args):
                custom_key = raw_args[idx]
            else:
                print("[LỖI] Thiếu giá trị sau tham số --key / -k")
                return 1
        elif arg.startswith("--key="):
            custom_key = arg.split("=", 1)[1]
        elif arg.startswith("-"):
            print(f"[CẢNH BÁO] Tham số không xác định: {arg}")
        else:
            if raw_text is None:
                raw_text = arg
        idx += 1

    print("=" * 65)
    print("  CORE-KIT: CÔNG CỤ MÃ HÓA THÔNG TIN CẤU HÌNH .ENV CHO IT/DEV")
    print("=" * 65)

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
        # Tiến hành mã hóa qua ConfigVault
        encrypted = vault.encrypt(raw_text, key=custom_key)

        # Tự động kiểm tra giải mã ngược để đảm bảo tính toàn vẹn 100%
        decrypted = vault.decrypt(encrypted, key=custom_key)
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
    if custom_key:
        print("\n* Chú ý: Bạn đang dùng khóa tùy biến. Hãy đảm bảo dự án có khai báo biến:")
        print(f"  {CIPHER_KEY_ENV_VAR}={custom_key}")
    print("=" * 65)

    return 0


if __name__ == "__main__":
    sys.exit(main())
