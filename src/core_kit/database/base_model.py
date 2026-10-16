from datetime import datetime
from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Lớp ORM cơ sở kế thừa SQLAlchemy DeclarativeBase."""
    pass


class TimestampMixin:
    """Mixin cung cấp sẵn thời gian tạo và cập nhật bản ghi."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="Thời điểm tạo bản ghi"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="Thời điểm cập nhật bản ghi gần nhất"
    )


class CommonModel(Base, TimestampMixin):
    """
    Model cơ sở chứa khóa chính ID tự tăng và dấu thời gian.
    Mọi bảng nghiệp vụ kế thừa từ model này để đồng nhất cấu trúc.
    """
    __abstract__ = True

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="Khóa chính ID"
    )
