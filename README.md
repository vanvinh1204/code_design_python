# Core Kit (`core_kit`)

Thư viện nền tảng module dùng chung (Shared Core Library) cho cả hệ thống **Web (FastAPI + Jinja2)** và **Desktop App (PySide6)**.

---

## 1. Cài đặt trực tiếp từ GitHub

Bạn có thể cài đặt toàn bộ hoặc cài theo từng nhóm module (Extras) để tối ưu dung lượng:

```bash
# Cài đặt toàn bộ tính năng
pip install "git+https://github.com/your-username/core_kit.git#egg=core_kit[all]"

# Dự án Web (FastAPI) chỉ cần: Cấu hình, Database, Xác thực, Health (/health)
pip install "git+https://github.com/your-username/core_kit.git#egg=core_kit[config,db,auth,web]"

# Dự án Desktop (PySide6) chỉ cần: Client API, Thiết bị in ấn/quét mã, Logger
pip install "git+https://github.com/your-username/core_kit.git#egg=core_kit[client,devices,logger]"
```

App theo chuẩn dự án (dùng `uv`) ghim `core_kit` theo tag `core_kit-vX.Y.Z` trong `pyproject.toml` của app:

```toml
[project]
dependencies = ["core-kit[config,db,web]"]

[dependency-groups]
dev = ["core-kit[build]"]          # CLI corekit build/release (Nuitka), không gom vào exe

[tool.uv.sources]
core-kit = { git = "https://github.com/vanvinh1204/code_design_python.git", tag = "core_kit-v0.3.0" }
```

Tag của thư viện theo dạng `core_kit-vX.Y.Z` (tag `v0.2.0` cũ vẫn giữ).

Phát hành phiên bản mới bằng `python tools/release.py` (không có cờ, mọi lựa chọn hỏi trong CLI): kiểm git sạch và đúng nhánh `main`, chọn patch/minor/major, ghi version vào `pyproject.toml` + `src/core_kit/__init__.py`, đổi mục `[Unreleased]` trong `CHANGELOG.md` thành `[X.Y.Z] - <ngày>`, chạy pytest (lỗi thì trả file về như cũ), commit `chore(release): bump version to X.Y.Z` + tag `core_kit-vX.Y.Z`, rồi hỏi mới push và tạo GitHub Release (cần `gh`). Chỉ nâng số version không commit: `python tools/bump_version.py patch|minor|major`.

---

## 2. Hướng dẫn sử dụng các Module

### 2.1. Cấu hình (`core_kit.config`)
Đọc biến môi trường từ file `.env` và **tự động giải mã trong suốt** mọi giá trị bắt đầu bằng hoặc chứa token `enc:...` (mật khẩu CSDL, API key...):

```python
from core_kit.config import BaseAppSettings

class AppSettings(BaseAppSettings):
    custom_param: str = "default_value"
    # Nếu file .env có:
    # DB_PASSWORD=enc:gAAAAAB...
    # DATABASE_URL=postgresql://admin:enc:gAAAAAB...@localhost:5432/db
    # Pydantic sẽ tự động giải mã ra chuỗi thuần túy ngay khi nạp cấu hình!

settings = AppSettings()
print(settings.database_url) # Chuỗi đã được giải mã sẵn sàng kết nối CSDL
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

#### 2.3.2. Máy in laser mạng PCL XL (PCL 6) Raster & PJL (Printer Family Lexmark, Brother — đã kiểm chứng)
Hỗ trợ in trực tiếp qua RAW TCP Socket (cổng 9100) không cần driver hệ điều hành. Khổ giấy (kể cả khổ tem tùy chỉnh) luôn được khai báo qua `CustomMediaSize` của PCL XL, nên không phụ thuộc cấu hình khổ giấy của khay trên máy in:
```python
from PIL import Image
from core_kit.devices import PCLXLRasterBuilder, PCLNetworkPrinter

# 1. Khởi tạo builder cho khổ tem decal 102 x 148 mm.
#    tray là tên MEDIASOURCE PJL của chính máy in (vd. 4620 SDW: "TRAY2", 4020SD: "TRAY1");
#    bỏ trống (None) để máy in dùng khay mặc định.
builder = PCLXLRasterBuilder(
    paper_size="CUSTOM",
    width_mm=102.0,
    height_mm=148.0,
    tray="TRAY2",
    dpi=300,
    job_name="SHIPPING_LABEL",
)

# 2. Thêm trang in: xoay, căn giữa; scale/shift chỉ dùng khi cần tinh chỉnh theo máy in
label_image = Image.open("label_artwork.png")
builder.add_page(image=label_image, rotate=90, auto_center=True)
payload = builder.build()

# 3. Kết nối máy in qua mạng, kiểm tra trạng thái phần cứng và gửi lệnh
printer = PCLNetworkPrinter(host="192.168.1.220", port=9100, timeout=5.0)

# Truy vấn trạng thái máy in (kẹt giấy, hết giấy, sẵn sàng)
status = printer.get_status()
print(f"Trạng thái LCD: {status.display} | Sẵn sàng: {status.is_ready}")

if status.is_ready:
    success = printer.send(payload, verify_ready=True)
    if success:
        print("Đã gửi lệnh in laser PCL XL thành công!")
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

Thư mục gốc của app (`core_kit.utils`), dùng thay cho `__file__` vì bản onefile chạy từ thư mục giải nén tạm:

```python
from core_kit.utils import app_dir, bundle_dir, data_dir

env_file = app_dir() / ".env"          # App Dir: nơi cài — .env, models/, các mục copy của corekit build
model = bundle_dir() / "assets" / "x"  # Bundle Dir: dữ liệu chỉ đọc gom kèm (datas)
db_file = data_dir() / "app.sqlite"    # Data Dir: dữ liệu sinh lúc chạy — logs/, SQLite, upload...
```

`data_dir()` trả về biến môi trường `DATA_DIR` nếu được đặt (tự tạo thư mục nếu chưa có), không thì bằng `app_dir()`. Nhờ vậy chạy dev (`uv run main.py`), chạy exe tay hay chạy dưới Windows service (NSSM đặt `DATA_DIR=%ProgramData%\<service>`) đều một đường code. `setup_logger` của `core_kit.logger` mặc định ghi vào `data_dir() / "logs"`; truyền đường dẫn tuyệt đối thì giữ nguyên.

### 2.7. Health check cho app server (`core_kit.web`)

Cần extra `web` (`fastapi`). `make_health_router(version)` trả về `APIRouter` có `GET /health` → `200 {"status": "ok", "version": "<version>"}`; đây là hợp đồng mà công cụ vận hành (`nssm_manager`) gọi để biết web còn trả lời và đang chạy bản nào. Router không tự gắn vào app, không kiểm tra DB hay dịch vụ phụ thuộc và không cần xác thực — app gắn một dòng trong `entrypoints/api/`:

```python
from fastapi import FastAPI
from core_kit.web import make_health_router

from myapp import __version__   # đúng version của app ([project].version lúc build)

app = FastAPI()
app.include_router(make_health_router(__version__))
```

### 2.8. Công cụ mã hóa cấu hình .env (`core_kit.tools.encrypt_env`)

#### Cách 1: Sử dụng qua dòng lệnh (CLI)
Sau khi cài đặt `core_kit`, lệnh `encrypt-env` (hoặc `core-kit-encrypt-env`) có sẵn trong terminal:
```bash
# 1. Nhập trực tiếp qua tham số:
encrypt-env "MatKhauCanMaHoa"

# 2. Hoặc chạy không có tham số để nhập ẩn từ bàn phím (tránh lộ trên màn hình):
encrypt-env

# 3. Chạy qua module python (nếu không cài CLI vào PATH):
py -m core_kit.tools.encrypt_env "MatKhauCanMaHoa"

# 4. Tùy biến khóa mã hóa (nếu dự án cần dùng khóa riêng):
encrypt-env "MatKhauCanMaHoa" --key "32_URLSAFE_BASE64_KEY="
```

#### Cách 2: Gọi trực tiếp từ code Python
```python
from core_kit.utils.crypto import encrypt_val, decrypt_val

# Mã hóa chuỗi với tiền tố enc:
ciphertext = encrypt_val("MySecretDbPassword")
# -> enc:gAAAAAB...

# Giải mã chuỗi
plaintext = decrypt_val(ciphertext)
# -> MySecretDbPassword
```

### 2.9. Đóng gói exe và phát hành bản giao khách (`corekit build` / `corekit release`)

Cài `core-kit[build]` vào dependency group `dev` của app (xem mục 1), rồi chạy trong thư mục app (`apps/<tên>/`). Lệnh chỉ đọc `pyproject.toml` ở thư mục hiện tại. Backend đóng gói duy nhất là **Nuitka**; lần đầu Nuitka tự tải trình biên dịch C (MinGW64) nếu máy chưa có.

```toml
[tool.corekit.build]
company = "Công ty ABC"              # tùy chọn, ghi vào thông tin file exe

[[tool.corekit.build.targets]]      # lặp khối này cho mỗi exe (ví dụ UI + tool CLI)
name = "MyApp"                       # tên exe và tên sản phẩm
entry = "main.py"                    # mặc định main.py (chuẩn v1.2.0)
icon = "assets/icon.ico"
windowed = true                      # app giao diện, không hiện cửa sổ cmd
onefile = false                      # true: một file exe duy nhất
datas = ["assets/"]                  # dữ liệu chỉ đọc gom vào bản build (thư mục hoặc file)
plugins = ["pyside6"]                # plugin Nuitka, khai tường minh
copy = ["models/"]                   # chép nguyên vẹn ra cạnh exe, khách sửa/thay được
extra_args = []                      # truyền thẳng cho Nuitka khi schema không đủ

[tool.corekit.release]
include = ["docs/HUONG_DAN.pdf"]     # tài liệu đi kèm bản giao khách
health_path = "/health"             # đường dẫn health ghi vào release.json (mặc định /health, phải bắt đầu bằng /)
```

**`uv run corekit build`** hỏi chế độ (Enter = giao khách) và, khi có nhiều target, target cần build (Enter = tất cả). Kết quả ở `build/<fast|release>/<name>/`, đã kèm `.env` (hoặc `.env.example` nếu chưa có `.env`) và các mục `copy` — bấm exe là chạy.

| | Nhanh (`--fast`) | Giao khách (`--release`, mặc định) |
|---|---|---|
| LTO | tắt | bật |
| `--deployment` | tắt (giữ kiểm tra tương thích để dò lỗi thiếu module) | bật |
| Console | `attach` (chạy từ cmd thấy traceback) | theo `windowed` |

Chạy không tương tác (CI): `corekit build --release --target MyApp` (`--target` lặp được; thiếu thì build tất cả, thiếu chế độ thì báo lỗi).

**`uv run corekit release`** lần lượt:
1. kiểm git sạch;
2. chọn version (patch/minor/major/giữ nguyên; CI: `--bump patch`), từ chối nếu tag đã tồn tại;
3. kiểm `.env.example`, các mục `include`, mục CHANGELOG của version mới (thiếu thì cảnh báo, hỏi tiếp tục);
4. ghi version vào `pyproject.toml` (và `uv lock`), build giao khách mọi target — lỗi thì trả lại như cũ;
5. đóng `dist/<name>-<version>-win-x64.zip` cho mỗi target: một thư mục gốc `<name>-<version>/`, **không có `.env`**, luôn có `.env.example`, kèm `include` và Manifest phát hành `release.json`;
6. commit `chore(release): <app> vX.Y.Z` + tag `<app>-vX.Y.Z`;
7. hỏi (mặc định Không; CI: `--publish`/`--no-publish`) rồi mới push và tạo GitHub Release kèm các zip (cần GitHub CLI `gh`), notes lấy từ CHANGELOG hoặc tự sinh.

**Manifest phát hành `release.json`** nằm ở gốc mỗi zip (ngang `.env.example`), để công cụ cài (ví dụ `nssm_manager`) biết đang cài repo nào, app nào, version nào và gọi health ở đâu mà không đoán từ tên file. Mỗi zip một manifest đúng target của nó:

```json
{
  "repo": "kho",                            // tên thư mục gốc repo git chứa app (không có .git thì tên thư mục app)
  "app": "server",                          // [project].name
  "target": "KhoServer",                    // tên Build Target
  "version": "1.2.0",
  "built_at": "2026-11-11T09:30:00+07:00",  // ISO 8601, giờ địa phương kèm offset
  "health_path": "/health",                 // [tool.corekit.release].health_path, mặc định /health
  "core_kit": "0.4.0"                       // version core_kit chạy lệnh release
}
```

`health_path` phải là chuỗi bắt đầu bằng `/`; sai kiểu thì lệnh dừng với lỗi cấu hình như các khóa khác.

Code app nên dùng `core_kit.utils.app_dir()` (thư mục chứa exe: `.env`, `models/`), `data_dir()` (dữ liệu sinh lúc chạy: `logs/`, SQLite...; theo biến môi trường `DATA_DIR` nếu có) và `bundle_dir()` (dữ liệu gom kèm `datas`) thay cho `__file__`, vì bản onefile chạy từ thư mục giải nén tạm (xem mục 2.6).
