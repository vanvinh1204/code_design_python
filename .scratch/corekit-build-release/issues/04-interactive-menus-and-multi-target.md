# 04 — Menu tương tác và nhiều target

**What to build:** `corekit build` không cờ hiện menu chọn chế độ (Enter = giao khách) và, khi có ≥ 2 target, menu chọn target (Enter = tất cả). `--target` (lặp được) bỏ qua menu target. Chạy không tương tác: thiếu cờ chế độ → lỗi kèm hướng dẫn; thiếu `--target` → tất cả.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Menu đọc qua cổng `ask`, nhập sai thì hỏi lại
- [ ] Các target build tuần tự, gặp lỗi đầu tiên thì dừng, mã thoát khác 0
- [ ] `--target` không khớp tên nào → lỗi liệt kê tên hợp lệ
