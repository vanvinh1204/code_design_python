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

    def _session_generator(self) -> Generator[Session, None, None]:
        """
        Generator nội bộ duy nhất nắm logic giao dịch:
        commit khi hoàn tất, rollback và ném lại khi có lỗi, luôn đóng session.
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

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Context Manager cho PySide6 / Background Workers:
            with db_manager.session() as session:
                items = session.query(Product).all()
        Tự động commit khi hoàn tất, rollback khi có lỗi và đóng session.
        Với FastAPI, dùng Depends(db_manager.get_db) thay vì session().
        """
        yield from self._session_generator()

    def session_scope(self):
        """[Alias tương thích ngược] Chuyển tiếp tới context manager session()."""
        return self.session()

    def get_db(self) -> Generator[Session, None, None]:
        """
        Generator thuần dùng cho FastAPI Dependency Injection:
            def my_endpoint(db: Session = Depends(db_manager.get_db)):
                ...
        Commit khi endpoint thành công, rollback khi endpoint ném lỗi, luôn đóng session.
        Không dùng get_db() trong khối with; hãy dùng db_manager.session().
        """
        return self._session_generator()
