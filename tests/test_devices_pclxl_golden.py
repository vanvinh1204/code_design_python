"""Golden test khóa payload PCL XL đã kiểm chứng trên phần cứng (seam: PCLXLRasterBuilder.build() -> bytes).

Fixture `tests/fixtures/pclxl_golden_102x148_tray2.prn` được dựng từ ảnh hình học không dùng font
(`pclxl_golden.golden_image()`: viền ngoài, viền trong cách mép 5 mm, vạch chia mm ở cạnh trên/trái,
dấu chữ thập ở tâm; 102 x 148 mm dọc @300 dpi) với paper CUSTOM 102 x 148, tray "TRAY2",
job_name "CORE_KIT_GOLDEN", còn lại mặc định.

Chỉ tái tạo fixture khi CỐ Ý thay đổi payload (và phải in lại để operator xác nhận căn lề ±2 mm),
chạy từ gốc repo:

    PYTHONPATH=src python tests/pclxl_golden.py
"""

from pclxl_golden import FIXTURE_PATH, mm_to_px, build_golden_payload, golden_image


def test_golden_image_is_102x148mm_portrait_at_300dpi_with_border_and_centre_cross():
    image = golden_image()

    assert image.mode == "1"
    assert image.size == (1205, 1748)
    # Viền ngoài ở cả bốn góc, viền trong cách mép 5 mm (59 px), tâm có chữ thập.
    for xy in [(0, 0), (1204, 0), (0, 1747), (1204, 1747), (59, 59), (1145, 1688), (602, 874)]:
        assert image.getpixel(xy) == 0, xy
    assert image.getpixel((300, 300)) == 1
    assert mm_to_px(5) == 59


def test_golden_image_is_deterministic():
    assert golden_image().tobytes() == golden_image().tobytes()


def test_build_reproduces_hardware_verified_fixture_byte_for_byte():
    expected = FIXTURE_PATH.read_bytes()

    assert build_golden_payload() == expected
