# 07 — `corekit release`: push và lưu trữ trên GitHub Release

**What to build:** Sau khi commit + tag, release hỏi (mặc định Không) rồi mới push nhánh + tag và `gh release create` kèm các zip; notes lấy từ mục CHANGELOG tương ứng hoặc `--generate-notes`. Cờ `--publish` / `--no-publish` cho CI.

**Blocked by:** 06

**Status:** ready-for-agent

- [ ] Từ chối / không tương tác không cờ → không push gì
- [ ] Thiếu `gh` → lỗi rõ ràng, giữ nguyên commit và tag cục bộ, không push
- [ ] Notes đúng mục `## [X.Y.Z]` của CHANGELOG, không có thì `--generate-notes`
