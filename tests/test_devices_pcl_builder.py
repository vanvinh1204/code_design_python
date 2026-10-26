"""Kiểm thử bộ tạo lệnh đồ họa PCL 5 và PJL header: PCL5RasterBuilder."""

from PIL import Image
import pytest
from core_kit.devices import PCL5RasterBuilder


def test_pcl_builder_custom_label():
    builder = PCL5RasterBuilder(
        paper_size="CUSTOM",
        width_mm=102.0,
        height_mm=148.0,
        tray="TRAY1",
        feed_direction="SHORTEDGEFEED",
        dpi=300,
        job_name="TEST_CUSTOM_LABEL",
    )

    test_img = Image.new("1", (200, 200), 0)
    builder.add_page(
        image=test_img,
        rotate=90,
        scale=(0.90, 0.94),
        shift_x_mm=1.5,
        shift_y_mm=-1.5,
        auto_center=True,
    )
    payload = builder.build()

    assert payload.startswith(b"\x1b%-12345X@PJL\r\n")
    assert b'@PJL JOB NAME = "TEST_CUSTOM_LABEL"\r\n' in payload
    assert b"@PJL SET PAPER = CUSTOM\r\n" in payload
    assert b"@PJL SET PAPERWIDTH = 2891\r\n" in payload
    assert b"@PJL SET PAPERLENGTH = 4195\r\n" in payload
    assert b"@PJL SET MEDIASOURCE = TRAY1\r\n" in payload
    assert b"@PJL SET SHORTEDGEFEED = ON\r\n" in payload
    assert b"@PJL SET FEEDDIR = SHORTEDGEFEED\r\n" in payload
    assert b"@PJL ENTER LANGUAGE = PCL\r\n" in payload
    assert b"\x1b*t300R" in payload
    assert b"\x1b*r1A" in payload
    assert b"\x1b*rB" in payload
    assert b"\x0c" in payload
    assert payload.endswith(b"\x1b%-12345X@PJL EOJ\r\n\x1b%-12345X")


def test_pcl_builder_standard_a4():
    builder = PCL5RasterBuilder(
        paper_size="A4",
        tray="MPFEEDER",
        feed_direction="LONGEDGEFEED",
        dpi=300,
        job_name="TEST_A4_REPORT",
    )
    assert builder.width_mm == 210.0
    assert builder.height_mm == 297.0

    test_img = Image.new("RGB", (300, 300), (255, 255, 255))
    builder.add_page(image=test_img, rotate=0, scale=1.0)
    payload = builder.build()

    assert b"@PJL SET PAPER = A4\r\n" in payload
    assert b"@PJL SET MEDIASOURCE = MPFEEDER\r\n" in payload
    assert b"@PJL SET SHORTEDGEFEED = OFF\r\n" in payload
    assert b"@PJL SET FEEDDIR = LONGEDGEFEED\r\n" in payload


def test_pcl_builder_bitwise_inversion_and_padding():
    # Ảnh 11x2 pixel: dòng đầu gồm 8 pixel đen, 3 pixel trắng
    img = Image.new("1", (11, 2), 1)  # 1 = Trắng
    for px in range(8):
        img.putpixel((px, 0), 0)  # 0 = Đen

    builder = PCL5RasterBuilder(
        paper_size="CUSTOM",
        width_mm=11 * 25.4 / 300,
        height_mm=2 * 25.4 / 300,
        dpi=300,
    )
    builder.add_page(image=img, rotate=0, scale=1.0, auto_center=False)
    payload = builder.build()

    # Dòng đầu: 8 bit đen (0xFF) + 3 bit trắng (0x00) -> b"\xFF\x00"
    assert b"\x1b*b2W\xff\x00" in payload
    # Dòng thứ hai: toàn bộ trắng -> b"\x00\x00"
    assert b"\x1b*b2W\x00\x00" in payload
