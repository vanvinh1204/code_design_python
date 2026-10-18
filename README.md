# Core Kit (`core_kit`)

Thư viện nền tảng module dùng chung (Shared Core Library) cho cả hệ thống **Web (FastAPI + Jinja2)** và **Desktop App (PySide6)**.

---

## 1. Cài đặt trực tiếp từ GitHub

Bạn có thể cài đặt toàn bộ hoặc cài theo từng nhóm module (Extras) để tối ưu dung lượng:

```bash
# Cài đặt toàn bộ tính năng
pip install "git+https://github.com/your-username/core_kit.git#egg=core_kit[all]"

# Dự án Web (FastAPI) chỉ cần: Cấu hình, Database, Xác thực
pip install "git+https://github.com/your-username/core_kit.git#egg=core_kit[config,db,auth]"

# Dự án Desktop (PySide6) chỉ cần: Client API, Thiết bị in ấn/quét mã, Logger
pip install "git+https://github.com/your-username/core_kit.git#egg=core_kit[client,devices,logger]"
```

---

## 2. Hướng dẫn sử dụng các Module

### 2.1. Cấu hình (`core_kit.config`)
Đọc biến môi trường từ file `.env`:
```python
from core_kit.config import BaseAppSettings

class AppSettings(BaseAppSettings):
    custom_param: str = "default_value"

settings = AppSettings()
print(settings.database_url)
```

### 2.2. Cơ sở dữ liệu (`core_kit.database`)
Dùng chung cho cả FastAPI và PySide6:
```python
from core_kit.database import CommonModel, DatabaseManager
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

# Khởi tạo quản lý DB
db_manager = DatabaseManager("sqlite:///./app.db")

# Định nghĩa bảng
class Product(CommonModel):
    __tablename__ = "products"
    name: Mapped[str] = mapped_column(String(100))

# Tạo bảng tự động (chỉ dùng cho test nhanh)
db_manager.create_tables(CommonModel.metadata)

# Hoặc Quản lý Migration tự động (Alembic):
# 1. Khởi tạo template cấu hình migration:
#    init_migration_scaffold(project_dir=".", script_location="migrations")
# 2. Tự động upgrade schema lên phiên bản mới nhất khi khởi động app:
db_manager.migrate(script_location="migrations")

# Sử dụng phiên làm việc (Session):
# 1. Dùng trong PySide6 (Context Manager):
with db_manager.session_scope() as session:
    product = Product(name="Mặt hàng A")
    session.add(product)

# 2. Dùng trong FastAPI (Dependency Injection):
# @app.get("/products")
# def get_products(db = Depends(db_manager.get_db)):
#     return db.query(Product).all()
```


### 2.3. Thiết bị in ấn mạng (`core_kit.devices`)

#### 2.3.1. Máy in tem mã vạch TSPL
```python
from core_kit.devices import TSPLBuilder, TSPLNetworkPrinter

# Tạo mẫu in tem mã vạch
builder = TSPLBuilder(width_mm=80, height_mm=50)
builder.text(x=20, y=20, content="TEN SAN PHAM", x_multi=2, y_multi=2)
builder.barcode(x=20, y=80, code="SP12345678", height=60)
builder.dmatrix(x=350, y=80, content="DATA-MATRIX-CODE", size=8)
tspl_commands = builder.print(copies=1)

# Gửi in qua mạng LAN tới IP máy in
printer = TSPLNetworkPrinter(host="192.168.1.200", port=9100)
printer.send_raw(tspl_commands)
```

#### 2.3.2. Máy in laser mạng PCL 5 Raster & PJL (Fujifilm ApeosPort, HP, Canon, Ricoh)
Hỗ trợ in trực tiếp qua RAW TCP Socket (cổng 9100) không cần driver hệ điều hành, bù trừ lề chết cơ khí và hỗ trợ khổ tem tùy chỉnh (Short-Edge Feed):
```python
from PIL import Image
from core_kit.devices import PCL5RasterBuilder, PCLNetworkPrinter

# 1. Khởi tạo builder cho khổ tem decal 102 x 148 mm từ Khay 1 (Short-Edge Feed)
builder = PCL5RasterBuilder(
    paper_size="CUSTOM",
    width_mm=102.0,
    height_mm=148.0,
    tray="TRAY1",
    feed_direction="SHORTEDGEFEED",
    dpi=300,
    job_name="SHIPPING_LABEL",
)

# 2. Thêm trang in: tự động xoay, co giãn 0.94 tránh cắt lề cơ khí và căn giữa
label_image = Image.open("label_artwork.png")
builder.add_page(
    image=label_image,
    rotate=90,
    scale=0.94,
    shift_x_mm=0.0,
    shift_y_mm=0.0,
    auto_center=True,
)
payload = builder.build()

# 3. Kết nối máy in qua mạng, kiểm tra trạng thái phần cứng và gửi lệnh
printer = PCLNetworkPrinter(host="192.168.1.220", port=9100, timeout=5.0)

# Truy vấn trạng thái máy in (kẹt giấy, hết giấy, sẵn sàng)
status = printer.get_status()
print(f"Trạng thái LCD: {status.display} | Sẵn sàng: {status.is_ready}")

if status.is_ready:
    success = printer.send(payload, verify_ready=True)
    if success:
        print("Đã gửi lệnh in laser PCL 5 thành công!")
else:
    print(f"Không thể in vì máy in đang báo: {status.display}")
```

### 2.4. Đọc máy quét mã vạch qua COM/Serial (`core_kit.devices`)
```python
from core_kit.devices import SerialScannerReader

def on_scan(barcode: str):
    print(f"Mã quét được: {barcode}")

scanner = SerialScannerReader(port="COM3", baudrate=9600)
scanner.start_listening(on_barcode_scanned=on_scan)

# Khi tắt app:
# scanner.stop_listening()
```

### 2.5. HTTP Client cho Desktop App (`core_kit.api_client`)
```python
from core_kit.api_client import BaseApiClient

client = BaseApiClient(base_url="http://localhost:8000")

# Đăng nhập và lưu token
# token = ...
# client.set_token(token)

# Gọi API có type hint và tự đính token
data = client.get("/api/v1/products")
```

### 2.6. Xác thực & Tiện ích (`core_kit.auth`, `core_kit.utils`)
```python
from core_kit.auth import hash_password, verify_password, create_access_token
from core_kit.utils import format_vn_datetime, now_utc, generate_short_id

hashed = hash_password("123456")
assert verify_password("123456", hashed)

order_code = f"ORD-{generate_short_id(6)}"
time_str = format_vn_datetime(now_utc())
```
