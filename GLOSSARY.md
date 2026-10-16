# Core Kit

Thư viện nền tảng module dùng chung cho các ứng dụng Web FastAPI và Desktop PySide6, cung cấp các khối xây dựng cốt lõi về cấu hình, cơ sở dữ liệu, xác thực, client API và giao tiếp thiết bị ngoại vi.

## Language

**PCL 5 Raster**:
Luồng dữ liệu đồ họa nhị phân (1-bit monochrome) đóng gói theo chuẩn Printer Command Language Level 5 để nạp trực tiếp vào bộ đệm điểm ảnh của máy in laser.
_Avoid_: PostScript, GDI raster, bitmap dump

**PJL (Printer Job Language)**:
Ngôn ngữ điều khiển tác vụ in dùng để cấu hình khay giấy, kích thước trang vật lý, chuyển đổi chế độ thông dịch và truy vấn trạng thái máy in mạng.
_Avoid_: ESC/POS, TSPL header, Job Spool

**RAW Socket Printing**:
Cơ chế gửi trực tiếp luồng byte dữ liệu in qua kết nối TCP socket (cổng 9100) đến card mạng máy in mà không qua driver hệ điều hành.
_Avoid_: Spooler printing, Driver printing, CUPS queue
