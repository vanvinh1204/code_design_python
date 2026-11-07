# 02 — Tracer bullet `corekit build` một target, chọn chế độ bằng cờ

**What to build:** Trong thư mục app, `uv run corekit build --fast` hoặc `--release` đọc target tối thiểu (`name`, `entry`, `windowed`) từ `pyproject.toml`, gọi Nuitka standalone với tham số đúng chế độ, rồi để lại `build/<chế độ>/<name>/` chạy được ngay (kèm `.env`, hoặc `.env.example` + cảnh báo). `core_kit` có extra `build` và script `corekit`.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `main(argv, ports)` là điểm vào; cổng thật mặc định, test dùng cổng giả
- [ ] fast: `--lto=no`, không `--deployment`, console `attach`; release: `--lto=yes`, `--deployment`, console theo `windowed`
- [ ] Luôn có `--assume-yes-for-downloads`, `--remove-output`, `--jobs`, `--output-filename=<name>.exe`
- [ ] Thư mục kết quả cũ bị xóa trước khi build; in đường dẫn, dung lượng, thời gian
- [ ] Thiếu `pyproject.toml`, thiếu khối target, thiếu file entry → lỗi rõ ràng, mã thoát 1; Nuitka lỗi → mã thoát khác 0
