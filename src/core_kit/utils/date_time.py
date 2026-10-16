from datetime import datetime, timezone
from typing import Optional


def now_utc() -> datetime:
    """Lấy thời điểm hiện tại theo chuẩn UTC."""
    return datetime.now(timezone.utc)


def format_vn_datetime(dt: Optional[datetime]) -> str:
    """Format đối tượng datetime sang định dạng tiếng Việt: DD/MM/YYYY HH:MM:SS."""
    if dt is None:
        return ""
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def format_vn_date(dt: Optional[datetime]) -> str:
    """Format đối tượng datetime sang định dạng ngày tiếng Việt: DD/MM/YYYY."""
    if dt is None:
        return ""
    return dt.strftime("%d/%m/%Y")


def parse_vn_datetime(dt_str: str) -> Optional[datetime]:
    """Parse chuỗi DD/MM/YYYY HH:MM:SS thành datetime."""
    try:
        return datetime.strptime(dt_str.strip(), "%d/%m/%Y %H:%M:%S")
    except ValueError:
        return None
