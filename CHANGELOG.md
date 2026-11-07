# Changelog

Tất cả các thay đổi đáng chú ý của thư viện `core_kit` sẽ được ghi chép tại tệp này.

Định dạng tuân theo [Keep a Changelog](https://keepachangelog.com/vi/1.1.0/)
và quy chuẩn [Semantic Versioning](https://semver.org/lang/vi/).

---

## [Unreleased]

### Đã thêm (Added)
- **CLI `corekit`** (extra `build`, cài vào dependency group `dev` của app), backend đóng gói duy nhất là Nuitka:
  - `corekit build`: đọc `[[tool.corekit.build.targets]]` (`name`, `entry`, `icon`, `windowed`, `onefile`, `datas`, `plugins`, `copy`, `extra_args`, cùng `[tool.corekit.build].company`), build từng target ra `build/<fast|release>/<name>/` kèm `.env` và các mục `copy`, bấm exe là chạy. Chọn chế độ Nhanh / Giao khách và target qua menu; cờ `--fast`, `--release`, `--target` cho CI.
  - `corekit release`: kiểm git sạch, chọn version (`--bump`), build giao khách mọi target, đóng `dist/<name>-<version>-win-x64.zip` (không `.env`, luôn có `.env.example`, kèm `[tool.corekit.release].include`), commit + tag `<app>-vX.Y.Z`, hỏi rồi mới push và tạo GitHub Release. Lỗi trước khi commit thì trả `pyproject.toml`/`uv.lock` về như cũ.
- `core_kit.utils.app_dir()` / `bundle_dir()` / `is_packaged()`: nhận diện dev, Nuitka standalone/onefile và PyInstaller.
- **Script phát hành thư viện `tools/release.py`** (hỏi trong CLI, không cờ): kiểm git sạch/nhánh `main`/tag chưa có, chọn patch/minor/major, ghi version, chốt mục `[Unreleased]` của CHANGELOG thành `[X.Y.Z] - <ngày>`, chạy pytest (lỗi thì hoàn tác), commit + tag `core_kit-vX.Y.Z`, hỏi rồi mới push và tạo GitHub Release. `tools/bump_version.py` nhận thêm tham số đường dẫn file.
- **Bộ dựng lệnh in PCL XL raster (`PCLXLRasterBuilder`)** trong `core_kit.devices`:
  - Đóng gói ảnh raster 1-bit thành job PCL XL bọc PJL, khai báo khổ giấy luôn qua `CustomMediaSize` (mm), kể cả khổ chuẩn (A4, A5, A6, Letter, ...).
  - In đúng khổ tem 102 x 148 mm trên cả ApeosPort Print 4020SD và ApeosPrint 4620 SDW mà không cần đổi cấu hình khay hay bù co giãn/dịch lề (xem ADR-0003).
  - Khay chọn qua PJL `MEDIASOURCE` truyền nguyên văn (`tray=None` mặc định: không chọn khay); không phát biến PJL khổ giấy/hướng nạp.

### Đã thay đổi (Changed)
- Tìm thư mục migration (`resolve_script_location`) theo `bundle_dir()` → `app_dir()` → CWD, chạy đúng với bản build Nuitka. Khi chạy bản đóng gói, `BaseAppSettings` đọc `.env` cạnh exe và `setup_logger` đặt thư mục log tương đối cạnh exe; chạy dev không đổi.
- Tag phát hành thư viện theo chuẩn `core_kit-vX.Y.Z` (tag `v0.2.0` cũ giữ nguyên).
- Ví dụ in tem hiệu chỉnh (`print_test_label.py`) chuyển sang `PCLXLRasterBuilder` với mặc định scale 1.0, shift 0 mm, không chọn khay, xoay 90 độ; bỏ đọc biến môi trường `PRINT_SCALE_X/Y`, `PRINT_SHIFT_X/Y`.

### Ngừng khuyến nghị (Deprecated)
- `PCL5RasterBuilder`: phát `DeprecationWarning` khi khởi tạo. PCL 5 không khai báo được khổ tùy chỉnh trên firmware Brother-family; dùng `PCLXLRasterBuilder` thay thế.

---

## [0.2.0] - 2026-10-29

### Đã thêm (Added)
- **Thiết bị in laser mạng PCL 5 (`core_kit.devices.printer_pcl`)**:
  - `PCL5RasterBuilder`: Hỗ trợ đóng gói lệnh in PCL 5 raster đồ họa kèm cấu hình trang PJL, tự động xoay, co giãn, bù lề cơ khí và hỗ trợ khổ tem tùy chỉnh (Short-Edge Feed).
  - `PCLNetworkPrinter`: Gửi trực tiếp luồng byte dữ liệu in qua TCP Socket (cổng 9100) mà không cần driver hệ điều hành.
- **Đầu dò trạng thái thiết bị ngoại vi (`StatusProbe` / `PJLStatusProbe`)**:
  - Giao diện trừu tượng và triển khai đầu dò trạng thái máy in qua lệnh PJL `@PJL INFO STATUS`.
  - Phân biệt rõ trạng thái lỗi kết nối mạng vật lý (`Printer Offline`) và trạng thái máy in đang bận hoặc lỗi phần cứng (`PrinterStatus`).
- **Quản lý phiên làm việc CSDL (`core_kit.database`)**:
  - Bổ sung context manager `session_scope` cho `DatabaseManager`, thuận tiện cho các ứng dụng Desktop (PySide6) và script CLI quản lý vòng đời session.
- **Máy quét mã nối tiếp (`SerialScannerReader`)**:
  - Quản lý đọc dữ liệu mã vạch từ cổng nối tiếp COM / RS-232 qua `pyserial`.

---

## [0.1.0] - 2026-10-14

### Đã thêm (Added)
- Khởi tạo nền tảng thư viện `core_kit` dùng chung cho Web (FastAPI) và Desktop (PySide6).
- Module cấu hình bảo mật `core_kit.config` với cơ chế giải mã tự động các biến môi trường mã hóa token `enc:...`.
- Module cơ sở dữ liệu `core_kit.database` dựa trên SQLAlchemy 2.0 và tích hợp quản lý migration tự động với Alembic.
- Module xác thực và mã hóa mật khẩu `core_kit.auth` (JWT + bcrypt).
- Module in tem nhãn nhiệt TSPL `TSPLBuilder`, `TSPLNetworkPrinter`.
- Công cụ CLI mã hóa biến môi trường `encrypt-env` (`core-kit-encrypt-env`).
