"""Kiểm thử quy trình tạo scaffold và thực thi migration Alembic: migration.py."""

from pathlib import Path
import pytest
from sqlalchemy import text

from core_kit.database import DatabaseManager, init_migration_scaffold


def test_init_migration_scaffold(tmp_path):
    migrations_dir = tmp_path / "migrations"
    init_migration_scaffold(project_dir=tmp_path, script_location="migrations")

    assert (tmp_path / "alembic.ini").exists()
    assert (migrations_dir / "env.py").exists()
    assert (migrations_dir / "script.py.mako").exists()
    assert (migrations_dir / "versions").is_dir()


def test_database_migration_e2e_execution(tmp_path):
    migrations_folder = tmp_path / "migrations"
    versions_folder = migrations_folder / "versions"
    db_file = tmp_path / "test_mig.db"
    db_url = f"sqlite:///{db_file}"

    # 1. Sinh scaffold
    init_migration_scaffold(project_dir=tmp_path, script_location="migrations")

    # 2. Tạo revision 001
    rev1_content = """\"\"\"001_create_items
Revision ID: 001
Revises: 
Create Date: 2026-10-26
\"\"\"
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'items',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(50), nullable=False)
    )

def downgrade() -> None:
    op.drop_table('items')
"""
    (versions_folder / "001_create_items.py").write_text(rev1_content, encoding="utf-8")

    # 3. Chạy migrate qua DatabaseManager
    db = DatabaseManager(db_url=db_url)
    db.migrate(
        script_location=str(migrations_folder),
        revision="head",
        ini_path=str(tmp_path / "alembic.ini"),
    )

    # 4. Kiểm tra bảng items đã được tạo và ghi nhận version
    with db.session() as session:
        result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='items'")).fetchall()
        assert len(result) == 1

        version = session.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert version == "001"
