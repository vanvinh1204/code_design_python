# 05 — Test Nuitka thật

**What to build:** Một test gắn marker `nuitka` (mặc định bỏ qua) build app hello-world ở chế độ nhanh, cả standalone lẫn onefile, chạy exe và kiểm stdout, gồm cả `app_dir()` in ra từ trong exe.

**Blocked by:** 01, 03

**Status:** ready-for-agent

- [ ] `pytest` mặc định không chạy test này; `pytest -m nuitka` chạy
- [ ] Xác nhận `__compiled__.containing_dir` cho onefile trỏ về thư mục chứa exe
