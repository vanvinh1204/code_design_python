"""
Cổng ra ngoài của CLI `corekit`: menu, console, chạy tiến trình (Nuitka, git, uv, gh), tìm chương trình.

Mặc định dùng bản thật (`real_ports()`); test truyền bản giả vào `main(argv, ports)`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence


class CorekitError(Exception):
    """Lỗi người dùng/cấu hình: CLI in thông điệp và thoát mã 1, không in traceback."""


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class Ports:
    ask: Callable[[str], str]
    is_interactive: Callable[[], bool]
    echo: Callable[[str], None]
    # capture=False: in thẳng ra console (Nuitka build lâu); capture=True: thu stdout/stderr (git, gh).
    run: Callable[..., ProcessResult]
    which: Callable[[str], Optional[str]]
    python: str


def _run(cmd: Sequence[str], cwd: Path, capture: bool = False) -> ProcessResult:
    try:
        if capture:
            done = subprocess.run(
                list(cmd), cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            return ProcessResult(done.returncode, done.stdout or "", done.stderr or "")
        return ProcessResult(subprocess.run(list(cmd), cwd=cwd).returncode)
    except FileNotFoundError as exc:
        raise CorekitError(f"Không chạy được '{cmd[0]}': {exc}") from exc


def _is_interactive() -> bool:
    try:
        return sys.stdin is not None and sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False


def _echo(message: str = "") -> None:
    print(message, flush=True)


def real_ports() -> Ports:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    return Ports(
        ask=input,
        is_interactive=_is_interactive,
        echo=_echo,
        run=_run,
        which=shutil.which,
        python=sys.executable,
    )
