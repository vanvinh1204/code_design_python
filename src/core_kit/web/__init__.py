"""
core_kit.web: Tiện ích dùng chung cho app server FastAPI.

Cần extra `web` (`pip install core_kit[web]`). Hiện cung cấp `make_health_router`:
router `GET /health` để công cụ vận hành (nssm_manager) biết web còn trả lời và đang chạy bản nào.
"""

from __future__ import annotations

try:
    import fastapi  # noqa: F401
except ImportError:
    raise ImportError(
        "Thư viện 'fastapi' chưa được cài đặt. Vui lòng cài đặt qua 'pip install fastapi>=0.110' "
        "hoặc 'pip install core_kit[web]'."
    )

from core_kit.web.health import make_health_router

__all__ = ["make_health_router"]
