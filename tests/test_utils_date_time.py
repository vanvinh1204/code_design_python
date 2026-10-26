"""Kiểm thử các hàm tiện ích ngày giờ: date_time."""

from datetime import datetime, timezone
import pytest
from core_kit.utils.date_time import (
    now_utc,
    format_vn_datetime,
    format_vn_date,
    parse_vn_datetime,
)


def test_now_utc_is_timezone_aware():
    dt = now_utc()
    assert dt.tzinfo is not None
    assert dt.tzinfo == timezone.utc


def test_format_vn_datetime_and_date():
    dt = datetime(2026, 10, 26, 14, 30, 45, tzinfo=timezone.utc)
    assert format_vn_datetime(dt) == "26/10/2026 14:30:45"
    assert format_vn_date(dt) == "26/10/2026"
    assert format_vn_datetime(None) == ""
    assert format_vn_date(None) == ""


def test_parse_vn_datetime():
    raw_str = "26/10/2026 09:15:00"
    parsed = parse_vn_datetime(raw_str)
    assert parsed is not None
    assert parsed.year == 2026
    assert parsed.month == 10
    assert parsed.day == 26
    assert parsed.hour == 9
    assert parsed.minute == 15
    assert parsed.second == 0

    assert parse_vn_datetime("invalid-date-string") is None
