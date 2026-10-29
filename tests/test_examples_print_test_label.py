"""Kiểm thử kịch bản kiểm chuẩn examples/print_test_label.py (seam: parse_simple_args(argv), build_payload(config))."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "examples" / "print_test_label.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("print_test_label", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def script():
    return _load_script()


def test_defaults_apply_no_compensation_no_tray_and_rotate_90(script):
    config = script.parse_simple_args([])

    assert config["scale"] == (1.0, 1.0)
    assert config["shift_x"] == 0.0
    assert config["shift_y"] == 0.0
    assert config["tray"] is None
    assert config["rotate"] == 90
    assert config["dry_run"] is False


def test_default_payload_is_pclxl_without_tray_selection(script):
    payload = script.build_payload(script.parse_simple_args([]))

    assert b"@PJL ENTER LANGUAGE = PCLXL\r\n" in payload
    assert b"MEDIASOURCE" not in payload
    assert b"PCL5" not in payload.split(b"@PJL ENTER")[0]


def test_tray_and_host_from_argv_reach_the_payload(script):
    config = script.parse_simple_args(["10.45.1.191", "--tray", "tray2", "--dry-run"])

    assert config["host"] == "10.45.1.191"
    assert config["dry_run"] is True
    assert b"@PJL SET MEDIASOURCE = TRAY2\r\n" in script.build_payload(config)


def test_scale_and_shift_flags_override_defaults(script):
    config = script.parse_simple_args(
        ["--scale", "0.9", "--scale-y", "0.95", "--shift-x", "1.5", "--shift-y", "-2", "--rotate", "0"]
    )

    assert config["scale"] == (0.9, 0.95)
    assert (config["shift_x"], config["shift_y"]) == (1.5, -2.0)
    assert config["rotate"] == 0
