"""`corekit build`: build từng target bằng Nuitka ra `build/<chế độ>/<name>/`, bấm exe là chạy."""

from __future__ import annotations

import os
import re
import shutil
import time
from pathlib import Path
from typing import List, Sequence

from core_kit.cli.ports import CorekitError, Ports
from core_kit.cli.project import BuildTarget, Project

FAST = "fast"
RELEASE = "release"
MODE_LABELS = {FAST: "Nhanh", RELEASE: "Giao khách"}
# Thư mục runtime theo chuẩn dự án: app tự tạo khi chạy, không bao giờ đóng gói.
RUNTIME_FOLDERS = ("data", "logs", "secrets")


def output_dir(project: Project, target: BuildTarget, mode: str) -> Path:
    return project.root / "build" / mode / target.name


def _staging_dir(project: Project, target: BuildTarget, mode: str) -> Path:
    return project.root / "build" / mode / ".staging" / target.name


def numeric_version(version: str) -> str:
    """Nuitka chỉ nhận tối đa 4 số: `0.3.0rc1` → `0.3.0`."""
    match = re.match(r"^\d+(?:\.\d+){0,3}", version.strip())
    if not match:
        raise CorekitError(f"[project].version '{version}' không bắt đầu bằng số (X.Y.Z).")
    return match.group(0)


def _rel(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def _existing(project: Project, rel_path: str, what: str) -> Path:
    path = project.root / rel_path
    if not path.exists():
        raise CorekitError(f"{what}: không tìm thấy '{rel_path}' trong {project.root}.")
    return path


def validate_target(project: Project, target: BuildTarget) -> None:
    """Kiểm mọi đường dẫn khai báo trước khi gọi Nuitka (build lâu, lỗi cấu hình phải báo sớm)."""
    where = f"Target '{target.name}'"
    entry = _existing(project, target.entry, f"{where}: entry")
    if not entry.is_file():
        raise CorekitError(f"{where}: entry '{target.entry}' không phải file.")
    if target.icon:
        _existing(project, target.icon, f"{where}: icon")
    for field, items in (("datas", target.datas), ("copy", target.copy)):
        for item in items:
            top = _rel(item).split("/")[0].lower()
            if top in RUNTIME_FOLDERS:
                raise CorekitError(
                    f"{where}: {field} không được chứa '{item}' — {', '.join(RUNTIME_FOLDERS)} là thư mục "
                    "runtime (app tự tạo khi chạy), không đóng gói để tránh lộ dữ liệu/bí mật."
                )
            _existing(project, item, f"{where}: {field}")


def nuitka_command(
    project: Project, target: BuildTarget, mode: str, staging: Path, python: str
) -> List[str]:
    version = numeric_version(project.version)
    if mode == FAST:
        mode_args = ["--lto=no", "--windows-console-mode=attach"]
    else:
        console = "disable" if target.windowed else "force"
        mode_args = ["--lto=yes", "--deployment", f"--windows-console-mode={console}"]

    cmd = [
        python, "-m", "nuitka",
        f"--mode={'onefile' if target.onefile else 'standalone'}",
        "--assume-yes-for-downloads",
        "--remove-output",
        f"--jobs={os.cpu_count() or 1}",
        f"--output-dir={staging}",
        f"--output-filename={target.name}.exe",
        f"--product-name={target.name}",
        f"--product-version={version}",
        f"--file-version={version}",
        *mode_args,
    ]
    if project.company:
        cmd.append(f"--company-name={project.company}")
    if target.icon:
        cmd.append(f"--windows-icon-from-ico={project.root / target.icon}")
    for plugin in target.plugins:
        cmd.append(f"--enable-plugins={plugin}")
    for item in target.datas:
        src = project.root / item
        flag = "--include-data-dir" if src.is_dir() else "--include-data-files"
        cmd.append(f"{flag}={src}={_rel(item)}")
    cmd.extend(target.extra_args)
    cmd.append(str(project.root / target.entry))
    return cmd


def _copy_into(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dest, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dest)


def _folder_size(folder: Path) -> int:
    return sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())


def build_target(project: Project, target: BuildTarget, mode: str, ports: Ports) -> Path:
    out = output_dir(project, target, mode)
    staging = _staging_dir(project, target, mode)
    for folder in (out, staging):
        if folder.exists():
            shutil.rmtree(folder)

    ports.echo(f"==> Build '{target.name}' (chế độ {MODE_LABELS[mode]})")
    started = time.monotonic()
    cmd = nuitka_command(project, target, mode, staging, ports.python)
    result = ports.run(cmd, project.root, capture=False)
    if result.returncode != 0:
        raise CorekitError(f"Nuitka lỗi khi build target '{target.name}' (mã {result.returncode}).")

    if target.onefile:
        produced = staging / f"{target.name}.exe"
        if not produced.is_file():
            raise CorekitError(f"Không thấy kết quả Nuitka: {produced}")
        out.mkdir(parents=True)
        shutil.move(str(produced), str(out / produced.name))
    else:
        produced = staging / f"{Path(target.entry).stem}.dist"
        if not produced.is_dir():
            raise CorekitError(f"Không thấy kết quả Nuitka: {produced}")
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(produced), str(out))
    shutil.rmtree(staging, ignore_errors=True)
    staging_root = staging.parent
    if staging_root.is_dir() and not any(staging_root.iterdir()):
        staging_root.rmdir()

    env_file = project.root / ".env"
    env_example = project.root / ".env.example"
    if env_file.is_file():
        shutil.copy2(env_file, out / ".env")
    elif env_example.is_file():
        shutil.copy2(env_example, out / ".env.example")
        ports.echo("    Cảnh báo: app chưa có .env, đã chép .env.example — sửa cấu hình trước khi chạy.")
    else:
        ports.echo("    Cảnh báo: app không có .env lẫn .env.example.")

    for item in target.copy:
        _copy_into(project.root / item, out / _rel(item))

    elapsed = time.monotonic() - started
    size_mb = _folder_size(out) / (1024 * 1024)
    ports.echo(f"    Xong: {out}  ({size_mb:.1f} MB, {elapsed:.0f} giây)")
    return out


def build_all(project: Project, targets: Sequence[BuildTarget], mode: str, ports: Ports) -> List[Path]:
    for target in targets:
        validate_target(project, target)
    return [build_target(project, target, mode, ports) for target in targets]
