import sys
from pathlib import Path
from typing import Optional, Union

from alembic import command
from alembic.config import Config
from loguru import logger

from core_kit.database.base_model import Base


ALEMBIC_INI_TEMPLATE = """# A generic, single database configuration.

[alembic]
script_location = {script_location}
prepend_sys_path = .
version_path_separator = os
path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""

ENV_PY_TEMPLATE = '''import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Đảm bảo đường dẫn gốc của project có thể import được core_kit và models
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core_kit.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Chạy migration ở chế độ offline (sinh SQL script)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Chạy migration trực tiếp kết nối tới cơ sở dữ liệu."""
    connectable = config.attributes.get("connection", None)

    if connectable is None:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        # SQLite cần bật render_as_batch=True để hỗ trợ ALTER TABLE / DROP COLUMN
        is_sqlite = connection.dialect.name == "sqlite"
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''

SCRIPT_MAKO_TEMPLATE = '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
'''


def resolve_script_location(script_location: Union[str, Path] = "migrations") -> Path:
    """
    Phân giải đường dẫn thư mục migration script.
    Hỗ trợ cả môi trường phát triển lẫn môi trường đóng gói (PyInstaller / cx_Freeze).
    """
    path_obj = Path(script_location)
    if path_obj.is_absolute() and path_obj.exists():
        return path_obj

    # 1. Kiểm tra môi trường đóng gói (Frozen application / PyInstaller)
    if getattr(sys, "frozen", False):
        # Khi đóng gói bằng PyInstaller một file (--onefile), tài nguyên nằm trong _MEIPASS
        if hasattr(sys, "_MEIPASS"):
            meipass_path = Path(sys._MEIPASS) / path_obj
            if meipass_path.exists():
                return meipass_path

        # Khi đóng gói dạng thư mục (--onedir), tài nguyên nằm cùng thư mục file .exe
        exe_dir_path = Path(sys.executable).resolve().parent / path_obj
        if exe_dir_path.exists():
            return exe_dir_path

    # 2. Kiểm tra đường dẫn tương đối so với thư mục hiện tại (CWD)
    cwd_path = Path.cwd() / path_obj
    if cwd_path.exists():
        return cwd_path.resolve()

    return path_obj.resolve()


def init_migration_scaffold(
    project_dir: Union[str, Path] = ".",
    script_location: str = "migrations",
    overwrite: bool = False,
) -> None:
    """
    Khởi tạo template cấu hình Alembic chuẩn cho dự án.
    Tạo sẵn alembic.ini, env.py (kết nối Base metadata và SQLite batch mode), script.py.mako.
    """
    root = Path(project_dir).resolve()
    migrations_dir = root / script_location
    versions_dir = migrations_dir / "versions"

    migrations_dir.mkdir(parents=True, exist_ok=True)
    versions_dir.mkdir(parents=True, exist_ok=True)

    # 1. Tạo file alembic.ini
    ini_file = root / "alembic.ini"
    if not ini_file.exists() or overwrite:
        ini_content = ALEMBIC_INI_TEMPLATE.format(script_location=script_location)
        ini_file.write_text(ini_content, encoding="utf-8")
        logger.info(f"Đã tạo file cấu hình: {ini_file}")

    # 2. Tạo file env.py
    env_file = migrations_dir / "env.py"
    if not env_file.exists() or overwrite:
        env_file.write_text(ENV_PY_TEMPLATE, encoding="utf-8")
        logger.info(f"Đã tạo file cấu hình môi trường: {env_file}")

    # 3. Tạo file script.py.mako
    mako_file = migrations_dir / "script.py.mako"
    if not mako_file.exists() or overwrite:
        mako_file.write_text(SCRIPT_MAKO_TEMPLATE, encoding="utf-8")
        logger.info(f"Đã tạo file template script: {mako_file}")


def get_alembic_config(
    db_url: Optional[str] = None,
    script_location: Union[str, Path] = "migrations",
    ini_path: Optional[Union[str, Path]] = None,
) -> Config:
    """
    Khởi tạo đối tượng Alembic Config.
    Nếu không có file alembic.ini vật lý, tự động thiết lập cấu hình bộ nhớ để chạy programmatic.
    """
    resolved_script_path = resolve_script_location(script_location)

    if ini_path and Path(ini_path).exists():
        config = Config(str(ini_path))
    else:
        # Tìm file alembic.ini trong thư mục hiện tại hoặc cùng cấp thư mục migrations
        default_ini = resolved_script_path.parent / "alembic.ini"
        if default_ini.exists():
            config = Config(str(default_ini))
        else:
            config = Config()

    # Luôn gán đường dẫn script tuyệt đối đã phân giải
    config.set_main_option("script_location", str(resolved_script_path))

    if db_url:
        config.set_main_option("sqlalchemy.url", db_url)

    return config


def apply_migrations(
    db_url: str,
    script_location: Union[str, Path] = "migrations",
    revision: str = "head",
    ini_path: Optional[Union[str, Path]] = None,
) -> None:
    """
    Thực thi migration tự động lên bản revision chỉ định (mặc định 'head').
    Phù hợp gọi khi khởi động ứng dụng Desktop (PySide6) hoặc Web Backend (FastAPI).
    """
    resolved_script_path = resolve_script_location(script_location)
    if not resolved_script_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy thư mục migration tại: '{resolved_script_path}'. "
            f"Vui lòng chạy 'init_migration_scaffold()' để tạo cấu trúc ban đầu."
        )

    logger.info(f"Đang thực thi database migration [{revision}] cho CSDL: {db_url}")
    try:
        config = get_alembic_config(
            db_url=db_url,
            script_location=resolved_script_path,
            ini_path=ini_path,
        )
        command.upgrade(config, revision)
        logger.info(f"Database migration [{revision}] hoàn tất thành công.")
    except Exception as e:
        logger.error(f"Lỗi khi thực thi database migration: {e}")
        raise


def create_migration(
    message: str,
    db_url: Optional[str] = None,
    script_location: Union[str, Path] = "migrations",
    autogenerate: bool = True,
    ini_path: Optional[Union[str, Path]] = None,
) -> None:
    """
    Tạo một revision migration mới (tự động so sánh model hoặc migration rỗng).
    """
    resolved_script_path = resolve_script_location(script_location)
    config = get_alembic_config(
        db_url=db_url,
        script_location=resolved_script_path,
        ini_path=ini_path,
    )
    logger.info(f"Đang tạo revision migration mới: '{message}'...")
    command.revision(config, message=message, autogenerate=autogenerate)
    logger.info(f"Đã tạo revision '{message}' thành công.")
