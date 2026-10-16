import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

try:
    from core_kit.database import CommonModel, DatabaseManager
    from core_kit.utils import generate_short_id
    from sqlalchemy import String
    from sqlalchemy.orm import Mapped, mapped_column

    print("=" * 50)
    print("TEST THỬ NGHIỆM: core_kit.database")
    print("=" * 50)

    # Sử dụng SQLite file tạm với mã ngẫu nhiên để test không bị trùng khóa
    db_file = Path(__file__).resolve().parent / "test_demo.db"
    db_url = f"sqlite:///{db_file}"
    db_manager = DatabaseManager(db_url=db_url)

    # 1. Định nghĩa bảng thử nghiệm kế thừa CommonModel
    class InventoryItem(CommonModel):
        __tablename__ = "inventory_items"
        sku: Mapped[str] = mapped_column(String(50), unique=True)
        name: Mapped[str] = mapped_column(String(100))

    # 2. Khởi tạo bảng nếu chưa có
    print("1. Đang khởi tạo bảng...")
    db_manager.create_tables(CommonModel.metadata)

    # 3. Thêm bản ghi mới ngẫu nhiên SKU
    random_suffix = generate_short_id(4)
    print(f"2. Đang thêm dữ liệu mẫu (Mã phiên: {random_suffix})...")
    with db_manager.session_scope() as session:
        item1 = InventoryItem(sku=f"SKU-SCAN-{random_suffix}", name="Máy quét mã vạch 2D")
        item2 = InventoryItem(sku=f"SKU-PRINT-{random_suffix}", name="Máy in tem nhãn nhiệt")
        session.add_all([item1, item2])

    # 4. Đọc dữ liệu ra
    print("3. Đọc danh sách bản ghi mới nhất từ DB:")
    with db_manager.session_scope() as session:
        results = session.query(InventoryItem).order_by(InventoryItem.id.desc()).limit(2).all()
        for r in results:
            print(f"   -> [ID: {r.id}] SKU: {r.sku} | Tên: {r.name} | Tạo lúc: {r.created_at}")

    print("=" * 50)
    print("-> Hoàn tất test database thành công!")

except ImportError as e:
    print(f"[LƯU Ý] Chưa cài sqlalchemy ({e}). Chạy: pip install sqlalchemy")
