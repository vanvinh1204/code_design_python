"""Kiểm thử nhận diện môi trường chạy và thư mục app/bundle/data (dev, Nuitka standalone/onefile, PyInstaller, `DATA_DIR`)."""

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
    monkeypatch.delenv("DATA_DIR", raising=False)
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


def test_data_dir_uses_env_var_and_creates_folder(dev_env, monkeypatch, tmp_path):
    data = tmp_path / "ProgramData" / "kho_server"
    assert not data.exists()
    monkeypatch.setenv("DATA_DIR", str(data))

    assert paths.data_dir() == data
    assert data.is_dir()
    assert paths.app_dir() == dev_env


def test_data_dir_falls_back_to_app_dir_when_unset_or_blank(dev_env, monkeypatch, tmp_path):
    assert paths.data_dir() == dev_env

    monkeypatch.setenv("DATA_DIR", "")
    assert paths.data_dir() == dev_env
    monkeypatch.setenv("DATA_DIR", "   ")
    assert paths.data_dir() == dev_env

    monkeypatch.delenv("DATA_DIR")
    dist = tmp_path / "Program Files" / "kho_server"
    _fake_nuitka(monkeypatch, onefile=False, containing_dir=dist.parent, executable=dist / "server.exe")
    assert paths.data_dir() == dist


def test_data_dir_env_var_wins_over_packaged_app_dir(dev_env, monkeypatch, tmp_path):
    dist = tmp_path / "Program Files" / "kho_server"
    data = tmp_path / "ProgramData" / "kho_server"
    _fake_nuitka(monkeypatch, onefile=True, containing_dir=dist, executable=tmp_path / "Temp" / "onefile_1" / "server.exe")
    monkeypatch.setenv("DATA_DIR", str(data))

    assert paths.app_dir() == dist
    assert paths.data_dir() == data
    assert data.is_dir()


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


def test_logger_relative_log_dir_anchored_at_data_dir(dev_env, monkeypatch, tmp_path):
    from core_kit.logger.logging import resolve_log_dir

    # Dev, không DATA_DIR: Data Dir = App Dir = thư mục hiện tại.
    assert resolve_log_dir("logs") == dev_env / "logs"

    # Bản đóng gói, không DATA_DIR: cạnh exe như trước.
    dist = tmp_path / "MyApp"
    _fake_nuitka(monkeypatch, onefile=False, containing_dir=tmp_path, executable=dist / "MyApp.exe")
    assert resolve_log_dir("logs") == dist / "logs"

    # Có DATA_DIR: log đi theo Data Dir dù đang chạy bản đóng gói.
    data = tmp_path / "ProgramData" / "MyApp"
    monkeypatch.setenv("DATA_DIR", str(data))
    assert resolve_log_dir("logs") == data / "logs"

    # Đường dẫn tuyệt đối vẫn được tôn trọng.
    absolute = tmp_path / "abs_logs"
    assert resolve_log_dir(str(absolute)) == absolute


def test_setup_logger_writes_file_into_data_dir_logs(dev_env, monkeypatch, tmp_path):
    from core_kit.logger import setup_logger

    data = tmp_path / "ProgramData" / "MyApp"
    monkeypatch.setenv("DATA_DIR", str(data))

    logger = setup_logger(app_name="myapp")
    try:
        logger.info("xin chào")
        if hasattr(logger, "complete"):  # loguru ghi file qua hàng đợi, chờ xả hết
            logger.complete()
        else:  # fallback logging chuẩn
            for handler in logger.handlers:
                handler.flush()
        log_files = list((data / "logs").glob("myapp*.log"))
    finally:
        if hasattr(logger, "remove"):
            logger.remove()
        else:
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)

    assert log_files, "không thấy file log trong DATA_DIR/logs"
    assert not (dev_env / "logs").exists()
    assert "xin chào" in log_files[0].read_text(encoding="utf-8")
