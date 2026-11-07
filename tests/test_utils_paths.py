"""Kiểm thử nhận diện môi trường chạy và thư mục app/bundle (dev, Nuitka standalone/onefile, PyInstaller)."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from core_kit.utils import paths


@pytest.fixture
def dev_env(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "_nuitka_compiled", lambda: None)
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _fake_nuitka(monkeypatch, *, onefile: bool, containing_dir: Path, executable: Path):
    info = SimpleNamespace(onefile=onefile, standalone=True, containing_dir=str(containing_dir))
    monkeypatch.setattr(paths, "_nuitka_compiled", lambda: info)
    monkeypatch.setattr(sys, "executable", str(executable))


def test_dev_mode_uses_cwd(dev_env):
    assert paths.is_packaged() is False
    assert paths.app_dir() == dev_env
    assert paths.bundle_dir() == dev_env


def test_nuitka_standalone_uses_exe_folder(dev_env, monkeypatch, tmp_path):
    dist = tmp_path / "build" / "release" / "MyApp"
    _fake_nuitka(monkeypatch, onefile=False, containing_dir=dist.parent, executable=dist / "MyApp.exe")

    assert paths.is_packaged() is True
    assert paths.app_dir() == dist
    assert paths.bundle_dir() == dist


def test_nuitka_onefile_app_dir_is_onefile_location_bundle_is_extraction(dev_env, monkeypatch, tmp_path):
    exe_dir = tmp_path / "khach" / "MyTool"
    extract = tmp_path / "Temp" / "onefile_1234"
    _fake_nuitka(monkeypatch, onefile=True, containing_dir=exe_dir, executable=extract / "MyTool.exe")

    assert paths.is_packaged() is True
    assert paths.app_dir() == exe_dir
    assert paths.bundle_dir() == extract


def test_pyinstaller_onefile(dev_env, monkeypatch, tmp_path):
    exe_dir = tmp_path / "app"
    meipass = tmp_path / "Temp" / "_MEI123"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_dir / "App.exe"))

    assert paths.is_packaged() is True
    assert paths.app_dir() == exe_dir
    assert paths.bundle_dir() == meipass


def test_pyinstaller_onedir_without_meipass(dev_env, monkeypatch, tmp_path):
    exe_dir = tmp_path / "app"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_dir / "App.exe"))

    assert paths.app_dir() == exe_dir
    assert paths.bundle_dir() == exe_dir


def test_resolve_script_location_finds_migrations_next_to_nuitka_exe(dev_env, monkeypatch, tmp_path):
    from core_kit.database.migration import resolve_script_location

    dist = tmp_path / "MyApp"
    (dist / "migrations").mkdir(parents=True)
    other_cwd = tmp_path / "elsewhere"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)
    _fake_nuitka(monkeypatch, onefile=False, containing_dir=tmp_path, executable=dist / "MyApp.exe")

    assert resolve_script_location("migrations") == dist / "migrations"


def test_resolve_script_location_prefers_bundle_then_app_dir_in_onefile(dev_env, monkeypatch, tmp_path):
    from core_kit.database.migration import resolve_script_location

    exe_dir = tmp_path / "khach"
    extract = tmp_path / "Temp" / "onefile_1"
    (exe_dir / "migrations").mkdir(parents=True)
    _fake_nuitka(monkeypatch, onefile=True, containing_dir=exe_dir, executable=extract / "A.exe")
    assert resolve_script_location("migrations") == exe_dir / "migrations"

    (extract / "migrations").mkdir(parents=True)
    assert resolve_script_location("migrations") == extract / "migrations"


def test_resolve_script_location_dev_uses_cwd(dev_env):
    from core_kit.database.migration import resolve_script_location

    (dev_env / "migrations").mkdir()
    assert resolve_script_location("migrations") == dev_env / "migrations"


def test_settings_env_file_anchored_at_app_dir_only_when_packaged(dev_env, monkeypatch, tmp_path):
    from core_kit.config.settings import default_env_file

    assert default_env_file() == ".env"

    dist = tmp_path / "MyApp"
    _fake_nuitka(monkeypatch, onefile=False, containing_dir=tmp_path, executable=dist / "MyApp.exe")
    assert Path(default_env_file()) == dist / ".env"


def test_logger_relative_log_dir_anchored_when_packaged(dev_env, monkeypatch, tmp_path):
    from core_kit.logger.logging import resolve_log_dir

    assert resolve_log_dir("logs") == Path("logs")

    dist = tmp_path / "MyApp"
    _fake_nuitka(monkeypatch, onefile=False, containing_dir=tmp_path, executable=dist / "MyApp.exe")
    assert resolve_log_dir("logs") == dist / "logs"
    absolute = tmp_path / "abs_logs"
    assert resolve_log_dir(str(absolute)) == absolute
