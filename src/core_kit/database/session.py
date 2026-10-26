from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


class DatabaseManager:
    """
    Quản lý vòng đời kết nối cơ sở dữ liệu và phiên làm việc (Session).
    Cung cấp Seam quản lý phiên chuẩn hóa duy nhất dùng cho cả FastAPI và PySide6.
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
        """
        Khởi tạo toàn bộ các bảng nếu chưa tồn tại.
        Khuyến cáo: Đối với ứng dụng production, ưu tiên dùng 'migrate()' để đồng bộ Alembic revision.
        """
        base_metadata.create_all(bind=self.engine)

    def migrate(
        self,
        script_location: str = "migrations",
        revision: str = "head",
        ini_path: str = None,
    ) -> None:
        """
        Thực thi tự động database migration lên phiên bản chỉ định (mặc định 'head').
        Hữu ích cho Desktop App (PySide6) tự động nâng cấp schema khi khởi chạy theo ADR-0001.
        """
        from core_kit.database.migration import apply_migrations

        apply_migrations(
            db_url=self.db_url,
            script_location=script_location,
            revision=revision,
            ini_path=ini_path,
        )

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Seam quản lý phiên làm việc chuẩn duy nhất (Context Manager).
        Tự động commit khi hoàn tất, rollback khi có lỗi và đóng session.
        Hoạt động hoàn hảo cho cả:
        - PySide6 / Background Workers:
            with db_manager.session() as session:
                items = session.query(Product).all()
        - FastAPI Dependency Injection:
            def my_endpoint(db: Session = Depends(db_manager.session)):
        """
        sess: Session = self.session_factory()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

    def session_scope(self):
        """[Alias tương thích ngược] Chuyển tiếp tới context manager session()."""
        return self.session()

    def get_db(self):
        """[Alias tương thích ngược] Chuyển tiếp tới context manager session()."""
        return self.session()
