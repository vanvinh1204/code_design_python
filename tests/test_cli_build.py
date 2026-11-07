"""Kiểm thử `corekit build` qua điểm vào CLI `main(argv, ports)` với cổng giả."""

from pathlib import Path

import pytest

from core_kit.cli import main
from corekit_fakes import PYTHON, FakeEnv, write_app

ONE_TARGET = """
[[tool.corekit.build.targets]]
name = "MyApp"
entry = "main.py"
windowed = true
"""


@pytest.fixture
def app(tmp_path, monkeypatch):
    root = write_app(tmp_path / "apps" / "my_app", ONE_TARGET)
    monkeypatch.chdir(root)
    return root


def test_fast_build_calls_nuitka_with_fast_options(app):
    env = FakeEnv()
    assert main(["build", "--fast"], env.ports) == 0

    (cmd,) = env.nuitka_calls
    assert cmd[:3] == [PYTHON, "-m", "nuitka"]
    assert cmd[-1] == str(app / "main.py")
    assert "--mode=standalone" in cmd
    assert "--lto=no" in cmd
    assert "--deployment" not in cmd
    assert "--windows-console-mode=attach" in cmd
    for flag in ("--assume-yes-for-downloads", "--remove-output", "--output-filename=MyApp.exe"):
        assert flag in cmd
    assert any(a.startswith("--jobs=") for a in cmd)


def test_release_build_uses_lto_deployment_and_windowed_console(app):
    env = FakeEnv()
    assert main(["build", "--release"], env.ports) == 0

    (cmd,) = env.nuitka_calls
    assert "--lto=yes" in cmd
    assert "--deployment" in cmd
    assert "--windows-console-mode=disable" in cmd


def test_release_console_forced_for_non_windowed_target(tmp_path, monkeypatch):
    root = write_app(tmp_path / "cli", '[[tool.corekit.build.targets]]\nname = "Tool"\n')
    monkeypatch.chdir(root)
    env = FakeEnv()
    assert main(["build", "--release"], env.ports) == 0
    (cmd,) = env.nuitka_calls
    assert "--windows-console-mode=force" in cmd
    assert cmd[-1] == str(root / "main.py")  # entry mặc định theo chuẩn v1.2.0


def test_output_folder_is_runnable_with_env_next_to_exe(app):
    env = FakeEnv()
    assert main(["build", "--fast"], env.ports) == 0

    out = app / "build" / "fast" / "MyApp"
    assert (out / "MyApp.exe").is_file()
    assert (out / "python312.dll").is_file()
    assert (out / ".env").read_text(encoding="utf-8") == "SECRET=real\n"
    assert not (out / ".env.example").exists()
    assert not (app / "build" / "fast" / ".staging").exists()
    assert str(out) in env.output


def test_env_example_copied_with_warning_when_env_missing(app):
    (app / ".env").unlink()
    env = FakeEnv()
    assert main(["build", "--fast"], env.ports) == 0

    out = app / "build" / "fast" / "MyApp"
    assert (out / ".env.example").is_file()
    assert not (out / ".env").exists()
    assert "Cảnh báo" in env.output and ".env" in env.output


def test_old_output_removed_before_build(app):
    stale = app / "build" / "release" / "MyApp" / "stale.txt"
    stale.parent.mkdir(parents=True)
    stale.write_text("old", encoding="utf-8")

    assert main(["build", "--release"], FakeEnv().ports) == 0
    assert not stale.exists()
    assert (app / "build" / "release" / "MyApp" / "MyApp.exe").is_file()


def test_missing_pyproject_is_clear_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = FakeEnv()
    assert main(["build", "--fast"], env.ports) == 1
    assert "pyproject.toml" in env.output
    assert env.nuitka_calls == []


def test_missing_target_block_is_clear_error(tmp_path, monkeypatch):
    root = write_app(tmp_path / "a", "")
    monkeypatch.chdir(root)
    env = FakeEnv()
    assert main(["build", "--fast"], env.ports) == 1
    assert "[[tool.corekit.build.targets]]" in env.output


def test_missing_entry_file_is_error_before_nuitka(app):
    (app / "main.py").unlink()
    env = FakeEnv()
    assert main(["build", "--fast"], env.ports) == 1
    assert "main.py" in env.output
    assert env.nuitka_calls == []


def test_nuitka_failure_gives_nonzero_exit(app):
    env = FakeEnv(nuitka_rc=3)
    assert main(["build", "--fast"], env.ports) != 0
    assert "MyApp" in env.output
    assert not (app / "build" / "fast" / "MyApp").exists()


def test_both_mode_flags_is_error(app):
    env = FakeEnv()
    assert main(["build", "--fast", "--release"], env.ports) == 1
    assert env.nuitka_calls == []


def test_unknown_command_and_help(app):
    env = FakeEnv()
    assert main(["deploy"], env.ports) == 1
    assert main(["--help"], env.ports) == 0
    assert "corekit build" in env.output and "corekit release" in env.output
