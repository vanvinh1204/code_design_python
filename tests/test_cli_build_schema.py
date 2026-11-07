"""Kiểm thử schema target đầy đủ của `corekit build`: icon, onefile, datas, plugins, copy, extra_args, company."""

import pytest

from core_kit.cli import main
from corekit_fakes import FakeEnv, write_app

FULL = """
[tool.corekit.build]
company = "Công ty ABC"

[[tool.corekit.build.targets]]
name = "MyApp"
entry = "main.py"
icon = "assets/icon.ico"
windowed = true
datas = ["assets/", "templates/label.prn"]
plugins = ["pyside6"]
copy = ["models/", "config/printers.toml"]
extra_args = ["--include-package-data=trafilatura"]
"""


@pytest.fixture
def app(tmp_path, monkeypatch):
    root = write_app(tmp_path / "my_app", FULL, version="0.3.0rc1")
    (root / "assets").mkdir()
    (root / "assets" / "icon.ico").write_bytes(b"ico")
    (root / "templates").mkdir()
    (root / "templates" / "label.prn").write_bytes(b"prn")
    (root / "models").mkdir()
    (root / "models" / "plate.pt").write_bytes(b"pt")
    (root / "config").mkdir()
    (root / "config" / "printers.toml").write_text("ip = '1.2.3.4'\n", encoding="utf-8")
    monkeypatch.chdir(root)
    return root


def test_full_schema_maps_to_nuitka_options(app):
    env = FakeEnv()
    assert main(["build", "--release"], env.ports) == 0

    (cmd,) = env.nuitka_calls
    assert f"--windows-icon-from-ico={app / 'assets' / 'icon.ico'}" in cmd
    assert f"--include-data-dir={app / 'assets'}=assets" in cmd
    assert f"--include-data-files={app / 'templates' / 'label.prn'}=templates/label.prn" in cmd
    assert "--enable-plugins=pyside6" in cmd
    assert "--company-name=Công ty ABC" in cmd
    assert "--product-name=MyApp" in cmd
    assert "--product-version=0.3.0" in cmd
    assert "--file-version=0.3.0" in cmd
    # extra_args đi sau tùy chọn sinh tự động, ngay trước file entry
    assert cmd[-2] == "--include-package-data=trafilatura"
    assert cmd[-1] == str(app / "main.py")


def test_copy_items_placed_next_to_exe_not_inside(app):
    env = FakeEnv()
    assert main(["build", "--release"], env.ports) == 0

    out = app / "build" / "release" / "MyApp"
    assert (out / "models" / "plate.pt").read_bytes() == b"pt"
    assert (out / "config" / "printers.toml").is_file()
    (cmd,) = env.nuitka_calls
    assert not any("models" in a for a in cmd)


def test_onefile_target_ends_up_in_its_own_folder(tmp_path, monkeypatch):
    root = write_app(
        tmp_path / "tool",
        '[[tool.corekit.build.targets]]\nname = "MyTool"\nonefile = true\ncopy = ["readme.txt"]\n',
    )
    (root / "readme.txt").write_text("hi", encoding="utf-8")
    monkeypatch.chdir(root)
    env = FakeEnv()
    assert main(["build", "--fast"], env.ports) == 0

    (cmd,) = env.nuitka_calls
    assert "--mode=onefile" in cmd
    out = root / "build" / "fast" / "MyTool"
    assert (out / "MyTool.exe").is_file()
    assert (out / ".env").is_file()
    assert (out / "readme.txt").is_file()


@pytest.mark.parametrize(
    "field, value",
    [
        ("icon", '"assets/missing.ico"'),
        ("datas", '["nope/"]'),
        ("copy", '["models/missing.pt"]'),
    ],
)
def test_missing_declared_path_fails_before_nuitka(tmp_path, monkeypatch, field, value):
    root = write_app(tmp_path / "a", f'[[tool.corekit.build.targets]]\nname = "A"\n{field} = {value}\n')
    monkeypatch.chdir(root)
    env = FakeEnv()
    assert main(["build", "--fast"], env.ports) == 1
    assert field in env.output
    assert env.nuitka_calls == []


def test_unknown_target_key_is_error(tmp_path, monkeypatch):
    root = write_app(tmp_path / "a", '[[tool.corekit.build.targets]]\nname = "A"\nwindow = true\n')
    monkeypatch.chdir(root)
    env = FakeEnv()
    assert main(["build", "--fast"], env.ports) == 1
    assert "window" in env.output
    assert env.nuitka_calls == []


def test_wrong_type_is_error(tmp_path, monkeypatch):
    root = write_app(tmp_path / "a", '[[tool.corekit.build.targets]]\nname = "A"\ndatas = "assets/"\n')
    monkeypatch.chdir(root)
    env = FakeEnv()
    assert main(["build", "--fast"], env.ports) == 1
    assert "datas" in env.output


def test_non_numeric_version_is_error(tmp_path, monkeypatch):
    root = write_app(tmp_path / "a", '[[tool.corekit.build.targets]]\nname = "A"\n', version="dev")
    monkeypatch.chdir(root)
    env = FakeEnv()
    assert main(["build", "--fast"], env.ports) == 1
    assert "version" in env.output
