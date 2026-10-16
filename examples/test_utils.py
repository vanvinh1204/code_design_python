import sys
from pathlib import Path

# Cấu hình UTF-8 cho Windows Terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Thêm thư mục src vào sys.path để import core_kit trực tiếp
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core_kit.utils import (
    format_vn_date,
    format_vn_datetime,
    generate_short_id,
    generate_uuid,
    hash_sha256,
    now_utc,
    parse_vn_datetime,
)

print("=" * 50)
print("TEST THỬ NGHIỆM: core_kit.utils")
print("=" * 50)

# 1. Thử nghiệm xử lý ngày giờ
now = now_utc()
print(f"1. Giờ UTC hiện tại           : {now}")
print(f"2. Định dạng ngày giờ VN      : {format_vn_datetime(now)}")
print(f"3. Định dạng ngày VN          : {format_vn_date(now)}")

str_time = "14/10/2026 15:30:00"
parsed = parse_vn_datetime(str_time)
print(f"4. Parse chuỗi '{str_time}'  : {parsed}")

# 2. Thử nghiệm sinh mã và băm
uuid_code = generate_uuid()
short_code = generate_short_id(8)
hash_val = hash_sha256("MatKhau@123")

print(f"5. Mã UUID sinh ra            : {uuid_code}")
print(f"6. Mã ngắn sinh ra (Barcode)  : {short_code}")
print(f"7. SHA256('MatKhau@123')     : {hash_val}")
print("=" * 50)
print("-> Hoàn tất test utils thành công!")
