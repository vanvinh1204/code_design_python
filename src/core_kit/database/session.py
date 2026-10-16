from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


class DatabaseManager:
    """
    Quản lý vòng đời kết nối cơ sở dữ liệu và phiên làm việc (Session).
    Hoạt động tốt cho cả FastAPI (Dependency Injection) và PySide6 (Context Manager).
    """

    def __init__(self, db_url: str, echo: bool = False, pool_pre_ping: bool = True):
        self.db_url = db_url

        connect_args = {}
        if db_url.startswith("sqlite"):
            # Cần thiết cho SQLite khi dùng đa luồng (Multi-threading trong PySide6 / FastAPI)
            connect_args["check_same_thread"] = False

        self.engine = create_engine(
            db_url,
            echo=echo,
            pool_pre_ping=pool_pre_ping,
            connect_args=connect_args
        )
        self.session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    def create_tables(self, base_metadata):
        """Khởi tạo toàn bộ các bảng nếu chưa tồn tại."""
        base_metadata.create_all(bind=self.engine)

    def migrate(
        self,
        script_location: str = "migrations",
        revision: str = "head",
        ini_path: str = None,
    ) -> None:
        """
        Thực thi tự động database migration lên phiên bản chỉ định (mặc định 'head').
        Hữu ích cho Desktop App (PySide6) tự động nâng cấp schema khi khởi chạy.
        """
        from core_kit.database.migration import apply_migrations

        apply_migrations(
            db_url=self.db_url,
            script_location=script_location,
            revision=revision,
            ini_path=ini_path,
        )


    def get_db(self) -> Generator[Session, None, None]:
        """
        Dành cho FastAPI Dependency Injection.
        Ví dụ: def my_endpoint(db: Session = Depends(db_manager.get_db))
        """
        session: Session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Dành cho Desktop App (PySide6) hoặc Background Workers.
        Ví dụ:
            with db_manager.session_scope() as session:
                items = session.query(Product).all()
        """
        session: Session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
