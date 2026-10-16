import shutil
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Thêm đường dẫn src vào sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sqlalchemy import text
from core_kit.database import DatabaseManager, init_migration_scaffold


def run_migration_e2e_test():
    print("=" * 60)
    print("KIỂM THỬ E2E TÍNH NĂNG MIGRATION (HIGHEST SEAM)")
    print("=" * 60)

    # 1. Tạo thư mục làm việc tạm thời cho test
    temp_dir = Path(tempfile.mkdtemp(prefix="core_kit_migration_test_"))
    print(f"1. Thư mục kiểm thử tạm thời: {temp_dir}")

    try:
        migrations_folder = temp_dir / "migrations"
        versions_folder = migrations_folder / "versions"
        db_file = temp_dir / "app_test.db"
        db_url = f"sqlite:///{db_file}"

        # 2. Sinh template cấu hình Alembic
        print("2. Đang sinh template cấu hình Alembic...")
        init_migration_scaffold(project_dir=temp_dir, script_location="migrations")
        assert (temp_dir / "alembic.ini").exists(), "Thiếu alembic.ini"
        assert (migrations_folder / "env.py").exists(), "Thiếu env.py"
        assert versions_folder.exists(), "Thiếu versions folder"
        print("   -> Đã sinh template thành công.")

        # 3. Tạo file Migration Revision 001 (Tạo bảng device_logs)
        print("3. Tạo Migration Revision 001: Tạo bảng device_logs...")
        rev1_content = """\"\"\"001_initial

Revision ID: 001
Revises: 
Create Date: 2026-10-14

\"\"\"
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'device_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('device_code', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
    )

def downgrade() -> None:
    op.drop_table('device_logs')
"""
        (versions_folder / "001_initial.py").write_text(rev1_content, encoding="utf-8")

        # 4. Chạy migration ban đầu lên 001 thông qua DatabaseManager.migrate()
        print("4. Thực thi db_manager.migrate() lên revision 001...")
        db_manager = DatabaseManager(db_url=db_url)
        db_manager.migrate(script_location=str(migrations_folder))

        # 5. Thêm dữ liệu mẫu vào bảng phiên bản 1
        print("5. Thêm bản ghi mẫu vào cơ sở dữ liệu...")
        with db_manager.session_scope() as session:
            session.execute(
                text("INSERT INTO device_logs (device_code) VALUES (:code)"),
                {"code": "SCANNER-ZEBRA-01"},
            )
            session.execute(
                text("INSERT INTO device_logs (device_code) VALUES (:code)"),
                {"code": "PRINTER-TSC-02"},
            )

        with db_manager.session_scope() as session:
            count = session.execute(text("SELECT count(*) FROM device_logs")).scalar()
            assert count == 2, f"Kỳ vọng 2 bản ghi, thực tế: {count}"
            print(f"   -> Đã ghi nhận {count} bản ghi mẫu.")

        # 6. Tạo file Migration Revision 002: Thêm cột 'status' và 'operator_note' bằng SQLite Batch Mode
        print("6. Tạo Migration Revision 002: Thêm cột mới với SQLite batch mode...")
        rev2_content = """\"\"\"002_add_status_and_note

Revision ID: 002
Revises: 001
Create Date: 2026-10-14

\"\"\"
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table('device_logs') as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(20), server_default='ACTIVE', nullable=False))
        batch_op.add_column(sa.Column('operator_note', sa.Text(), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('device_logs') as batch_op:
        batch_op.drop_column('operator_note')
        batch_op.drop_column('status')
"""
        (versions_folder / "002_add_status_and_note.py").write_text(rev2_content, encoding="utf-8")

        # 7. Chạy migration nâng cấp lên revision 002
        print("7. Thực thi db_manager.migrate() lên revision 002 (head)...")
        db_manager.migrate(script_location=str(migrations_folder))

        # 8. Kiểm chứng schema đã cập nhật và dữ liệu cũ không bị mất
        print("8. Kiểm tra tính toàn vẹn dữ liệu và các cột mới...")
        with db_manager.session_scope() as session:
            records = session.execute(
                text("SELECT id, device_code, status, operator_note FROM device_logs ORDER BY id ASC")
            ).fetchall()

            assert len(records) == 2, f"Kỳ vọng 2 bản ghi sau migration, thực tế: {len(records)}"
            r1, r2 = records[0], records[1]
            print(f"   -> Bản ghi 1: ID={r1[0]} | Code={r1[1]} | Status={r1[2]} | Note={r1[3]}")
            print(f"   -> Bản ghi 2: ID={r2[0]} | Code={r2[1]} | Status={r2[2]} | Note={r2[3]}")

            assert r1[1] == "SCANNER-ZEBRA-01"
            assert r1[2] == "ACTIVE"  # Giá trị mặc định của cột mới
            assert r2[1] == "PRINTER-TSC-02"
            assert r2[2] == "ACTIVE"

            # Cập nhật thử cột mới
            session.execute(
                text("UPDATE device_logs SET operator_note = :note WHERE id = :id"),
                {"note": "Đang hoạt động tốt tại chuyền 1", "id": r1[0]},
            )

        with db_manager.session_scope() as session:
            updated_note = session.execute(
                text("SELECT operator_note FROM device_logs WHERE id = :id"),
                {"id": r1[0]},
            ).scalar()
            assert updated_note == "Đang hoạt động tốt tại chuyền 1"
            print(f"   -> Kiểm tra cập nhật cột mới: '{updated_note}' [OK]")

        print("=" * 60)
        print("-> TẤT CẢ KỊCH BẢN KIỂM THỬ E2E ĐÃ VƯỢT QUA THÀNH CÔNG 100%!")
        print("=" * 60)

    finally:
        # Dọn dẹp thư mục tạm
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("Đã dọn dẹp thư mục kiểm thử tạm.")


if __name__ == "__main__":
    run_migration_e2e_test()
