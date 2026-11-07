"""
CLI `corekit`: đóng gói app thành exe (Nuitka) và phát hành bản giao khách.

Cách dùng (trong thư mục app, ví dụ `apps/<tên>/`):
    uv run corekit build                 chọn chế độ / target qua menu
    uv run corekit build --fast          build nhanh (dev, thử chạy)
    uv run corekit build --release       build giao khách (LTO + deployment)
    uv run corekit build --target MyApp  chỉ build target MyApp (lặp được)
    uv run corekit release               kiểm git, nâng version, build, đóng zip, commit + tag
        --bump patch|minor|major|keep    chọn version không qua menu
        --publish / --no-publish         đẩy (hoặc không) lên GitHub Release không qua câu hỏi

Cấu hình đọc từ [[tool.corekit.build.targets]] và [tool.corekit.release] trong pyproject.toml.
Tuân thủ quy tắc dự án: không dùng argparse.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from core_kit.cli.build import FAST, MODE_LABELS, RELEASE, build_all
from core_kit.cli.menu import choose
from core_kit.cli.ports import CorekitError, Ports, real_ports
from core_kit.cli.project import BuildTarget, Project, load_project

__all__ = ["main"]


def _parse(args: Sequence[str], flags: Sequence[str], options: Sequence[str]) -> Tuple[set, Dict[str, List[str]]]:
    """Tách cờ (`--fast`) và tùy chọn có giá trị (`--target X` hoặc `--target=X`)."""
    seen: set = set()
    values: Dict[str, List[str]] = {}
    items = list(args)
    i = 0
    while i < len(items):
        arg = items[i]
        name, sep, inline = arg.partition("=")
        if name in options:
            if sep:
                value = inline
            else:
                i += 1
                if i >= len(items):
                    raise CorekitError(f"Thiếu giá trị cho {name}.")
                value = items[i]
            values.setdefault(name, []).append(value)
        elif arg in flags:
            seen.add(arg)
        else:
            raise CorekitError(f"Tham số không hỗ trợ: '{arg}'. Xem: corekit --help")
        i += 1
    return seen, values


def _pick_mode(seen: set, ports: Ports) -> str:
    if "--fast" in seen and "--release" in seen:
        raise CorekitError("Chỉ chọn một trong --fast hoặc --release.")
    if "--fast" in seen:
        return FAST
    if "--release" in seen:
        return RELEASE
    if not ports.is_interactive():
        raise CorekitError("Chạy không tương tác: hãy thêm --fast hoặc --release.")
    key = choose(
        ports,
        "Chọn chế độ build:",
        [("1", f"{MODE_LABELS[FAST]} (dev, thử chạy)"), ("2", f"{MODE_LABELS[RELEASE]} (LTO + deployment, chậm)")],
        default="2",
    )
    return FAST if key == "1" else RELEASE


def _pick_targets(project: Project, names: List[str], ports: Ports) -> List[BuildTarget]:
    by_name = {t.name: t for t in project.targets}
    if names:
        unknown = [n for n in names if n not in by_name]
        if unknown:
            raise CorekitError(
                f"Không có target: {', '.join(unknown)}. Target hợp lệ: {', '.join(by_name)}."
            )
        return [by_name[n] for n in dict.fromkeys(names)]
    if len(project.targets) < 2 or not ports.is_interactive():
        return list(project.targets)
    options = [("0", "Tất cả")] + [(str(i), t.name) for i, t in enumerate(project.targets, start=1)]
    key = choose(ports, "Chọn target:", options, default="0")
    return list(project.targets) if key == "0" else [project.targets[int(key) - 1]]


def _cmd_build(args: Sequence[str], ports: Ports) -> int:
    seen, values = _parse(args, flags=("--fast", "--release"), options=("--target",))
    project = load_project(Path.cwd())
    mode = _pick_mode(seen, ports)
    targets = _pick_targets(project, values.get("--target", []), ports)
    build_all(project, targets, mode, ports)
    return 0


def _cmd_release(args: Sequence[str], ports: Ports) -> int:
    from core_kit.cli.release import run_release

    seen, values = _parse(args, flags=("--publish", "--no-publish"), options=("--bump",))
    if "--publish" in seen and "--no-publish" in seen:
        raise CorekitError("Chỉ chọn một trong --publish hoặc --no-publish.")
    bump = values.get("--bump", [None])[-1]
    publish: Optional[bool] = True if "--publish" in seen else False if "--no-publish" in seen else None
    return run_release(load_project(Path.cwd()), bump, publish, ports)


def main(argv: Optional[Sequence[str]] = None, ports: Optional[Ports] = None) -> int:
    ports = ports or real_ports()
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        ports.echo(__doc__.strip() if __doc__ else "corekit")
        return 0
    command, rest = args[0], args[1:]
    if "-h" in rest or "--help" in rest:
        ports.echo(__doc__.strip() if __doc__ else "corekit")
        return 0
    try:
        if command == "build":
            return _cmd_build(rest, ports)
        if command == "release":
            return _cmd_release(rest, ports)
        raise CorekitError(f"Lệnh không hỗ trợ: '{command}'. Dùng: corekit build | corekit release")
    except CorekitError as exc:
        ports.echo(f"[LỖI] {exc}")
        return 1
    except KeyboardInterrupt:
        ports.echo("Đã hủy.")
        return 130


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
