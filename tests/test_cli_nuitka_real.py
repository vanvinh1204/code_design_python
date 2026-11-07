"""
Test Nuitka thật (chậm, cần mạng ở lần đầu để Nuitka tải MinGW64): build app hello-world ở chế độ nhanh,
chạy exe từ một thư mục khác và kiểm `app_dir()` / `bundle_dir()` in ra từ trong exe.

Mặc định bị bỏ qua. Chạy: pytest -m nuitka
"""

import subprocess
import sys

import pytest

from core_kit.cli import main
from core_kit.cli.ports import real_ports

pytestmark = [
    pytest.mark.nuitka,
    pytest.mark.skipif(sys.platform != "win32", reason="corekit build nhắm Windows"),
]

HELLO = '''from core_kit.utils.paths import app_dir, bundle_dir, is_packaged

print(f"packaged={is_packaged()}")
print(f"app_dir={app_dir()}")
print(f"bundle_dir={bundle_dir()}")
print(f"data={(bundle_dir() / 'assets' / 'note.txt').read_text(encoding='utf-8').strip()}")
'''


@pytest.mark.parametrize("onefile", [False, True], ids=["standalone", "onefile"])
def test_real_fast_build_runs_and_resolves_app_dir(tmp_path, monkeypatch, onefile):
    root = tmp_path / "hello"
    (root / "assets").mkdir(parents=True)
    (root / "assets" / "note.txt").write_text("bundled", encoding="utf-8")
    (root / "main.py").write_text(HELLO, encoding="utf-8")
    (root / ".env").write_text("A=1\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "hello"\nversion = "0.1.0"\n\n'
        '[[tool.corekit.build.targets]]\nname = "Hello"\n'
        f'onefile = {"true" if onefile else "false"}\ndatas = ["assets/"]\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(root)

    assert main(["build", "--fast"], real_ports()) == 0

    exe = root / "build" / "fast" / "Hello" / "Hello.exe"
    assert exe.is_file()
    assert (exe.parent / ".env").is_file()

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    done = subprocess.run(
        [str(exe)], cwd=elsewhere, capture_output=True, text=True, encoding="utf-8", timeout=120
    )
    assert done.returncode == 0, done.stderr
    lines = dict(line.split("=", 1) for line in done.stdout.splitlines() if "=" in line)
    assert lines["packaged"] == "True"
    assert lines["app_dir"].lower() == str(exe.parent.resolve()).lower()
    assert lines["data"] == "bundled"
    if onefile:
        assert lines["bundle_dir"].lower() != lines["app_dir"].lower()
    else:
        assert lines["bundle_dir"].lower() == lines["app_dir"].lower()
