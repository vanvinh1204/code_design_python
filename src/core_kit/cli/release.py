"""
`corekit release`: phát hành Bản giao khách.

Trình tự: git sạch → chọn version → kiểm .env.example / include / CHANGELOG → ghi version
→ build giao khách mọi target → zip từng target → commit + tag `<app>-vX.Y.Z`
→ (hỏi) push + GitHub Release để lưu trữ. Lỗi trước khi commit thì trả lại pyproject.toml/uv.lock.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import List, Optional

from core_kit.cli.build import RELEASE, build_all, output_dir, validate_target
from core_kit.cli.menu import choose, confirm
from core_kit.cli.ports import CorekitError, Ports, ProcessResult
from core_kit.cli.project import BuildTarget, Project

PLATFORM = "win-x64"
BUMPS = ("patch", "minor", "major", "keep")


def next_version(current: str, bump: str) -> str:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", current.strip())
    if not match:
        raise CorekitError(f"[project].version '{current}' không đúng dạng X.Y.Z.")
    major, minor, patch = (int(g) for g in match.groups())
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "keep":
        return current
    raise CorekitError(f"--bump '{bump}' không hợp lệ. Chọn: {', '.join(BUMPS)}.")


def write_project_version(text: str, new_version: str) -> str:
    """Thay `version = "..."` trong bảng [project], giữ nguyên phần còn lại của file."""
    lines = text.splitlines(keepends=True)
    in_project = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("["):
            in_project = stripped == "[project]"
            continue
        if in_project:
            match = re.match(r'^(\s*version\s*=\s*)(["\'])[^"\']*\2', line)
            if match:
                lines[i] = f'{match.group(1)}"{new_version}"' + line[match.end():]
                return "".join(lines)
    raise CorekitError("Không tìm thấy dòng version trong bảng [project] của pyproject.toml.")


def changelog_section(changelog: Path, version: str) -> Optional[str]:
    """Nội dung mục `## [X.Y.Z]` của CHANGELOG (Keep a Changelog), None nếu không có."""
    if not changelog.is_file():
        return None
    text = changelog.read_text(encoding="utf-8")
    heading = re.compile(rf"^##\s*\[?{re.escape(version)}\]?(\s|$)", re.MULTILINE)
    match = heading.search(text)
    if not match:
        return None
    body_start = text.find("\n", match.start())
    body_start = len(text) if body_start == -1 else body_start + 1
    nxt = re.compile(r"^##\s", re.MULTILINE).search(text, body_start)
    body = text[body_start: nxt.start() if nxt else len(text)].strip()
    return body.rstrip("-").strip() or None


def zip_name(target: BuildTarget, version: str) -> str:
    return f"{target.name}-{version}-{PLATFORM}.zip"


def package_target(project: Project, target: BuildTarget) -> Path:
    """Đóng Bản giao khách: thư mục gốc `<name>-<version>/`, không .env, luôn có .env.example."""
    src = output_dir(project, target, RELEASE)
    folder = f"{target.name}-{project.version}"
    dist = project.root / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    zip_path = dist / zip_name(target, project.version)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(src.rglob("*")):
            rel = file.relative_to(src).as_posix()
            if file.is_file() and rel not in (".env", ".env.example"):
                archive.write(file, f"{folder}/{rel}")
        archive.write(project.root / ".env.example", f"{folder}/.env.example")
        for item in project.release_include:
            path = project.root / item
            if path.is_dir():
                for file in sorted(path.rglob("*")):
                    if file.is_file():
                        archive.write(file, f"{folder}/{path.name}/{file.relative_to(path).as_posix()}")
            else:
                archive.write(path, f"{folder}/{path.name}")
    return zip_path


class _Git:
    def __init__(self, project: Project, ports: Ports) -> None:
        self.root = project.root
        self.ports = ports

    def __call__(self, *args: str) -> ProcessResult:
        return self.ports.run(["git", *args], self.root, capture=True)

    def must(self, *args: str) -> ProcessResult:
        result = self(*args)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise CorekitError(f"git {' '.join(args)} lỗi (mã {result.returncode}): {detail}")
        return result


def _choose_bump(project: Project, bump: Optional[str], ports: Ports) -> str:
    if bump is not None:
        if bump not in BUMPS:
            raise CorekitError(f"--bump '{bump}' không hợp lệ. Chọn: {', '.join(BUMPS)}.")
        return bump
    if not ports.is_interactive():
        raise CorekitError("Chạy không tương tác: hãy thêm --bump patch|minor|major|keep.")
    current = project.version
    options = [
        ("1", f"patch → {next_version(current, 'patch')}"),
        ("2", f"minor → {next_version(current, 'minor')}"),
        ("3", f"major → {next_version(current, 'major')}"),
        ("4", f"giữ nguyên {current} (chỉ khi chưa có tag này)"),
    ]
    key = choose(ports, f"Version hiện tại: {current}", options, default="1")
    return BUMPS[int(key) - 1]


def _check_inputs(project: Project, version: str, ports: Ports) -> None:
    if not (project.root / ".env.example").is_file():
        raise CorekitError("App thiếu .env.example — Bản giao khách bắt buộc kèm file mẫu cấu hình này.")
    for item in project.release_include:
        if not (project.root / item).exists():
            raise CorekitError(f"[tool.corekit.release].include: không tìm thấy '{item}'.")
    for target in project.targets:
        validate_target(project, target)
    changelog = project.root / "CHANGELOG.md"
    if changelog.is_file() and changelog_section(changelog, version) is None:
        ports.echo(f"Cảnh báo: CHANGELOG.md chưa có mục [{version}].")
        if ports.is_interactive() and not confirm(ports, "Vẫn tiếp tục phát hành?", default=True):
            raise CorekitError("Đã dừng để cập nhật CHANGELOG.md.")


def _publish(project: Project, tag: str, zips: List[Path], git: _Git, ports: Ports) -> None:
    if ports.which("gh") is None:
        raise CorekitError(
            "Chưa cài GitHub CLI (gh) nên không tạo được GitHub Release. "
            f"Commit và tag {tag} vẫn ở máy; push tay: git push origin HEAD && git push origin {tag}"
        )
    git.must("push", "origin", "HEAD")
    git.must("push", "origin", tag)
    cmd = ["gh", "release", "create", tag, *[str(z) for z in zips], "--title", f"{project.name} v{project.version}"]
    notes = changelog_section(project.root / "CHANGELOG.md", project.version)
    cmd += ["--notes", notes] if notes else ["--generate-notes"]
    result = ports.run(cmd, project.root, capture=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise CorekitError(f"gh release create lỗi (mã {result.returncode}): {detail}")
    ports.echo(f"Đã tạo GitHub Release {tag}. {result.stdout.strip()}".rstrip())


def run_release(project: Project, bump: Optional[str], publish: Optional[bool], ports: Ports) -> int:
    if ports.which("git") is None:
        raise CorekitError("Không tìm thấy git.")
    git = _Git(project, ports)
    status = git("status", "--porcelain")
    if status.returncode != 0:
        raise CorekitError(f"Không đọc được trạng thái git: {(status.stderr or status.stdout).strip()}")
    if status.stdout.strip():
        raise CorekitError("Git còn thay đổi chưa commit. Commit hoặc stash trước khi phát hành.")

    new_version = next_version(project.version, _choose_bump(project, bump, ports))
    tag = f"{project.name}-v{new_version}"
    if git.must("tag", "-l", tag).stdout.strip():
        raise CorekitError(f"Tag {tag} đã tồn tại. Chọn version khác.")
    _check_inputs(project, new_version, ports)

    pyproject = project.pyproject
    lock = project.root / "uv.lock"
    original_pyproject = pyproject.read_bytes()
    original_lock = lock.read_bytes() if lock.is_file() else None
    released = replace(project, version=new_version)
    zips: List[Path] = []
    changed = new_version != project.version
    try:
        if changed:
            text = original_pyproject.decode("utf-8")
            pyproject.write_bytes(write_project_version(text, new_version).encode("utf-8"))
            if original_lock is not None:
                locked = ports.run(["uv", "lock"], project.root, capture=True)
                if locked.returncode != 0:
                    raise CorekitError(f"uv lock lỗi: {(locked.stderr or locked.stdout).strip()}")
        build_all(released, released.targets, RELEASE, ports)
        for target in released.targets:
            zips.append(package_target(released, target))
        if changed:
            git.must("add", "pyproject.toml", *(["uv.lock"] if original_lock is not None else []))
            git.must("commit", "-m", f"chore(release): {project.name} v{new_version}")
    except BaseException:
        pyproject.write_bytes(original_pyproject)
        if original_lock is not None:
            lock.write_bytes(original_lock)
        for z in zips:
            z.unlink(missing_ok=True)
        ports.echo("Phát hành thất bại: đã trả pyproject.toml/uv.lock về như cũ, không commit, không tag.")
        raise
    git.must("tag", "-a", tag, "-m", f"Release {project.name} v{new_version}")

    ports.echo(f"Đã phát hành {project.name} v{new_version} (tag {tag}):")
    for z in zips:
        ports.echo(f"    {z}")

    if publish is None:
        publish = ports.is_interactive() and confirm(
            ports, "Push commit + tag và tạo GitHub Release?", default=False
        )
    if publish:
        _publish(released, tag, zips, git, ports)
    else:
        ports.echo("Chưa push. Khi cần: git push origin HEAD && git push origin " + tag)
    return 0
