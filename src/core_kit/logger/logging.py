import os
import sys
from pathlib import Path

from core_kit.utils.paths import data_dir


def resolve_log_dir(log_dir: str) -> Path:
    """Thư mục log: đường dẫn tương đối được neo vào Data Dir (``data_dir()``: ``DATA_DIR`` nếu đặt, không thì App Dir); đường dẫn tuyệt đối giữ nguyên."""
    path = Path(log_dir)
    if path.is_absolute():
        return path
    return data_dir() / path


def setup_logger(
    log_dir: str = "logs",
    log_level: str = "INFO",
    app_name: str = "app",
    file_format: str | None = None,
):
    """
    Khởi tạo hệ thống ghi log tập trung.
    Hỗ trợ xuất ra cả Console và file xoay vòng (rotating file).
    """
    log_path = resolve_log_dir(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    default_file_fmt = file_format or "{time:YY.MM.DD HH:mm:ss.SSS} | {level: <8} | {message}"

    try:
        from loguru import logger
        logger.remove()

        # Log ra Console với màu sắc
        logger.add(
            sys.stdout,
            level=log_level,
            format="<green>{time:YY.MM.DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True
        )

        # Log ra File xoay vòng theo ngày và dung lượng
        log_file_path = os.path.join(log_path, f"{app_name}_{{time:YYYY-MM-DD}}.log")
        logger.add(
            log_file_path,
            level=log_level,
            format=default_file_fmt,
            rotation="00:00",
            retention="30 days",
            compression="zip",
            encoding="utf-8",
            enqueue=True
        )
        return logger
    except ImportError:
        # Fallback về thư viện logging tiêu chuẩn nếu chưa cài loguru
        import logging
        from logging.handlers import TimedRotatingFileHandler

        std_logger = logging.getLogger(app_name)
        std_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        if not std_logger.handlers:
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
                datefmt="%y.%m.%d %H:%M:%S"
            )

            # Console handler
            ch = logging.StreamHandler(sys.stdout)
            ch.setFormatter(formatter)
            std_logger.addHandler(ch)

            # File handler xoay vòng mỗi ngày
            fh = TimedRotatingFileHandler(
                filename=os.path.join(log_path, f"{app_name}.log"),
                when="midnight",
                interval=1,
                backupCount=30,
                encoding="utf-8"
            )
            file_formatter = logging.Formatter(
                fmt="%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s",
                datefmt="%y.%m.%d %H:%M:%S"
            )
            fh.setFormatter(file_formatter)
            std_logger.addHandler(fh)

        return std_logger
