"""Kiểm thử bộ tạo lệnh PCL XL raster kèm PJL: PCLXLRasterBuilder (seam: build() -> bytes)."""

from PIL import Image
import pytest
from core_kit.devices import PCLXLRasterBuilder

UEL = b"\x1b%-12345X"


def _label_builder(**kwargs) -> PCLXLRasterBuilder:
    params = dict(paper_size="CUSTOM", width_mm=102.0, height_mm=148.0, job_name="LABEL_JOB")
    params.update(kwargs)
    return PCLXLRasterBuilder(**params)


def test_pjl_envelope_names_job_and_enters_pclxl_without_paper_variables():
    payload = _label_builder().add_page(Image.new("1", (10, 10), 1)).build()

    assert payload.startswith(UEL + b'@PJL\r\n@PJL JOB NAME = "LABEL_JOB"\r\n')
    assert b"@PJL ENTER LANGUAGE = PCLXL\r\n" in payload
    for forbidden in (b"PAPER", b"LCUSTOM", b"SHORTEDGEFEED", b"FEEDDIR", b"DUPLEX", b"MEDIASOURCE"):
        assert forbidden not in payload.split(b") HP-PCL XL")[0]
    assert payload.endswith(UEL + b'@PJL EOJ NAME = "LABEL_JOB"\r\n' + UEL)


def test_tray_is_passed_verbatim_as_pjl_mediasource():
    payload = _label_builder(tray="TRAY2").add_page(Image.new("1", (10, 10), 1)).build()

    assert b'@PJL JOB NAME = "LABEL_JOB"\r\n@PJL SET MEDIASOURCE = TRAY2\r\n@PJL ENTER LANGUAGE = PCLXL\r\n' in payload


def _stream(payload: bytes) -> bytes:
    """Phần luồng PCL XL nằm giữa PJL header và PJL footer."""
    start = payload.index(b"@PJL ENTER LANGUAGE = PCLXL\r\n") + len(b"@PJL ENTER LANGUAGE = PCLXL\r\n")
    end = payload.rindex(UEL + b"@PJL EOJ")
    return payload[start:end]


def test_stream_opens_session_at_dpi_and_closes_it():
    stream = _stream(_label_builder(dpi=300).add_page(Image.new("1", (10, 10), 1)).build())

    assert stream.startswith(b") HP-PCL XL;2;0;")
    after_header = stream[stream.index(b"\n") + 1:]
    # BeginSession: UnitsPerMeasure=(300,300), Measure=eInch, ErrorReport=eErrorPage
    # OpenDataSource: SourceType=eDefaultDataSource, DataOrg=eBinaryLowByteFirst
    assert after_header.startswith(
        b"\xd1\x2c\x01\x2c\x01\xf8\x89" b"\xc0\x00\xf8\x86" b"\xc0\x02\xf8\x8f" b"\x41"
        b"\xc0\x00\xf8\x88" b"\xc0\x01\xf8\x82" b"\x48"
    )
    # EndPage PageCopies=1, CloseDataSource, EndSession
    assert stream.endswith(b"\xc1\x01\x00\xf8\x31\x44" b"\x49\x42")


def test_begin_page_declares_custom_media_size_in_millimetres():
    stream = _stream(_label_builder().add_page(Image.new("1", (10, 10), 1)).build())

    # Orientation=ePortrait, MediaSource=eDefaultSource, CustomMediaSize=(102.0, 148.0) real32,
    # CustomMediaSizeUnits=eMillimeter, BeginPage
    assert (
        b"\xc0\x00\xf8\x28" b"\xc0\x00\xf8\x26"
        b"\xd5\x00\x00\xcc\x42\x00\x00\x14\x43\xf8\x2f" b"\xc0\x01\xf8\x30" b"\x43"
    ) in stream


def _page_images(payload: bytes) -> list[Image.Image]:
    """Giải mã ảnh trang từ các khối BeginImage/ReadImage trong payload (đọc từ byte công khai)."""
    import struct

    images = []
    pos = 0
    while True:
        begin = payload.find(b"\xf8\x67\xb0", pos)
        if begin < 0:
            return images
        # DestinationSize: d1 <width uint16> <height uint16> f8 67
        width, height = struct.unpack("<HH", payload[begin - 4:begin])
        read = payload.index(b"\xf8\x65\xb1\xfa", begin) + 4
        length = struct.unpack("<I", payload[read:read + 4])[0]
        data = payload[read + 4:read + 4 + length]
        padded = length // height
        img = Image.frombytes("1", (padded * 8, height), data).crop((0, 0, width, height))
        images.append(img)
        pos = read + 4 + length


def test_image_is_full_page_canvas_with_rows_padded_to_four_bytes():
    payload = _label_builder(dpi=300).add_page(Image.new("1", (10, 10), 1)).build()

    # 102 x 148 mm @ 300 dpi = 1205 x 1748 px; SourceWidth, SourceHeight, DestinationSize
    assert b"\xc1\xb5\x04\xf8\x6c" b"\xc1\xd4\x06\xf8\x6b" b"\xd1\xb5\x04\xd4\x06\xf8\x67\xb0" in payload
    # ReadImage: StartLine 0, BlockHeight 1748, eNoCompression, data length 1748 * 152 bytes
    assert b"\xc1\x00\x00\xf8\x6d" b"\xc1\xd4\x06\xf8\x63" b"\xc0\x00\xf8\x65\xb1" b"\xfa" + (265696).to_bytes(4, "little") in payload
    # Byte đệm cuối mỗi dòng là trắng
    read = payload.index(b"\xf8\x65\xb1\xfa") + 8
    assert payload[read + 151] == 0xFF


def test_page_sized_image_lands_at_page_origin_and_shift_moves_it():
    # 254 dpi: 1 mm = 10 px
    page = Image.new("1", (200, 300), 1)
    page.putpixel((0, 0), 0)
    builder = _label_builder(width_mm=20.0, height_mm=30.0, dpi=254)

    builder.add_page(page)
    builder.add_page(page, shift_x_mm=3.0, shift_y_mm=1.5)
    unshifted, shifted = _page_images(builder.build())

    assert unshifted.size == (200, 300)
    assert unshifted.getpixel((0, 0)) == 0
    assert shifted.getpixel((30, 15)) == 0
    assert shifted.getpixel((0, 0)) != 0


def _black_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    return img.point(lambda p: 255 - p).getbbox()


def test_rotation_turns_content_clockwise_and_swaps_its_dimensions():
    content = Image.new("1", (100, 50), 1)
    content.paste(0, (0, 0, 10, 10))  # ô đen ở góc trên-trái
    builder = _label_builder(width_mm=20.0, height_mm=20.0, dpi=254)

    builder.add_page(content, auto_center=False)
    builder.add_page(content, rotate=90, auto_center=False)
    upright, rotated = _page_images(builder.build())

    assert _black_bbox(upright) == (0, 0, 10, 10)
    # Xoay 90° theo chiều kim đồng hồ: ảnh 100x50 thành 50x100, góc trên-trái sang góc trên-phải
    assert _black_bbox(rotated) == (40, 0, 50, 10)


def test_scale_resizes_content_uniformly_or_per_axis():
    content = Image.new("1", (100, 100), 0)
    builder = _label_builder(width_mm=20.0, height_mm=20.0, dpi=254)

    builder.add_page(content, scale=0.5, auto_center=False)
    builder.add_page(content, scale=(0.5, 1.0), auto_center=False)
    uniform, per_axis = _page_images(builder.build())

    assert _black_bbox(uniform) == (0, 0, 50, 50)
    assert _black_bbox(per_axis) == (0, 0, 50, 100)


def test_auto_center_places_content_in_the_middle_of_the_page():
    payload = _label_builder(width_mm=20.0, height_mm=20.0, dpi=254).add_page(Image.new("1", (100, 50), 0)).build()

    assert _black_bbox(_page_images(payload)[0]) == (50, 75, 150, 125)


@pytest.mark.parametrize(
    "paper, expected_size",
    [
        # real32 little-endian: 210.0 = 0x43520000, 297.0 = 0x43948000
        ("A4", b"\x00\x00\x52\x43\x00\x80\x94\x43"),
        # 105.0 = 0x42D20000, 148.0 = 0x43140000
        ("a6", b"\x00\x00\xd2\x42\x00\x00\x14\x43"),
    ],
)
def test_standard_paper_name_is_declared_through_custom_media_size(paper, expected_size):
    payload = PCLXLRasterBuilder(paper_size=paper).add_page(Image.new("1", (10, 10), 1)).build()

    assert b"\xd5" + expected_size + b"\xf8\x2f" b"\xc0\x01\xf8\x30" b"\x43" in payload


def test_multiple_pages_share_one_session():
    blank = Image.new("1", (10, 10), 1)
    stream = _stream(_label_builder().add_page(blank).add_page(blank).add_page(blank).build())

    begin_page = b"\xc0\x01\xf8\x30\x43"
    end_page = b"\xc1\x01\x00\xf8\x31\x44"
    assert stream.count(begin_page) == 3
    assert stream.count(end_page) == 3
    assert stream.count(b"\xf8\x8f\x41") == 1  # một BeginSession
    assert stream.endswith(end_page + b"\x49\x42")


def test_reset_clears_pages_and_returns_builder():
    builder = _label_builder().add_page(Image.new("1", (10, 10), 1))

    assert builder.reset() is builder
    with pytest.raises(ValueError):
        builder.build()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"paper_size": "B99"},
        {"paper_size": "CUSTOM"},
        {"paper_size": "CUSTOM", "width_mm": 102.0},
        {"paper_size": "CUSTOM", "height_mm": 148.0},
    ],
)
def test_invalid_paper_raises_value_error(kwargs):
    with pytest.raises(ValueError):
        PCLXLRasterBuilder(**kwargs)


@pytest.mark.parametrize(
    "page_kwargs",
    [
        {"scale": 0},
        {"scale": -1.0},
        {"scale": (1.0, 0.0)},
        {"scale": (1.0,)},
        {"scale": (1.0, 1.0, 1.0)},
        {"rotate": 45},
    ],
)
def test_invalid_page_layout_raises_value_error(page_kwargs):
    with pytest.raises(ValueError):
        _label_builder().add_page(Image.new("1", (10, 10), 1), **page_kwargs)


@pytest.mark.parametrize(
    "content",
    [
        Image.new("RGB", (40, 40), (0, 0, 0)),
        Image.new("L", (40, 40), 0),
        Image.new("RGBA", (40, 40), (0, 0, 0, 255)),
    ],
)
def test_any_pillow_mode_is_converted_to_one_bit(content):
    payload = _label_builder(width_mm=20.0, height_mm=20.0, dpi=254).add_page(content, auto_center=False).build()

    assert _black_bbox(_page_images(payload)[0]) == (0, 0, 40, 40)


def test_build_without_pages_raises_value_error():
    with pytest.raises(ValueError):
        _label_builder().build()
