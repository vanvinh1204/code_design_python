"""
Router `GET /health` theo hợp đồng chung của chuẩn dự án.

Trả `200` với JSON đúng hai khóa `{"status": "ok", "version": "<version>"}`. Không kiểm tra DB hay
dịch vụ phụ thuộc, không yêu cầu xác thực; chỉ cho biết web còn trả lời và đang chạy bản nào.
"""

from __future__ import annotations

from fastapi import APIRouter


def make_health_router(version: str) -> APIRouter:
    """Tạo `APIRouter` có `GET /health` trả `{"status": "ok", "version": version}`.

    Không tự gắn vào app nào; app gắn trong `entrypoints/api/`:
    `app.include_router(make_health_router(__version__))`.

    Args:
        version: Version của app (lấy từ `[project].version` lúc build) để công cụ vận hành
            so với version ghi khi cài.
    """
    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": version}

    return router
