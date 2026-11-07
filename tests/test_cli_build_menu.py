"""Kiểm thử menu tương tác, chọn target và chế độ không tương tác của `corekit build`."""

import pytest

from core_kit.cli import main
from corekit_fakes import FakeEnv, write_app

TWO_TARGETS = """
[[tool.corekit.build.targets]]
name = "MyApp"
windowed = true

[[tool.corekit.build.targets]]
name = "MyTool"
"""


@pytest.fixture
def one_target_app(tmp_path, monkeypatch):
    root = write_app(tmp_path / "one", '[[tool.corekit.build.targets]]\nname = "MyApp"\n')
    monkeypatch.chdir(root)
    return root


@pytest.fixture
def two_target_app(tmp_path, monkeypatch):
    root = write_app(tmp_path / "two", TWO_TARGETS)
    monkeypatch.chdir(root)
    return root


def _built(env):
    return [next(a for a in c if a.startswith("--output-filename=")).split("=", 1)[1] for c in env.nuitka_calls]


def test_enter_on_mode_menu_picks_customer_build(one_target_app):
    env = FakeEnv(answers=[""])
    assert main(["build"], env.ports) == 0
    assert "--lto=yes" in env.nuitka_calls[0]
    assert "Giao khách" in env.output and "Nhanh" in env.output
    assert len(env.prompts) == 1  # một target thì không hỏi target


def test_mode_menu_choice_1_is_fast_and_reasks_on_invalid(one_target_app):
    env = FakeEnv(answers=["9", "1"])
    assert main(["build"], env.ports) == 0
    assert "--lto=no" in env.nuitka_calls[0]
    assert "không hợp lệ" in env.output


def test_non_interactive_without_mode_flag_fails_with_guidance(one_target_app):
    env = FakeEnv(interactive=False)
    assert main(["build"], env.ports) == 1
    assert "--fast" in env.output and "--release" in env.output
    assert env.nuitka_calls == []


def test_target_menu_enter_builds_all_in_order(two_target_app):
    env = FakeEnv(answers=["1", ""])
    assert main(["build"], env.ports) == 0
    assert _built(env) == ["MyApp.exe", "MyTool.exe"]
    assert "Tất cả" in env.output


def test_target_menu_pick_one(two_target_app):
    env = FakeEnv(answers=["1", "2"])
    assert main(["build"], env.ports) == 0
    assert _built(env) == ["MyTool.exe"]


def test_target_flag_skips_menu_and_is_repeatable(two_target_app):
    env = FakeEnv()
    assert main(["build", "--fast", "--target", "MyTool", "--target=MyApp"], env.ports) == 0
    assert _built(env) == ["MyTool.exe", "MyApp.exe"]
    assert env.prompts == []


def test_non_interactive_without_target_builds_all(two_target_app):
    env = FakeEnv(interactive=False)
    assert main(["build", "--release"], env.ports) == 0
    assert _built(env) == ["MyApp.exe", "MyTool.exe"]


def test_unknown_target_lists_valid_names(two_target_app):
    env = FakeEnv()
    assert main(["build", "--fast", "--target", "Nope"], env.ports) == 1
    assert "MyApp" in env.output and "MyTool" in env.output
    assert env.nuitka_calls == []


def test_stops_at_first_failing_target(two_target_app):
    env = FakeEnv(nuitka_rc={"MyApp": 2}, interactive=False)
    assert main(["build", "--fast"], env.ports) != 0
    assert _built(env) == ["MyApp.exe"]
    assert not (two_target_app / "build" / "fast" / "MyTool").exists()


def test_each_target_has_own_output_folder(two_target_app):
    assert main(["build", "--fast"], FakeEnv(interactive=False).ports) == 0
    assert (two_target_app / "build" / "fast" / "MyApp" / "MyApp.exe").is_file()
    assert (two_target_app / "build" / "fast" / "MyTool" / "MyTool.exe").is_file()


def test_cancel_on_menu_is_clean_error(one_target_app):
    env = FakeEnv(answers=[])  # ask() ném EOFError
    assert main(["build"], env.ports) == 1
    assert "hủy" in env.output
