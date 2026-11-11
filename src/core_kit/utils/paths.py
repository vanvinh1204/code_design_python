"""
Nhận diện môi trường chạy (dev / bản đóng gói) và các thư mục gốc của app.

- ``app_dir()`` (App Dir): thư mục chứa file exe — nơi cài app, đặt những thứ khách
  sửa/thay được và đi kèm bản cài (``.env``, ``models/``, các mục ``copy`` của
  ``corekit build``).
- ``data_dir()`` (Data Dir): thư mục dữ liệu sinh lúc chạy (``logs/``, SQLite, upload...).
  Là biến môi trường ``DATA_DIR`` nếu được đặt (tự tạo thư mục nếu chưa có), không thì
  trùng ``app_dir()``. Khác App Dir ở chỗ App Dir là nơi cài, có thể không ghi được với
  tài khoản thường (ví dụ ``%ProgramFiles%`` khi chạy dưới Windows service), còn Data Dir
  luôn là nơi app được phép ghi. Chạy dev, chạy exe tay, chạy dưới service đều một đường code.
- ``bundle_dir()`` (Bundle Dir): thư mục chứa dữ liệu chỉ đọc gom kèm (``datas``). Với Nuitka
  onefile/PyInstaller onefile, đây là thư mục giải nén tạm, khác ``app_dir()``.

Khi chạy dev (``uv run main.py`` trong ``apps/<tên>/``) cả ba đều là thư mục hiện tại
(trừ khi đặt ``DATA_DIR``). Hỗ trợ Nuitka (standalone, onefile) và PyInstaller (onedir, onefile).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

DATA_DIR_ENV_VAR = "DATA_DIR"


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


def data_dir() -> Path:
    """Thư mục dữ liệu sinh lúc chạy: ``DATA_DIR`` nếu biến môi trường có giá trị (tự tạo nếu chưa có), không thì ``app_dir()``."""
    raw = os.environ.get(DATA_DIR_ENV_VAR, "").strip()
    if not raw:
        return app_dir()
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


def bundle_dir() -> Path:
    """Thư mục chứa dữ liệu gom kèm bản build (``datas``); khi chạy dev là thư mục hiện tại."""
    if _nuitka_compiled() is not None:
        return _executable_dir()
    if _pyinstaller_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        return Path(meipass).resolve() if meipass else _executable_dir()
    return Path.cwd()
