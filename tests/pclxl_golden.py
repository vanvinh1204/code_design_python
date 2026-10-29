"""Ảnh kiểm thử hình học và payload golden PCL XL cho golden test của PCLXLRasterBuilder.

Ảnh không dùng font (tránh phụ thuộc font hệ thống) và hoàn toàn tất định:
viền ngoài, viền trong cách mép 5 mm, vạch chia mm ở cạnh trên/trái, chữ thập ở tâm.

Tái tạo fixture (chỉ khi CỐ Ý đổi payload; sau đó phải in lại để operator xác nhận), từ gốc repo:

    PYTHONPATH=src python tests/pclxl_golden.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

from core_kit.devices import PCLXLRasterBuilder

WIDTH_MM = 102.0
HEIGHT_MM = 148.0
DPI = 300
TRAY = "TRAY2"
JOB_NAME = "CORE_KIT_GOLDEN"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "pclxl_golden_102x148_tray2.prn"

LINE_PX = 3  # nét đủ dày để thấy rõ khi in ở 300 dpi


def mm_to_px(mm: float) -> int:
    return int(round(mm * DPI / 25.4))


def golden_image() -> Image.Image:
    """Ảnh 1-bit 102 x 148 mm dọc @300 dpi (1205 x 1748 px), nền trắng, nét đen."""
    width, height = mm_to_px(WIDTH_MM), mm_to_px(HEIGHT_MM)
    image = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(image)

    # Viền ngoài sát mép giấy và viền trong cách mép 5 mm (nét vẽ vào phía trong).
    draw.rectangle([0, 0, width - 1, height - 1], outline=0, width=LINE_PX)
    inset = mm_to_px(5)
    draw.rectangle([inset, inset, width - 1 - inset, height - 1 - inset], outline=0, width=LINE_PX)

    # Vạch chia mm: 1 mm dài 1.5 mm, 5 mm dài 3 mm, 10 mm dài 5 mm.
    def tick_length(mm: int) -> int:
        if mm % 10 == 0:
            return mm_to_px(5)
        if mm % 5 == 0:
            return mm_to_px(3)
        return mm_to_px(1.5)

    for mm in range(1, int(WIDTH_MM)):
        x = mm_to_px(mm)
        draw.line([x, 0, x, tick_length(mm)], fill=0, width=1)
    for mm in range(1, int(HEIGHT_MM)):
        y = mm_to_px(mm)
        draw.line([0, y, tick_length(mm), y], fill=0, width=1)

    # Chữ thập ở tâm, mỗi nhánh 10 mm.
    cx, cy, arm = width // 2, height // 2, mm_to_px(10)
    draw.line([cx - arm, cy, cx + arm, cy], fill=0, width=LINE_PX)
    draw.line([cx, cy - arm, cx, cy + arm], fill=0, width=LINE_PX)
    return image


def build_golden_payload() -> bytes:
    builder = PCLXLRasterBuilder(
        paper_size="CUSTOM", width_mm=WIDTH_MM, height_mm=HEIGHT_MM, tray=TRAY, job_name=JOB_NAME
    )
    return builder.add_page(golden_image()).build()


def regenerate_fixture() -> Path:
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_bytes(build_golden_payload())
    return FIXTURE_PATH


if __name__ == "__main__":
    path = regenerate_fixture()
    print(f"Wrote {path} ({path.stat().st_size} bytes)")
