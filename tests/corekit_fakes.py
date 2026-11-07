"""Cổng giả cho CLI `corekit`: thay menu, console, Nuitka, git, uv và gh trong test."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union

from core_kit.cli.ports import Ports, ProcessResult

Handler = Union[ProcessResult, Callable[[List[str]], ProcessResult]]

PYTHON = "C:/app/.venv/Scripts/python.exe"


def _opt(cmd: Sequence[str], name: str) -> Optional[str]:
    prefix = f"{name}="
    for arg in cmd:
        if arg.startswith(prefix):
            return arg[len(prefix):]
    return None


class FakeEnv:
    def __init__(
        self,
        answers: Sequence[str] = (),
        interactive: bool = True,
        nuitka_rc: Union[int, Dict[str, int]] = 0,
        installed: Sequence[str] = ("gh", "git", "uv"),
        handlers: Optional[Dict[Tuple[str, ...], Handler]] = None,
    ) -> None:
        self.answers = list(answers)
        self.interactive = interactive
        self.nuitka_rc = nuitka_rc
        self.installed = set(installed)
        self.handlers = dict(handlers or {})
        self.lines: List[str] = []
        self.prompts: List[str] = []
        self.commands: List[List[str]] = []

    # ---- cổng ----
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
        if cmd[:3] == [PYTHON, "-m", "nuitka"]:
            return self._nuitka(cmd)
        best: Optional[Tuple[str, ...]] = None
        for prefix in self.handlers:
            if tuple(cmd[: len(prefix)]) == prefix and (best is None or len(prefix) > len(best)):
                best = prefix
        if best is None:
            return ProcessResult(0, "", "")
        handler = self.handlers[best]
        return handler(cmd) if callable(handler) else handler

    @property
    def ports(self) -> Ports:
        return Ports(
            ask=self.ask,
            is_interactive=lambda: self.interactive,
            echo=self.echo,
            run=self.run,
            which=self.which,
            python=PYTHON,
        )

    # ---- giả lập Nuitka ----
    def _nuitka(self, cmd: List[str]) -> ProcessResult:
        filename = _opt(cmd, "--output-filename") or "main.exe"
        name = filename[:-4] if filename.endswith(".exe") else filename
        rc = self.nuitka_rc.get(name, 0) if isinstance(self.nuitka_rc, dict) else self.nuitka_rc
        if rc != 0:
            return ProcessResult(rc, "", "nuitka failed")
        out = Path(_opt(cmd, "--output-dir") or ".")
        out.mkdir(parents=True, exist_ok=True)
        if _opt(cmd, "--mode") == "onefile":
            (out / filename).write_bytes(b"MZ onefile")
        else:
            dist = out / f"{Path(cmd[-1]).stem}.dist"
            dist.mkdir(parents=True, exist_ok=True)
            (dist / filename).write_bytes(b"MZ standalone")
            (dist / "python312.dll").write_bytes(b"dll")
        return ProcessResult(0, "", "")

    # ---- tiện ích cho test ----
    @property
    def nuitka_calls(self) -> List[List[str]]:
        return [c for c in self.commands if c[:3] == [PYTHON, "-m", "nuitka"]]

    def commands_starting(self, *prefix: str) -> List[List[str]]:
        return [c for c in self.commands if tuple(c[: len(prefix)]) == prefix]

    @property
    def output(self) -> str:
        return "\n".join(self.lines)


def write_app(root: Path, toml_body: str, *, version: str = "0.3.0", name: str = "my-app") -> Path:
    """Dựng một app giả theo chuẩn: pyproject.toml + main.py + .env + .env.example."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nversion = "{version}"\n\n{toml_body}', encoding="utf-8"
    )
    (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (root / ".env").write_text("SECRET=real\n", encoding="utf-8")
    (root / ".env.example").write_text("SECRET=\n", encoding="utf-8")
    return root
