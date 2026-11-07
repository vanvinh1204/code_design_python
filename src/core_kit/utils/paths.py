"""
Nhận diện môi trường chạy (dev / bản đóng gói) và các thư mục gốc của app.

- ``app_dir()``: thư mục chứa file exe — nơi đặt các thứ khách sửa/thay được
  (``.env``, ``models/``, ``logs/``, các mục ``copy`` của ``corekit build``).
- ``bundle_dir()``: thư mục chứa dữ liệu chỉ đọc gom kèm (``datas``). Với Nuitka
  onefile/PyInstaller onefile, đây là thư mục giải nén tạm, khác ``app_dir()``.

Khi chạy dev (``py main.py`` trong ``apps/<tên>/``) cả hai đều là thư mục hiện tại.
Hỗ trợ Nuitka (standalone, onefile) và PyInstaller (onedir, onefile).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional


def _nuitka_compiled() -> Optional[Any]:
    """Trả về ``__compiled__`` mà Nuitka gắn vào module đã biên dịch, hoặc None khi chạy Python thường."""
    return globals().get("__compiled__")


def _pyinstaller_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def is_packaged() -> bool:
    """True khi đang chạy từ exe đóng gói (Nuitka hoặc PyInstaller)."""
    return _nuitka_compiled() is not None or _pyinstaller_frozen()


def _executable_dir() -> Path:
    return Path(sys.executable).resolve().parent


def app_dir() -> Path:
    """Thư mục chứa file exe; khi chạy dev là thư mục hiện tại."""
    compiled = _nuitka_compiled()
    if compiled is not None:
        if getattr(compiled, "onefile", False):
            # Onefile: sys.executable nằm trong thư mục giải nén tạm; containing_dir là nơi đặt file exe.
            return Path(compiled.containing_dir).resolve()
        return _executable_dir()
    if _pyinstaller_frozen():
        return _executable_dir()
    return Path.cwd()


def bundle_dir() -> Path:
    """Thư mục chứa dữ liệu gom kèm bản build (``datas``); khi chạy dev là thư mục hiện tại."""
    if _nuitka_compiled() is not None:
        return _executable_dir()
    if _pyinstaller_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        return Path(meipass).resolve() if meipass else _executable_dir()
    return Path.cwd()
