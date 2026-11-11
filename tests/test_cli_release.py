"""Kiểm thử `corekit release` qua `main(argv, ports)`: git, version, build, zip, rollback, publish, release.json."""

import json
import zipfile
from datetime import datetime

import pytest

import core_kit
from core_kit.cli import main
from core_kit.cli.ports import ProcessResult
from corekit_fakes import FakeEnv, write_app

TARGETS = """
[[tool.corekit.build.targets]]
name = "MyApp"
windowed = true
copy = ["models/"]

[[tool.corekit.build.targets]]
name = "MyTool"

[tool.corekit.release]
include = ["docs/HUONG_DAN.pdf", "CHANGELOG.md"]
"""

CHANGELOG = """# Changelog

## [Unreleased]

## [0.3.1] - 2026-11-07

### Đã thêm
- In tem mới.

## [0.3.0] - 2026-11-01
- Bản đầu.
"""


def git_env(*, dirty: str = "", tags: str = "", **kwargs) -> FakeEnv:
    handlers = {
        ("git", "status", "--porcelain"): ProcessResult(0, dirty),
        ("git", "tag", "-l"): lambda cmd: ProcessResult(0, f"{cmd[3]}\n" if cmd[3] in tags.split() else ""),
    }
    handlers.update(kwargs.pop("handlers", {}))
    kwargs.setdefault("interactive", False)
    return FakeEnv(handlers=handlers, **kwargs)


@pytest.fixture
def app(tmp_path, monkeypatch):
    root = write_app(tmp_path / "apps" / "kho", TARGETS, version="0.3.0", name="kho")
    (root / "models").mkdir()
    (root / "models" / "plate.pt").write_bytes(b"pt")
    (root / "docs").mkdir()
    (root / "docs" / "HUONG_DAN.pdf").write_bytes(b"%PDF")
    (root / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
    monkeypatch.chdir(root)
    return root


def _version(root):
    import tomllib

    return tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def test_release_bumps_builds_zips_commits_and_tags(app):
    env = git_env()
    assert main(["release", "--bump", "patch", "--no-publish"], env.ports) == 0

    assert _version(app) == "0.3.1"
    nuitka = env.nuitka_calls
    assert len(nuitka) == 2
    assert all("--lto=yes" in c and "--deployment" in c and "--product-version=0.3.1" in c for c in nuitka)
    assert env.commands_starting("git", "add") == [["git", "add", "pyproject.toml"]]
    assert env.commands_starting("git", "commit") == [["git", "commit", "-m", "chore(release): kho v0.3.1"]]
    assert env.commands_starting("git", "tag", "-a") == [["git", "tag", "-a", "kho-v0.3.1", "-m", "Release kho v0.3.1"]]
    assert env.commands_starting("git", "push") == []
    assert env.commands_starting("gh") == []
    order = [c[:2] for c in env.commands if c[0] == "git" and c[1] in ("commit", "tag") and len(c) > 2 and c[2] != "-l"]
    assert order == [["git", "commit"], ["git", "tag"]]


def test_zip_contents_exclude_env_and_include_example_and_docs(app):
    assert main(["release", "--bump", "minor", "--no-publish"], git_env().ports) == 0

    zip_path = app / "dist" / "MyApp-0.4.0-win-x64.zip"
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        assert archive.read("MyApp-0.4.0/.env.example") == (app / ".env.example").read_bytes()
    assert {n.split("/")[0] for n in names} == {"MyApp-0.4.0"}
    assert "MyApp-0.4.0/MyApp.exe" in names
    assert "MyApp-0.4.0/models/plate.pt" in names
    assert "MyApp-0.4.0/HUONG_DAN.pdf" in names
    assert "MyApp-0.4.0/CHANGELOG.md" in names
    assert not any(n.endswith("/.env") for n in names)
    assert (app / "dist" / "MyTool-0.4.0-win-x64.zip").is_file()


def test_dirty_git_tree_refuses_before_anything(app):
    env = git_env(dirty=" M src/kho/app.py\n")
    assert main(["release", "--bump", "patch"], env.ports) == 1
    assert "commit" in env.output.lower()
    assert env.nuitka_calls == []
    assert _version(app) == "0.3.0"


def test_existing_tag_refused_including_keep(app):
    env = git_env(tags="kho-v0.3.0")
    assert main(["release", "--bump", "keep"], env.ports) == 1
    assert "kho-v0.3.0" in env.output
    assert env.nuitka_calls == []


def test_keep_without_existing_tag_tags_without_commit(app):
    env = git_env()
    assert main(["release", "--bump", "keep", "--no-publish"], env.ports) == 0
    assert env.commands_starting("git", "commit") == []
    assert env.commands_starting("git", "tag", "-a")[0][3] == "kho-v0.3.0"


def test_build_failure_restores_pyproject_and_lock_no_commit_no_tag(app):
    original = (app / "pyproject.toml").read_bytes()
    (app / "uv.lock").write_text("lock v0.3.0\n", encoding="utf-8")

    def fake_uv_lock(cmd):
        (app / "uv.lock").write_text("lock v0.3.1\n", encoding="utf-8")
        return ProcessResult(0)

    env = git_env(nuitka_rc={"MyTool": 1}, handlers={("uv", "lock"): fake_uv_lock})
    assert main(["release", "--bump", "patch", "--no-publish"], env.ports) == 1

    assert env.commands_starting("uv", "lock")
    assert (app / "pyproject.toml").read_bytes() == original
    assert (app / "uv.lock").read_text(encoding="utf-8") == "lock v0.3.0\n"
    assert env.commands_starting("git", "commit") == []
    assert env.commands_starting("git", "tag", "-a") == []
    assert list(app.glob("dist/*.zip")) == []
    assert "trả" in env.output


def test_uv_lock_committed_with_pyproject(app):
    (app / "uv.lock").write_text("lock\n", encoding="utf-8")
    env = git_env()
    assert main(["release", "--bump", "patch", "--no-publish"], env.ports) == 0
    assert env.commands_starting("git", "add") == [["git", "add", "pyproject.toml", "uv.lock"]]


def test_missing_env_example_fails_before_build(app):
    (app / ".env.example").unlink()
    env = git_env()
    assert main(["release", "--bump", "patch"], env.ports) == 1
    assert ".env.example" in env.output
    assert env.nuitka_calls == []
    assert _version(app) == "0.3.0"


def test_missing_include_fails_before_build(app):
    (app / "docs" / "HUONG_DAN.pdf").unlink()
    env = git_env()
    assert main(["release", "--bump", "patch"], env.ports) == 1
    assert "HUONG_DAN.pdf" in env.output
    assert env.nuitka_calls == []


def test_version_menu_default_is_patch(app):
    env = git_env(interactive=True, answers=["", ""])  # Enter = patch, Enter = không push
    assert main(["release"], env.ports) == 0
    assert _version(app) == "0.3.1"
    assert "minor → 0.4.0" in env.output and "major → 1.0.0" in env.output
    assert env.commands_starting("git", "push") == []


def test_non_interactive_without_bump_is_error(app):
    env = git_env()
    assert main(["release"], env.ports) == 1
    assert "--bump" in env.output


def test_release_never_asks_build_mode_or_target(app):
    env = git_env(interactive=True, answers=["1", "n"])
    assert main(["release"], env.ports) == 0
    assert len(env.prompts) == 2
    assert len(env.nuitka_calls) == 2


def test_missing_changelog_section_warns_and_can_stop(app):
    env = git_env(interactive=True, answers=["2", "n"])  # minor 0.4.0 chưa có trong CHANGELOG, chọn dừng
    assert main(["release"], env.ports) == 1
    assert "CHANGELOG.md" in env.output and "0.4.0" in env.output
    assert env.nuitka_calls == []


def test_missing_changelog_section_non_interactive_continues_with_warning(app):
    env = git_env()
    assert main(["release", "--bump", "minor", "--no-publish"], env.ports) == 0
    assert "Cảnh báo" in env.output


# ---- nssm_manager v1, ticket 03: Manifest phát hành release.json ----

MANIFEST_KEYS = {"repo", "app", "target", "version", "built_at", "health_path", "core_kit"}


def _manifest(zip_path, folder):
    with zipfile.ZipFile(zip_path) as archive:
        return json.loads(archive.read(f"{folder}/release.json").decode("utf-8"))


def test_release_json_in_every_zip_describes_its_target(app, tmp_path):
    (tmp_path / ".git").mkdir()  # app nằm ở <repo>/apps/kho → repo là tên thư mục chứa .git
    before = datetime.now().astimezone().replace(microsecond=0)
    assert main(["release", "--bump", "patch", "--no-publish"], git_env().ports) == 0

    for target in ("MyApp", "MyTool"):
        data = _manifest(app / "dist" / f"{target}-0.3.1-win-x64.zip", f"{target}-0.3.1")
        assert set(data) == MANIFEST_KEYS
        assert data["repo"] == tmp_path.name
        assert data["app"] == "kho"
        assert data["target"] == target
        assert data["version"] == "0.3.1"
        assert data["health_path"] == "/health"
        assert data["core_kit"] == core_kit.__version__
        built_at = datetime.fromisoformat(data["built_at"])
        assert built_at.utcoffset() is not None  # giờ địa phương kèm offset
        assert before <= built_at <= datetime.now().astimezone()


def test_release_json_sits_next_to_env_example(app):
    assert main(["release", "--bump", "patch", "--no-publish"], git_env().ports) == 0
    with zipfile.ZipFile(app / "dist" / "MyApp-0.3.1-win-x64.zip") as archive:
        names = archive.namelist()
    assert "MyApp-0.3.1/release.json" in names and "MyApp-0.3.1/.env.example" in names
    assert [n for n in names if n.endswith("release.json")] == ["MyApp-0.3.1/release.json"]


def test_custom_health_path_written_to_release_json(app):
    with open(app / "pyproject.toml", "a", encoding="utf-8") as f:
        f.write('health_path = "/api/health"\n')
    assert main(["release", "--bump", "patch", "--no-publish"], git_env().ports) == 0
    data = _manifest(app / "dist" / "MyTool-0.3.1-win-x64.zip", "MyTool-0.3.1")
    assert data["health_path"] == "/api/health"


@pytest.mark.parametrize("value", ['"health"', "true", '["/health"]'])
def test_invalid_health_path_is_config_error_before_build(app, value):
    with open(app / "pyproject.toml", "a", encoding="utf-8") as f:
        f.write(f"health_path = {value}\n")
    env = git_env()
    assert main(["release", "--bump", "patch", "--no-publish"], env.ports) == 1
    assert "[tool.corekit.release].health_path" in env.output
    assert env.nuitka_calls == []
    assert _version(app) == "0.3.0"


# ---- ticket 07: publish ----


def test_publish_pushes_and_creates_release_with_changelog_notes(app):
    env = git_env()
    assert main(["release", "--bump", "patch", "--publish"], env.ports) == 0

    assert env.commands_starting("git", "push") == [
        ["git", "push", "origin", "HEAD"],
        ["git", "push", "origin", "kho-v0.3.1"],
    ]
    (gh,) = env.commands_starting("gh", "release", "create")
    assert gh[3] == "kho-v0.3.1"
    assert str(app / "dist" / "MyApp-0.3.1-win-x64.zip") in gh
    assert str(app / "dist" / "MyTool-0.3.1-win-x64.zip") in gh
    assert gh[gh.index("--title") + 1] == "kho v0.3.1"
    assert "--notes-file" in gh


def test_publish_without_changelog_uses_generated_notes(app):
    (app / "CHANGELOG.md").unlink()
    (app / "pyproject.toml").write_text(
        (app / "pyproject.toml").read_text(encoding="utf-8").replace(', "CHANGELOG.md"', ""), encoding="utf-8"
    )
    env = git_env()
    assert main(["release", "--bump", "patch", "--publish"], env.ports) == 0
    (gh,) = env.commands_starting("gh", "release", "create")
    assert "--generate-notes" in gh and "--notes" not in gh


def test_interactive_confirm_yes_publishes(app):
    env = git_env(interactive=True, answers=["1", "y"])
    assert main(["release"], env.ports) == 0
    assert env.commands_starting("gh", "release", "create")


def test_missing_gh_keeps_local_tag_and_pushes_nothing(app):
    env = git_env(installed=("git", "uv"))
    assert main(["release", "--bump", "patch", "--publish"], env.ports) == 1
    assert "gh" in env.output and "kho-v0.3.1" in env.output
    assert env.commands_starting("git", "tag", "-a")
    assert env.commands_starting("git", "push") == []
    assert _version(app) == "0.3.1"  # commit đã có, không rollback


def test_both_publish_flags_is_error(app):
    env = git_env()
    assert main(["release", "--publish", "--no-publish"], env.ports) == 1


def test_notes_passed_via_notes_file(app):
    seen = {}

    def gh_create(cmd):
        notes_file = cmd[cmd.index("--notes-file") + 1]
        seen["text"] = open(notes_file, encoding="utf-8").read()
        return ProcessResult(0, "https://github.com/x/y/releases/tag/kho-v0.3.1")

    env = git_env(handlers={("gh", "release", "create"): gh_create})
    assert main(["release", "--bump", "patch", "--publish"], env.ports) == 0
    (gh,) = env.commands_starting("gh", "release", "create")
    assert "--notes" not in gh
    assert seen["text"].startswith("### Đã thêm")


def test_commit_failure_unstages_and_restores(app):
    original = (app / "pyproject.toml").read_bytes()
    env = git_env(handlers={("git", "commit"): ProcessResult(1, "", "hook rejected")})
    assert main(["release", "--bump", "patch", "--no-publish"], env.ports) == 1
    assert (app / "pyproject.toml").read_bytes() == original
    assert ["git", "reset", "-q", "--", "pyproject.toml"] in env.commands
    assert env.commands_starting("git", "tag", "-a") == []
    assert "hook rejected" in env.output


def test_tag_existing_on_remote_is_refused(app):
    env = git_env(
        handlers={
            ("git", "remote"): ProcessResult(0, "origin\n"),
            ("git", "ls-remote", "--tags", "origin"): ProcessResult(0, "abc123\trefs/tags/kho-v0.3.1\n"),
        }
    )
    assert main(["release", "--bump", "patch"], env.ports) == 1
    assert "kho-v0.3.1" in env.output
    assert env.nuitka_calls == []


def test_unreachable_remote_only_warns(app):
    env = git_env(
        handlers={
            ("git", "remote"): ProcessResult(0, "origin\n"),
            ("git", "ls-remote", "--tags", "origin"): ProcessResult(128, "", "Could not resolve host"),
        }
    )
    assert main(["release", "--bump", "patch", "--no-publish"], env.ports) == 0
    assert "remote" in env.output
