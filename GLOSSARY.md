# Core Kit

Thư viện nền tảng module dùng chung cho các ứng dụng Web FastAPI và Desktop PySide6, cung cấp các khối xây dựng cốt lõi về cấu hình, cơ sở dữ liệu, xác thực, client API và giao tiếp thiết bị ngoại vi.

## Language

**PCL 5 Raster**:
Luồng dữ liệu đồ họa nhị phân (1-bit monochrome) đóng gói theo chuẩn Printer Command Language Level 5 để nạp trực tiếp vào bộ đệm điểm ảnh của máy in laser.
_Avoid_: PostScript, GDI raster, bitmap dump

**PCL XL**:
Ngôn ngữ mô tả trang dạng nhị phân (PCL 6 Enhanced) gồm toán tử và thuộc tính có kiểu, dùng trong dự án để gửi ảnh raster 1-bit kèm kích thước trang khai báo tường minh.
_Avoid_: PCL 6 (khi nói chung chung), PCL 5, PCLXL raster dump

**CustomMediaSize**:
Kích thước trang vật lý (rộng x cao, đơn vị mm) khai báo ngay trong lệnh bắt đầu trang của PCL XL, là cách khai báo khổ giấy duy nhất đã kiểm chứng đúng trên mọi Printer Family đang dùng.
_Avoid_: Custom paper, khổ tùy chỉnh PJL, LCUSTOMPAPER, PAPERWIDTH

**Printer Family**:
Nhóm máy in có chung dòng firmware gốc (hiện có: Lexmark-family như ApeosPort Print 4020SD, Brother-family như ApeosPrint 4620 SDW), nhận diện qua `@PJL INFO ID` và cách đặt tên biến PJL; quyết định máy hiểu những biến PJL và tên khay nào.
_Avoid_: Printer model, Brand, Vendor

**PJL (Printer Job Language)**:
Ngôn ngữ điều khiển tác vụ in dùng để cấu hình khay giấy, kích thước trang vật lý, chuyển đổi chế độ thông dịch và truy vấn trạng thái máy in mạng.
_Avoid_: ESC/POS, TSPL header, Job Spool

**RAW Socket Printing**:
Cơ chế gửi trực tiếp luồng byte dữ liệu in qua kết nối TCP socket (cổng 9100) đến card mạng máy in mà không qua driver hệ điều hành.
_Avoid_: Spooler printing, Driver printing, CUPS queue

**Status Probe**:
Đầu dò trạng thái máy in, nắm trọn một giao thức truy vấn trạng thái: byte lệnh truy vấn, dấu kết thúc phản hồi và cách phân tích phản hồi thành trạng thái thiết bị. Ví dụ hiện có: PJL `@PJL INFO STATUS`.
_Avoid_: Status parser, Health check, Printer monitor

**Printer Offline**:
Trạng thái khi không thiết lập được kết nối hoặc truy vấn tới máy in (timeout, bị từ chối kết nối). Khác với máy in trả lời được nhưng đang báo lỗi (kẹt giấy, mở nắp).
_Avoid_: Connection Error status, Printer error

**Build Target**:
Một exe khai trong một khối `[[tool.corekit.build.targets]]` của app; mỗi target build độc lập ra thư mục riêng `build/<chế độ>/<name>/`.
_Avoid_: Spec, Build profile, Multidist

**Bản giao khách (Release Package)**:
File zip `<name>-<version>-win-x64.zip` mà `corekit release` tạo cho một Build Target: một thư mục gốc kèm version, không chứa `.env` thật, luôn có `.env.example` cùng tài liệu đi kèm.
_Avoid_: Installer, Artifact, Bản build

**App Dir**:
Thư mục chứa file exe của bản đóng gói (khi chạy dev là thư mục hiện tại), nơi đặt những thứ khách sửa hoặc thay được: `.env`, `models/`, `logs/`. Khác **Bundle Dir** (nơi chứa dữ liệu chỉ đọc gom kèm, là thư mục giải nén tạm với bản onefile).
_Avoid_: Base dir, Root dir, `__file__` dir

