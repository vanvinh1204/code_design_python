import os
import sys
from pathlib import Path


def setup_logger(log_dir: str = "logs", log_level: str = "INFO", app_name: str = "app"):
    """
    Khởi tạo hệ thống ghi log tập trung.
    Hỗ trợ xuất ra cả Console và file xoay vòng (rotating file).
    """
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    try:
        from loguru import logger
        logger.remove()

        # Log ra Console với màu sắc
        logger.add(
            sys.stdout,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True
        )

        # Log ra File xoay vòng theo ngày và dung lượng
        log_file_path = os.path.join(log_dir, f"{app_name}_{{time:YYYY-MM-DD}}.log")
        logger.add(
            log_file_path,
            level=log_level,
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

        logger = logging.getLogger(app_name)
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        if not logger.handlers:
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )

            # Console handler
            ch = logging.StreamHandler(sys.stdout)
            ch.setFormatter(formatter)
            logger.addHandler(ch)

            # File handler xoay vòng mỗi ngày
            fh = TimedRotatingFileHandler(
                filename=os.path.join(log_dir, f"{app_name}.log"),
                when="midnight",
                interval=1,
                backupCount=30,
                encoding="utf-8"
            )
            fh.setFormatter(formatter)
            logger.addHandler(fh)

        return logger
