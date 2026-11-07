# 01 — `app_dir()` / `bundle_dir()` và nhận diện bản build Nuitka

**What to build:** `core_kit` biết mình đang chạy dev, Nuitka standalone, Nuitka onefile hay PyInstaller, và trả đúng thư mục chứa exe (`app_dir()`) cùng thư mục chứa dữ liệu gom kèm (`bundle_dir()`). Migration tìm `migrations/` theo `bundle_dir()` → `app_dir()` → CWD; `BaseAppSettings` đọc `.env` và `setup_logger` đặt `logs/` cạnh exe khi chạy bản đóng gói. Chạy dev không đổi hành vi.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `is_packaged()`, `app_dir()`, `bundle_dir()` trả đúng cho dev, Nuitka standalone, Nuitka onefile, PyInstaller (test giả lập `__compiled__`, `sys.frozen`, `sys._MEIPASS`, `sys.executable`)
- [ ] `resolve_script_location` tìm được `migrations/` trong bản Nuitka khi CWD khác thư mục exe
- [ ] `.env` / `logs/` neo vào `app_dir()` chỉ khi packaged; test cũ vẫn xanh
