"""Menu đánh số đọc qua cổng `ask` (không dùng thư viện ngoài)."""

from __future__ import annotations

from typing import Sequence, Tuple

from core_kit.cli.ports import CorekitError, Ports


def _ask(ports: Ports, prompt: str) -> str:
    try:
        return ports.ask(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        raise CorekitError("Đã hủy.") from None


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
