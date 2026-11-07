"""
Phát hành thư viện core_kit: nâng version, chốt CHANGELOG, chạy test, commit, tag,
rồi hỏi mới push và tạo GitHub Release.

Cách dùng (mọi lựa chọn đều hỏi trong CLI, không có cờ):
    python tools/release.py

Quy trình:
    1. Kiểm: git sạch, đang ở nhánh main (không thì hỏi), tag core_kit-vX.Y.Z chưa có ở local/remote.
    2. Chọn patch / minor / major, chọn có chạy test không, xem tóm tắt rồi xác nhận.
    3. Ghi version vào pyproject.toml + src/core_kit/__init__.py; đổi mục [Unreleased] trong
       CHANGELOG.md thành [X.Y.Z] - <ngày>; chạy pytest. Lỗi ở bước này thì trả file về như cũ.
    4. Commit "chore(release): bump version to X.Y.Z" + tag core_kit-vX.Y.Z.
    5. Hỏi push (mặc định Không). Có gh thì tạo GitHub Release với ghi chú từ CHANGELOG.

Tuân thủ quy tắc dự án: KHÔNG SỬ DỤNG THƯ VIỆN ARGPARSE.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bump_version import calculate_next_version, get_current_version, update_init, update_pyproject  # noqa: E402

ROOT_DIR = Path(__file__).resolve().parent.parent
PACKAGE = "core_kit"
RELEASE_FILES = ("pyproject.toml", "src/core_kit/__init__.py", "CHANGELOG.md")
UNRELEASED_HEADING = "## [Unreleased]"
BUMPS = (("1", "patch"), ("2", "minor"), ("3", "major"))


class ReleaseError(Exception):
    """Lỗi người dùng/môi trường: in thông điệp và thoát mã 1, không in traceback."""


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class Ports:
    """Cổng ra ngoài: test truyền bản giả, `real_ports()` dùng bản thật."""

    ask: Callable[[str], str]
    echo: Callable[[str], None]
    # capture=True: thu stdout/stderr (git, gh); capture=False: in thẳng ra console (pytest).
    run: Callable[..., ProcessResult]
    which: Callable[[str], Optional[str]]
    python: str


# ---------------------------------------------------------------------------
# Cổng thật
# ---------------------------------------------------------------------------
def _run(cmd: Sequence[str], cwd: Path, capture: bool = False) -> ProcessResult:
    try:
        if capture:
            done = subprocess.run(
                list(cmd), cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            return ProcessResult(done.returncode, done.stdout or "", done.stderr or "")
        return ProcessResult(subprocess.run(list(cmd), cwd=cwd).returncode)
    except FileNotFoundError as exc:
        raise ReleaseError(f"Không chạy được '{cmd[0]}': {exc}") from exc


def _echo(message: str = "") -> None:
    print(message, flush=True)


def real_ports() -> Ports:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    return Ports(ask=input, echo=_echo, run=_run, which=shutil.which, python=sys.executable)


# ---------------------------------------------------------------------------
# Hỏi đáp trong CLI
# ---------------------------------------------------------------------------
def _ask(ports: Ports, prompt: str) -> str:
    try:
        return ports.ask(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        raise ReleaseError("Đã hủy.") from None


def choose(ports: Ports, title: str, options: Sequence[Tuple[str, str]], default: str) -> str:
    """Hiện menu `key) nhãn`, trả về key được chọn; Enter = `default`, nhập sai thì hỏi lại."""
    keys = [key for key, _ in options]
    ports.echo(title)
    for key, label in options:
        ports.echo(f"  {key}) {label}")
    while True:
        answer = _ask(ports, f"Lựa chọn [{default}]: ")
        if not answer:
            return default
        if answer in keys:
            return answer
        ports.echo(f"  Lựa chọn không hợp lệ: '{answer}'. Nhập một trong: {', '.join(keys)}.")


def confirm(ports: Ports, question: str, default: bool) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        answer = _ask(ports, f"{question} {hint}: ").lower()
        if not answer:
            return default
        if answer in ("y", "yes", "c", "co", "có"):
            return True
        if answer in ("n", "no", "k", "khong", "không"):
            return False
        ports.echo("  Trả lời y hoặc n.")


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------
def _detail(result: ProcessResult) -> str:
    return (result.stderr or result.stdout).strip()


class Git:
    def __init__(self, root: Path, ports: Ports) -> None:
        self.root = root
        self.ports = ports

    def __call__(self, *args: str) -> ProcessResult:
        return self.ports.run(["git", *args], self.root, capture=True)

    def must(self, *args: str) -> ProcessResult:
        result = self(*args)
        if result.returncode != 0:
            raise ReleaseError(f"git {' '.join(args)} lỗi (mã {result.returncode}): {_detail(result)}")
        return result


def tag_name(version: str) -> str:
    return f"{PACKAGE}-v{version}"


def check_worktree_clean(git: Git) -> None:
    status = git("status", "--porcelain")
    if status.returncode != 0:
        raise ReleaseError(f"Không đọc được trạng thái git: {_detail(status)}")
    if status.stdout.strip():
        raise ReleaseError("Working tree chưa sạch. Commit hoặc stash các thay đổi trước khi phát hành.")


def check_branch(git: Git, ports: Ports) -> None:
    branch = git.must("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if branch == "main":
        return
    ports.echo(f"Cảnh báo: đang ở nhánh '{branch}', không phải 'main'.")
    if not confirm(ports, "Vẫn phát hành từ nhánh này?", default=False):
        raise ReleaseError("Đã dừng. Chuyển sang nhánh main rồi chạy lại.")


def check_tag_free(tag: str, git: Git, ports: Ports) -> None:
    """Từ chối nếu tag đã có ở local hoặc remote; không kết nối được remote thì chỉ cảnh báo."""
    if git.must("tag", "-l", tag).stdout.strip():
        raise ReleaseError(f"Tag {tag} đã tồn tại ở local. Chọn version khác.")
    remotes = git("remote").stdout.split()
    if "origin" not in remotes:
        return
    result = git("ls-remote", "--tags", "origin", f"refs/tags/{tag}")
    if result.returncode != 0:
        ports.echo(f"Cảnh báo: không kiểm được tag trên remote origin ({_detail(result)}). Tiếp tục với tag local.")
    elif result.stdout.strip():
        raise ReleaseError(f"Tag {tag} đã có trên remote origin. Chọn version khác.")


# ---------------------------------------------------------------------------
# CHANGELOG
# ---------------------------------------------------------------------------
def _section_body(text: str, heading_start: int) -> str:
    body_start = text.find("\n", heading_start)
    body_start = len(text) if body_start == -1 else body_start + 1
    nxt = re.compile(r"^##\s", re.MULTILINE).search(text, body_start)
    return text[body_start: nxt.start() if nxt else len(text)]


def _strip_rules(body: str) -> str:
    """Bỏ các dòng `---` ngăn cách mục và khoảng trắng thừa."""
    lines = [line for line in body.splitlines() if line.strip() != "---"]
    return "\n".join(lines).strip()


def release_changelog(text: str, version: str, today: date) -> Tuple[str, bool]:
    """Đổi `## [Unreleased]` thành `## [version] - today`, chèn lại mục Unreleased trống phía trên.

    Trả về (nội dung mới, mục Unreleased có nội dung hay không).
    """
    match = re.compile(rf"^{re.escape(UNRELEASED_HEADING)}[ \t]*$", re.MULTILINE).search(text)
    if match is None:
        raise ReleaseError(f"CHANGELOG.md không có mục '{UNRELEASED_HEADING}'.")
    has_content = bool(_strip_rules(_section_body(text, match.start())))
    new_heading = f"{UNRELEASED_HEADING}\n\n---\n\n## [{version}] - {today.isoformat()}"
    return text[: match.start()] + new_heading + text[match.end():], has_content


def changelog_notes(text: str, version: str) -> Optional[str]:
    """Nội dung mục `## [version]` để làm ghi chú GitHub Release, None nếu trống."""
    match = re.compile(rf"^##\s*\[{re.escape(version)}\](\s|$)", re.MULTILINE).search(text)
    if match is None:
        return None
    return _strip_rules(_section_body(text, match.start())) or None


# ---------------------------------------------------------------------------
# Các bước ghi
# ---------------------------------------------------------------------------
def choose_version(current: str, ports: Ports) -> str:
    options = [(key, f"{kind:<5} -> {calculate_next_version(current, kind)}") for key, kind in BUMPS]
    key = choose(ports, f"Version hiện tại: {current}. Nâng lên:", options, default="1")
    kind = dict(BUMPS)[key]
    return calculate_next_version(current, kind)


def write_release_files(root: Path, version: str, today: date, ports: Ports) -> None:
    update_pyproject(version, root / "pyproject.toml")
    update_init(version, root / "src" / "core_kit" / "__init__.py")
    changelog = root / "CHANGELOG.md"
    new_text, has_content = release_changelog(changelog.read_text(encoding="utf-8"), version, today)
    changelog.write_text(new_text, encoding="utf-8")
    if not has_content:
        ports.echo("Cảnh báo: mục [Unreleased] trong CHANGELOG.md trống, mục mới sẽ không có nội dung.")
    ports.echo(f"Đã ghi version {version} vào: {', '.join(RELEASE_FILES)}")


def run_tests(root: Path, ports: Ports) -> None:
    ports.echo("Đang chạy pytest ...")
    result = ports.run([ports.python, "-m", "pytest", "-q"], root, capture=False)
    if result.returncode != 0:
        raise ReleaseError(f"pytest thất bại (mã {result.returncode}). Sửa test rồi chạy lại.")


def restore_release_files(git: Git, ports: Ports) -> None:
    result = git("checkout", "--", *RELEASE_FILES)
    if result.returncode != 0:
        ports.echo(f"Cảnh báo: không hoàn tác được file ({_detail(result)}). Kiểm tra bằng `git status`.")
    else:
        ports.echo("Đã trả pyproject.toml, __init__.py, CHANGELOG.md về nguyên trạng.")


def commit_and_tag(git: Git, version: str, ports: Ports) -> str:
    tag = tag_name(version)
    git.must("add", "--", *RELEASE_FILES)
    git.must("commit", "-m", f"chore(release): bump version to {version}")
    git.must("tag", "-a", tag, "-m", f"Release {PACKAGE} v{version}")
    ports.echo(f"Đã commit và tạo tag {tag}.")
    return tag


def _manual_push_hint(tag: str) -> str:
    return f"Push tay: git push origin HEAD && git push origin {tag}"


def publish(root: Path, version: str, tag: str, git: Git, ports: Ports) -> None:
    git.must("push", "origin", "HEAD")
    git.must("push", "origin", tag)
    ports.echo(f"Đã push nhánh hiện tại và tag {tag} lên origin.")
    if ports.which("gh") is None:
        ports.echo(
            "Chưa cài GitHub CLI (gh) nên không tạo GitHub Release tự động.\n"
            f"Tạo tay trên GitHub: Releases -> Draft a new release -> chọn tag {tag}, "
            f"dán nội dung mục [{version}] trong CHANGELOG.md vào ghi chú."
        )
        return
    cmd = ["gh", "release", "create", tag, "--title", f"{PACKAGE} v{version}"]
    notes = changelog_notes((root / "CHANGELOG.md").read_text(encoding="utf-8"), version)
    with tempfile.TemporaryDirectory(prefix="core-kit-notes-") as tmp:
        if notes:
            notes_file = Path(tmp) / "notes.md"
            notes_file.write_text(notes + "\n", encoding="utf-8")
            cmd += ["--notes-file", str(notes_file)]
        else:
            cmd.append("--generate-notes")
        result = ports.run(cmd, root, capture=True)
    if result.returncode != 0:
        raise ReleaseError(f"gh release create lỗi (mã {result.returncode}): {_detail(result)}")
    ports.echo(f"Đã tạo GitHub Release {tag}. {result.stdout.strip()}".rstrip())


def _print_plan(current: str, version: str, tag: str, with_tests: bool, today: date, ports: Ports) -> None:
    ports.echo("")
    ports.echo("=" * 60)
    ports.echo(f"  PHÁT HÀNH {PACKAGE}: {current} -> {version}")
    ports.echo("=" * 60)
    ports.echo(f"  File sẽ sửa : {', '.join(RELEASE_FILES)}")
    ports.echo(f"  CHANGELOG   : [Unreleased] -> [{version}] - {today.isoformat()}")
    ports.echo(f"  Chạy test   : {'có' if with_tests else 'không'}")
    ports.echo(f"  Commit      : chore(release): bump version to {version}")
    ports.echo(f"  Tag         : {tag}")
    ports.echo("  Push        : hỏi sau khi tag xong")
    ports.echo("=" * 60)


def run_release(root: Path, ports: Ports, today: Optional[date] = None) -> int:
    today = today or date.today()
    if ports.which("git") is None:
        raise ReleaseError("Không tìm thấy git.")
    git = Git(root, ports)

    check_worktree_clean(git)
    check_branch(git, ports)

    current = get_current_version(root / "pyproject.toml")
    version = choose_version(current, ports)
    tag = tag_name(version)
    check_tag_free(tag, git, ports)
    with_tests = confirm(ports, "Chạy pytest trước khi commit?", default=True)

    _print_plan(current, version, tag, with_tests, today, ports)
    if not confirm(ports, "Thực hiện?", default=True):
        raise ReleaseError("Đã hủy, chưa sửa gì.")

    try:
        write_release_files(root, version, today, ports)
        if with_tests:
            run_tests(root, ports)
    except ReleaseError:
        restore_release_files(git, ports)
        raise

    commit_and_tag(git, version, ports)

    if not confirm(ports, "Push lên origin (và tạo GitHub Release nếu có gh)?", default=False):
        ports.echo(f"Chưa push. {_manual_push_hint(tag)}")
        return 0
    try:
        publish(root, version, tag, git, ports)
    except ReleaseError as exc:
        raise ReleaseError(f"{exc}\nCommit và tag {tag} vẫn ở local. {_manual_push_hint(tag)}") from None
    return 0


def main() -> int:
    ports = real_ports()
    try:
        return run_release(ROOT_DIR, ports)
    except ReleaseError as exc:
        ports.echo(f"[LỖI] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
