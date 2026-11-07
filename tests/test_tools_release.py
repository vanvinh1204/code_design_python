"""Kiểm thử `tools/release.py`: tiên quyết git, chọn version, CHANGELOG, test, rollback, commit/tag, push."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union

import pytest

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import release  # noqa: E402
from release import Ports, ProcessResult, ReleaseError, run_release  # noqa: E402

Handler = Union[ProcessResult, Callable[[List[str]], ProcessResult]]
PYTHON = "C:/kit/.venv/Scripts/python.exe"
TODAY = date(2026, 11, 7)

CHANGELOG = """# Changelog

Mô tả.

---

## [Unreleased]

### Đã thêm (Added)
- Tính năng A.

### Đã thay đổi (Changed)
- Sửa B.

---

## [0.2.0] - 2026-10-29

### Đã thêm (Added)
- Bản đầu.
"""

CHANGELOG_EMPTY = """# Changelog

## [Unreleased]

---

## [0.2.0] - 2026-10-29
- Bản đầu.
"""


class FakeEnv:
    """Cổng giả: ghi lại lệnh và prompt, trả kết quả theo handler khớp tiền tố dài nhất."""

    def __init__(
        self,
        answers: Sequence[str] = (),
        *,
        dirty: str = "",
        branch: str = "main",
        local_tags: Sequence[str] = (),
        remote_tags: Sequence[str] = (),
        remote_rc: int = 0,
        pytest_rc: int = 0,
        installed: Sequence[str] = ("git", "gh"),
        handlers: Optional[Dict[Tuple[str, ...], Handler]] = None,
    ) -> None:
        self.answers = list(answers)
        self.installed = set(installed)
        self.lines: List[str] = []
        self.prompts: List[str] = []
        self.commands: List[List[str]] = []
        self.handlers: Dict[Tuple[str, ...], Handler] = {
            ("git", "status", "--porcelain"): ProcessResult(0, dirty),
            ("git", "rev-parse", "--abbrev-ref", "HEAD"): ProcessResult(0, f"{branch}\n"),
            ("git", "tag", "-l"): lambda cmd: ProcessResult(0, f"{cmd[3]}\n" if cmd[3] in local_tags else ""),
            ("git", "remote"): ProcessResult(0, "origin\n"),
            ("git", "ls-remote"): lambda cmd: ProcessResult(
                remote_rc, "" if remote_rc else ("abc\t" + cmd[4] if cmd[4].split("/")[-1] in remote_tags else ""), "no network" if remote_rc else ""
            ),
            (PYTHON, "-m", "pytest"): ProcessResult(pytest_rc),
            ("gh", "release", "create"): ProcessResult(0, "https://github.com/x/y/releases/tag/t\n"),
        }
        self.handlers.update(handlers or {})

    def ask(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.answers:
            raise EOFError
        return self.answers.pop(0)

    def echo(self, message: str = "") -> None:
        self.lines.append(message)

    def which(self, program: str) -> Optional[str]:
        return f"C:/bin/{program}.exe" if program in self.installed else None

    def run(self, cmd: Sequence[str], cwd: Path, capture: bool = False) -> ProcessResult:
        cmd = list(cmd)
        self.commands.append(cmd)
        best: Optional[Tuple[str, ...]] = None
        for prefix in self.handlers:
            if tuple(cmd[: len(prefix)]) == prefix and (best is None or len(prefix) > len(best)):
                best = prefix
        if best is None:
            return ProcessResult(0)
        handler = self.handlers[best]
        return handler(cmd) if callable(handler) else handler

    @property
    def ports(self) -> Ports:
        return Ports(ask=self.ask, echo=self.echo, run=self.run, which=self.which, python=PYTHON)

    def commands_starting(self, *prefix: str) -> List[List[str]]:
        return [c for c in self.commands if tuple(c[: len(prefix)]) == prefix]

    @property
    def output(self) -> str:
        return "\n".join(self.lines)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "core_kit"\nversion = "0.2.0"\n', encoding="utf-8"
    )
    pkg = tmp_path / "src" / "core_kit"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text('"""core_kit"""\n\n__version__ = "0.2.0"\n', encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
    return tmp_path


def _version(repo: Path) -> Tuple[str, str]:
    import re

    py = re.search(r'^version = "([^"]+)"', (repo / "pyproject.toml").read_text(encoding="utf-8"), re.M)
    init = re.search(r'^__version__ = "([^"]+)"', (repo / "src/core_kit/__init__.py").read_text(encoding="utf-8"), re.M)
    return py.group(1), init.group(1)


# Trả lời theo thứ tự: chọn bump, chạy test?, thực hiện?, push?
ANSWERS_MINOR_NO_PUSH = ["2", "", "", ""]


# ---------------------------------------------------------------------------
# Hàm thuần: CHANGELOG
# ---------------------------------------------------------------------------
def test_release_changelog_moves_unreleased_into_new_version():
    text, has_content = release.release_changelog(CHANGELOG, "0.3.0", TODAY)
    assert has_content
    assert "## [Unreleased]\n\n---\n\n## [0.3.0] - 2026-11-07\n\n### Đã thêm (Added)\n- Tính năng A." in text
    assert text.count("## [Unreleased]") == 1
    assert "## [0.2.0] - 2026-10-29" in text


def test_release_changelog_reports_empty_unreleased():
    text, has_content = release.release_changelog(CHANGELOG_EMPTY, "0.3.0", TODAY)
    assert not has_content
    assert "## [Unreleased]\n\n---\n\n## [0.3.0] - 2026-11-07\n\n---\n\n## [0.2.0]" in text


def test_release_changelog_requires_unreleased_heading():
    with pytest.raises(ReleaseError, match="Unreleased"):
        release.release_changelog("# Changelog\n\n## [0.2.0]\n", "0.3.0", TODAY)


def test_changelog_notes_strips_rules_and_returns_none_when_empty():
    text, _ = release.release_changelog(CHANGELOG, "0.3.0", TODAY)
    notes = release.changelog_notes(text, "0.3.0")
    assert notes.startswith("### Đã thêm (Added)")
    assert "- Sửa B." in notes
    assert "---" not in notes
    assert release.changelog_notes(text, "0.9.9") is None
    empty, _ = release.release_changelog(CHANGELOG_EMPTY, "0.3.0", TODAY)
    assert release.changelog_notes(empty, "0.3.0") is None


# ---------------------------------------------------------------------------
# Luồng chính
# ---------------------------------------------------------------------------
def test_happy_path_bumps_tests_commits_tags_without_push(repo):
    env = FakeEnv(ANSWERS_MINOR_NO_PUSH)
    assert run_release(repo, env.ports, TODAY) == 0

    assert _version(repo) == ("0.3.0", "0.3.0")
    changelog = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [0.3.0] - 2026-11-07" in changelog
    assert "## [Unreleased]\n\n---\n\n## [0.3.0]" in changelog

    assert env.commands_starting(PYTHON, "-m", "pytest", "-q")
    assert env.commands_starting("git", "add", "--", "pyproject.toml", "src/core_kit/__init__.py", "CHANGELOG.md")
    assert ["git", "commit", "-m", "chore(release): bump version to 0.3.0"] in env.commands
    assert ["git", "tag", "-a", "core_kit-v0.3.0", "-m", "Release core_kit v0.3.0"] in env.commands
    assert not env.commands_starting("git", "push")
    assert not env.commands_starting("gh")
    assert "git push origin HEAD && git push origin core_kit-v0.3.0" in env.output
    assert "0.2.0 -> 0.3.0" in env.output


def test_menu_shows_all_three_bumps_and_default_is_patch(repo):
    env = FakeEnv(["", "", "", ""])
    run_release(repo, env.ports, TODAY)
    assert _version(repo) == ("0.2.1", "0.2.1")
    assert "patch -> 0.2.1" in env.output
    assert "minor -> 0.3.0" in env.output
    assert "major -> 1.0.0" in env.output


def test_skipping_tests_does_not_run_pytest(repo):
    env = FakeEnv(["2", "n", "", ""])
    run_release(repo, env.ports, TODAY)
    assert not env.commands_starting(PYTHON, "-m", "pytest")
    assert "Chạy test   : không" in env.output
    assert env.commands_starting("git", "commit")


def test_declining_plan_changes_nothing(repo):
    env = FakeEnv(["2", "", "n"])
    with pytest.raises(ReleaseError, match="chưa sửa gì"):
        run_release(repo, env.ports, TODAY)
    assert _version(repo) == ("0.2.0", "0.2.0")
    assert "## [0.3.0]" not in (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert not env.commands_starting("git", "commit")


# ---------------------------------------------------------------------------
# Tiên quyết
# ---------------------------------------------------------------------------
def test_dirty_worktree_is_refused_before_asking_anything(repo):
    env = FakeEnv(ANSWERS_MINOR_NO_PUSH, dirty=" M src/core_kit/x.py\n")
    with pytest.raises(ReleaseError, match="chưa sạch"):
        run_release(repo, env.ports, TODAY)
    assert env.prompts == []
    assert _version(repo) == ("0.2.0", "0.2.0")


def test_missing_git_is_refused(repo):
    env = FakeEnv(ANSWERS_MINOR_NO_PUSH, installed=())
    with pytest.raises(ReleaseError, match="git"):
        run_release(repo, env.ports, TODAY)


def test_other_branch_asks_and_default_stops(repo):
    env = FakeEnv([""], branch="feature/x")
    with pytest.raises(ReleaseError, match="nhánh main"):
        run_release(repo, env.ports, TODAY)
    assert "đang ở nhánh 'feature/x'" in env.output
    assert _version(repo) == ("0.2.0", "0.2.0")


def test_other_branch_can_continue_when_confirmed(repo):
    env = FakeEnv(["y", *ANSWERS_MINOR_NO_PUSH], branch="feature/x")
    assert run_release(repo, env.ports, TODAY) == 0
    assert env.commands_starting("git", "tag", "-a", "core_kit-v0.3.0")


def test_existing_local_tag_is_refused(repo):
    env = FakeEnv(["2"], local_tags=("core_kit-v0.3.0",))
    with pytest.raises(ReleaseError, match="đã tồn tại ở local"):
        run_release(repo, env.ports, TODAY)
    assert _version(repo) == ("0.2.0", "0.2.0")


def test_existing_remote_tag_is_refused(repo):
    env = FakeEnv(["2"], remote_tags=("core_kit-v0.3.0",))
    with pytest.raises(ReleaseError, match="đã có trên remote"):
        run_release(repo, env.ports, TODAY)
    assert ["git", "ls-remote", "--tags", "origin", "refs/tags/core_kit-v0.3.0"] in env.commands


def test_remote_unreachable_only_warns(repo):
    env = FakeEnv(ANSWERS_MINOR_NO_PUSH, remote_rc=128)
    assert run_release(repo, env.ports, TODAY) == 0
    assert "không kiểm được tag trên remote" in env.output
    assert env.commands_starting("git", "tag", "-a")


def test_no_origin_remote_skips_remote_check(repo):
    env = FakeEnv(ANSWERS_MINOR_NO_PUSH, handlers={("git", "remote"): ProcessResult(0, "")})
    assert run_release(repo, env.ports, TODAY) == 0
    assert not env.commands_starting("git", "ls-remote")


# ---------------------------------------------------------------------------
# CHANGELOG trống, test fail, rollback
# ---------------------------------------------------------------------------
def test_empty_unreleased_warns_but_releases(repo):
    (repo / "CHANGELOG.md").write_text(CHANGELOG_EMPTY, encoding="utf-8")
    env = FakeEnv(ANSWERS_MINOR_NO_PUSH)
    assert run_release(repo, env.ports, TODAY) == 0
    assert "[Unreleased] trong CHANGELOG.md trống" in env.output
    assert "## [0.3.0] - 2026-11-07" in (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert env.commands_starting("git", "commit")


def test_failing_tests_restore_files_and_skip_commit(repo):
    env = FakeEnv(ANSWERS_MINOR_NO_PUSH, pytest_rc=1)
    with pytest.raises(ReleaseError, match="pytest thất bại"):
        run_release(repo, env.ports, TODAY)
    assert ["git", "checkout", "--", "pyproject.toml", "src/core_kit/__init__.py", "CHANGELOG.md"] in env.commands
    assert not env.commands_starting("git", "commit")
    assert not env.commands_starting("git", "tag", "-a")


def test_missing_unreleased_heading_restores_files(repo):
    (repo / "CHANGELOG.md").write_text("# Changelog\n\n## [0.2.0]\n", encoding="utf-8")
    env = FakeEnv(ANSWERS_MINOR_NO_PUSH)
    with pytest.raises(ReleaseError, match="Unreleased"):
        run_release(repo, env.ports, TODAY)
    assert env.commands_starting("git", "checkout", "--")
    assert not env.commands_starting(PYTHON, "-m", "pytest")


# ---------------------------------------------------------------------------
# Push và GitHub Release
# ---------------------------------------------------------------------------
def test_push_with_gh_creates_release_with_changelog_notes(repo):
    notes_seen: Dict[str, str] = {}

    def gh(cmd: List[str]) -> ProcessResult:
        notes_seen["text"] = Path(cmd[cmd.index("--notes-file") + 1]).read_text(encoding="utf-8")
        return ProcessResult(0, "https://github.com/x/y/releases/tag/core_kit-v0.3.0\n")

    env = FakeEnv(["2", "", "", "y"], handlers={("gh", "release", "create"): gh})
    assert run_release(repo, env.ports, TODAY) == 0
    assert ["git", "push", "origin", "HEAD"] in env.commands
    assert ["git", "push", "origin", "core_kit-v0.3.0"] in env.commands
    gh_cmd = env.commands_starting("gh", "release", "create")[0]
    assert gh_cmd[3] == "core_kit-v0.3.0"
    assert gh_cmd[gh_cmd.index("--title") + 1] == "core_kit v0.3.0"
    assert notes_seen["text"].startswith("### Đã thêm (Added)")
    assert "Đã tạo GitHub Release core_kit-v0.3.0" in env.output


def test_push_with_gh_and_empty_notes_generates_notes(repo):
    (repo / "CHANGELOG.md").write_text(CHANGELOG_EMPTY, encoding="utf-8")
    env = FakeEnv(["2", "", "", "y"])
    run_release(repo, env.ports, TODAY)
    assert "--generate-notes" in env.commands_starting("gh", "release", "create")[0]


def test_push_without_gh_prints_manual_instructions(repo):
    env = FakeEnv(["2", "", "", "y"], installed=("git",))
    assert run_release(repo, env.ports, TODAY) == 0
    assert ["git", "push", "origin", "core_kit-v0.3.0"] in env.commands
    assert not env.commands_starting("gh")
    assert "Chưa cài GitHub CLI (gh)" in env.output
    assert "chọn tag core_kit-v0.3.0" in env.output


def test_push_failure_keeps_local_commit_and_explains(repo):
    env = FakeEnv(["2", "", "", "y"], handlers={("git", "push"): ProcessResult(1, "", "rejected")})
    with pytest.raises(ReleaseError, match="vẫn ở local"):
        run_release(repo, env.ports, TODAY)
    assert env.commands_starting("git", "tag", "-a")
    assert not env.commands_starting("git", "checkout", "--")


def test_gh_failure_after_push_is_reported(repo):
    env = FakeEnv(["2", "", "", "y"], handlers={("gh", "release", "create"): ProcessResult(1, "", "auth required")})
    with pytest.raises(ReleaseError, match="gh release create lỗi"):
        run_release(repo, env.ports, TODAY)
    assert ["git", "push", "origin", "core_kit-v0.3.0"] in env.commands


def test_eof_on_prompt_cancels_cleanly(repo):
    env = FakeEnv([])
    with pytest.raises(ReleaseError, match="Đã hủy"):
        run_release(repo, env.ports, TODAY)
    assert _version(repo) == ("0.2.0", "0.2.0")


def test_main_prints_error_and_returns_1(repo, monkeypatch):
    env = FakeEnv([], dirty="?? x\n")
    monkeypatch.setattr(release, "real_ports", lambda: env.ports)
    monkeypatch.setattr(release, "ROOT_DIR", repo)
    assert release.main() == 1
    assert "[LỖI] Working tree chưa sạch" in env.output
