# 03 — Đủ schema target

**What to build:** Target khai được `icon`, `onefile`, `datas`, `plugins`, `copy`, `extra_args`, cùng `[tool.corekit.build].company`; exe mang version resource lấy từ `[project].version`.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] `datas`: thư mục → `--include-data-dir=SRC=REL`, file → `--include-data-files=SRC=REL`
- [ ] `copy`: chép nguyên vẹn ra cạnh exe, giữ đường dẫn tương đối
- [ ] `onefile = true` → `--mode=onefile`, kết quả `build/<chế độ>/<name>/<name>.exe`
- [ ] `0.3.0rc1` → `--product-version=0.3.0`, `--file-version=0.3.0`
- [ ] Đường dẫn khai báo không tồn tại hoặc khóa lạ trong target → lỗi trước khi gọi Nuitka
