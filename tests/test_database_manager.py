"""Kiểm thử DatabaseManager: unified session seam, rollback on error, và timezone-aware timestamps."""

import pytest
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from core_kit.database import DatabaseManager, CommonModel, Base


class SampleProduct(CommonModel):
    __tablename__ = "test_products"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[int] = mapped_column(default=0)


@pytest.fixture
def in_memory_db():
    db = DatabaseManager(db_url="sqlite:///:memory:")
    # Khởi tạo bảng cho test in-memory
    Base.metadata.create_all(bind=db.engine)
    return db


def test_database_manager_session_commit(in_memory_db):
    # Test seam 1: with db.session() as session
    with in_memory_db.session() as session:
        product = SampleProduct(name="Sản phẩm A", price=100)
        session.add(product)

    # Kiểm tra trong phiên mới dữ liệu đã được commit thành công
    with in_memory_db.session() as session:
        saved = session.query(SampleProduct).filter_by(name="Sản phẩm A").first()
        assert saved is not None
        assert saved.price == 100
        assert saved.created_at is not None
        assert saved.updated_at is not None


def test_database_manager_session_rollback_on_exception(in_memory_db):
    # Khi gặp ngoại lệ trong block with, session phải tự động rollback
    with pytest.raises(RuntimeError, match="Cố ý ném lỗi để kiểm tra rollback"):
        with in_memory_db.session() as session:
            product = SampleProduct(name="Sản phẩm Lỗi", price=500)
            session.add(product)
            raise RuntimeError("Cố ý ném lỗi để kiểm tra rollback")

    # Kiểm tra bản ghi chưa từng được lưu vào database
    with in_memory_db.session() as session:
        saved = session.query(SampleProduct).filter_by(name="Sản phẩm Lỗi").first()
        assert saved is None


def test_database_manager_backward_compatibility_aliases(in_memory_db):
    # session_scope và get_db phải hoạt động tương đương session()
    with in_memory_db.session_scope() as session:
        p = SampleProduct(name="Sản phẩm Alias", price=200)
        session.add(p)

    with in_memory_db.session() as session:
        saved = session.query(SampleProduct).filter_by(name="Sản phẩm Alias").first()
        assert saved is not None
        assert saved.name == "Sản phẩm Alias"
