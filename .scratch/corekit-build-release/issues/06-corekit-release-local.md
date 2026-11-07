# 06 — `corekit release`: tạo bản giao khách cục bộ

**What to build:** `uv run corekit release` kiểm git sạch, chọn version (menu hoặc `--bump`), build giao khách mọi target, đóng zip `dist/<name>-<version>-win-x64.zip` cho mỗi target, rồi commit và tag `<tên app>-vX.Y.Z`. Không push gì.

**Blocked by:** 03, 04

**Status:** ready-for-agent

- [ ] Git bẩn → dừng; tag đã tồn tại → dừng (kể cả `keep`)
- [ ] Zip có một thư mục gốc `<name>-<version>/`, không có `.env`, luôn có `.env.example`, có các mục `[tool.corekit.release].include`
- [ ] Thiếu `.env.example` hoặc mục `include` → lỗi trước khi build
- [ ] Build lỗi → `pyproject.toml` (và `uv.lock`) trở về như cũ, không commit, không tag
- [ ] `CHANGELOG.md` có nhưng thiếu mục version mới → cảnh báo, hỏi tiếp tục
