"""Đọc và kiểm tra cấu hình `corekit` trong `pyproject.toml` của app."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from core_kit.cli.ports import CorekitError

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python 3.10
    import tomli as tomllib

TARGETS_TABLE = "[[tool.corekit.build.targets]]"
RELEASE_TABLE = "[tool.corekit.release]"
DEFAULT_HEALTH_PATH = "/health"

_TARGET_KEYS = {
    "name", "entry", "icon", "windowed", "onefile", "datas", "plugins", "copy", "extra_args",
}


@dataclass(frozen=True)
class BuildTarget:
    name: str
    entry: str = "main.py"
    icon: Optional[str] = None
    windowed: bool = False
    onefile: bool = False
    datas: Tuple[str, ...] = ()
    plugins: Tuple[str, ...] = ()
    copy: Tuple[str, ...] = ()
    extra_args: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Project:
    root: Path
    name: str
    version: str
    company: Optional[str]
    targets: Tuple[BuildTarget, ...]
    release_include: Tuple[str, ...]
    # Đường dẫn health ghi vào Manifest phát hành (`release.json`), công cụ cài ghép với port thành Health URL.
    health_path: str = DEFAULT_HEALTH_PATH

    @property
    def pyproject(self) -> Path:
        return self.root / "pyproject.toml"


def _str_list(value: Any, where: str) -> Tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise CorekitError(f"{where} phải là danh sách chuỗi.")
    return tuple(value)


def _opt_str(value: Any, where: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise CorekitError(f"{where} phải là chuỗi khác rỗng.")
    return value


def _health_path(value: Any, where: str) -> str:
    if value is None:
        return DEFAULT_HEALTH_PATH
    if not isinstance(value, str) or not value.startswith("/"):
        raise CorekitError(f"{where} phải là chuỗi bắt đầu bằng '/' (ví dụ '{DEFAULT_HEALTH_PATH}').")
    return value


def _bool(value: Any, where: str) -> bool:
    if value is None:
        return False
    if not isinstance(value, bool):
        raise CorekitError(f"{where} phải là true/false.")
    return value


def _parse_target(raw: Any, index: int) -> BuildTarget:
    where = f"{TARGETS_TABLE} thứ {index + 1}"
    if not isinstance(raw, dict):
        raise CorekitError(f"{where} không hợp lệ.")
    unknown = sorted(set(raw) - _TARGET_KEYS)
    if unknown:
        raise CorekitError(
            f"{where} có khóa không hỗ trợ: {', '.join(unknown)}. "
            f"Khóa hợp lệ: {', '.join(sorted(_TARGET_KEYS))}."
        )
    name = _opt_str(raw.get("name"), f"{where}: 'name'")
    if name is None:
        raise CorekitError(f"{where} thiếu 'name'.")
    where = f"Target '{name}'"
    return BuildTarget(
        name=name,
        entry=_opt_str(raw.get("entry"), f"{where}: 'entry'") or "main.py",
        icon=_opt_str(raw.get("icon"), f"{where}: 'icon'"),
        windowed=_bool(raw.get("windowed"), f"{where}: 'windowed'"),
        onefile=_bool(raw.get("onefile"), f"{where}: 'onefile'"),
        datas=_str_list(raw.get("datas"), f"{where}: 'datas'"),
        plugins=_str_list(raw.get("plugins"), f"{where}: 'plugins'"),
        copy=_str_list(raw.get("copy"), f"{where}: 'copy'"),
        extra_args=_str_list(raw.get("extra_args"), f"{where}: 'extra_args'"),
    )


def _table(data: Dict[str, Any], *keys: str) -> Dict[str, Any]:
    node: Any = data
    for key in keys:
        node = node.get(key, {}) if isinstance(node, dict) else {}
    return node if isinstance(node, dict) else {}


def load_project(root: Path) -> Project:
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        raise CorekitError(
            f"Không tìm thấy pyproject.toml trong {root}. Hãy chạy lệnh trong thư mục app (apps/<tên>/)."
        )
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise CorekitError(f"pyproject.toml không hợp lệ: {exc}") from exc

    project = _table(data, "project")
    name = project.get("name")
    version = project.get("version")
    if not isinstance(name, str) or not isinstance(version, str):
        raise CorekitError("pyproject.toml thiếu [project].name hoặc [project].version.")

    build = _table(data, "tool", "corekit", "build")
    raw_targets = build.get("targets")
    if not raw_targets:
        raise CorekitError(f"Chưa khai báo {TARGETS_TABLE} trong pyproject.toml.")
    if not isinstance(raw_targets, list):
        raise CorekitError(f"{TARGETS_TABLE} phải là mảng bảng (dùng [[...]]).")
    targets = tuple(_parse_target(raw, i) for i, raw in enumerate(raw_targets))
    names = [t.name for t in targets]
    duplicated = sorted({n for n in names if names.count(n) > 1})
    if duplicated:
        raise CorekitError(f"Tên target bị trùng: {', '.join(duplicated)}.")

    release = _table(data, "tool", "corekit", "release")
    return Project(
        root=root,
        name=name,
        version=version,
        company=_opt_str(build.get("company"), "[tool.corekit.build].company"),
        targets=targets,
        release_include=_str_list(release.get("include"), f"{RELEASE_TABLE}.include"),
        health_path=_health_path(release.get("health_path"), f"{RELEASE_TABLE}.health_path"),
    )
