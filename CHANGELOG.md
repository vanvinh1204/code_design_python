# Changelog

Tất cả các thay đổi đáng chú ý của thư viện `core_kit` sẽ được ghi chép tại tệp này.

Định dạng tuân theo [Keep a Changelog](https://keepachangelog.com/vi/1.1.0/)
và quy chuẩn [Semantic Versioning](https://semver.org/lang/vi/).

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
