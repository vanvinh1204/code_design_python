import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core_kit.devices import TSPLBuilder

print("=" * 50)
print("TEST THỬ NGHIỆM: core_kit.devices (TSPL Builder)")
print("=" * 50)

# Khởi tạo kích thước tem 80mm x 50mm
builder = TSPLBuilder(width_mm=80, height_mm=50)

# Thiết lập các thành phần in
builder.text(x=20, y=20, content="CONG TY ABC - TEM XUAT KHO", font="TSS24.BF2", x_multi=1, y_multi=1)
builder.line(x=20, y=50, width=550, height=2)
builder.text(x=20, y=60, content="SAN PHAM: BAN LE KIM LOAI", font="TSS24.BF2", x_multi=1, y_multi=1)
builder.barcode(x=20, y=100, code="PRD-998877", height=50, readable=1)
builder.dmatrix(x=380, y=100, content="PRD-998877-LOT01", size=6)
builder.text(x=20, y=170, content="SO LUONG: 100 PCS", font="TSS24.BF2", x_multi=1, y_multi=1)

# Sinh lệnh in
raw_tspl = builder.print(copies=1)

print("Chuỗi lệnh TSPL được sinh ra để gửi máy in:")
print("-" * 50)
print(raw_tspl)
print("-" * 50)
print("-> Hoàn tất test devices (TSPL Builder) thành công!")
