"""
Module điều khiển máy in laser mạng qua chuẩn PCL 5 Raster và Printer Job Language (PJL).
Cung cấp khả năng in trực tiếp qua RAW TCP Socket (cổng 9100) mà không cần cài đặt driver OS.
"""

import io
import struct
import warnings
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union


class PCL5RasterBuilder:
    """
    Trình dựng lệnh và đồ họa raster PCL 5 kèm header/footer PJL.
    Hỗ trợ cả kích thước trang tiêu chuẩn (A4, Letter) và kích thước tùy chỉnh (Custom mm).
    Tự động chuẩn hóa ảnh (xoay, co giãn tránh lề cơ khí, căn giữa, dịch chuyển mm).

    .. deprecated::
        Dùng `PCLXLRasterBuilder` thay thế. PCL 5 không khai báo được khổ giấy tùy chỉnh
        trên firmware Printer Family Brother (khổ CUSTOM bị bỏ qua), trong khi PCL XL
        khai báo qua `CustomMediaSize` hoạt động trên cả Lexmark và Brother.
    """

    STANDARD_PAPER_SIZES: dict[str, tuple[float, float]] = {
        "A4": (210.0, 297.0),
        "A5": (148.0, 210.0),
        "LETTER": (215.9, 279.4),
        "LEGAL": (215.9, 355.6),
        "EXECUTIVE": (184.1, 266.7),
    }

    def __init__(
        self,
        paper_size: str = "CUSTOM",
        width_mm: Optional[float] = None,
        height_mm: Optional[float] = None,
        tray: str = "TRAY1",
        feed_direction: str = "SHORTEDGEFEED",
        dpi: int = 300,
        job_name: str = "PCL_PRINT_JOB",
    ):
        warnings.warn(
            "PCL5RasterBuilder đã lỗi thời (không khai báo được khổ tùy chỉnh trên firmware "
            "Brother); hãy dùng PCLXLRasterBuilder.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.paper_size = paper_size.upper()
        self.tray = tray.upper() if tray else "TRAY1"
        self.feed_direction = feed_direction.upper() if feed_direction else ""
        self.dpi = dpi
        self.job_name = job_name

        # Xác định kích thước trang tính bằng mm
        if self.paper_size in self.STANDARD_PAPER_SIZES:
            std_w, std_h = self.STANDARD_PAPER_SIZES[self.paper_size]
            self.width_mm = width_mm if width_mm is not None else std_w
            self.height_mm = height_mm if height_mm is not None else std_h
        else:
            self.paper_size = "CUSTOM"
            self.width_mm = width_mm if width_mm is not None else 102.0
            self.height_mm = height_mm if height_mm is not None else 148.0

        # Kích thước khung vẽ vật lý tính theo điểm ảnh (pixels)
        self.canvas_width_px = int(round(self.width_mm * self.dpi / 25.4))
        self.canvas_height_px = int(round(self.height_mm * self.dpi / 25.4))

        self.pages_pcl_data: list[bytes] = []

    def reset(self) -> "PCL5RasterBuilder":
        """Xóa toàn bộ các trang đã thêm vào buffer."""
        self.pages_pcl_data.clear()
        return self

    def add_page(
        self,
        image: Any,
        rotate: int = 0,
        scale: float | tuple[float, float] = (0.89, 0.94),
        shift_x_mm: float = 0.0,
        shift_y_mm: float = 0.0,
        auto_center: bool = True,
    ) -> "PCL5RasterBuilder":
        """
        Nạp một trang ảnh vào tác vụ in PCL 5.

        Args:
            image: Đối tượng PIL.Image.Image, đường dẫn file (str/Path) hoặc dữ liệu bytes ảnh.
            rotate: Góc xoay theo chiều kim đồng hồ (0, 90, 180, 270).
            scale: Hệ số tỷ lệ co giãn (mặc định (0.89, 0.94) để bù trừ lề cấm cơ khí và bảo toàn toàn bộ nội dung).
            shift_x_mm: Độ dịch chuyển ngang theo mm (mặc định -5.0 mm để bù trừ lề logic PCL 5 và định tâm khay nạp).
            shift_y_mm: Độ dịch chuyển dọc theo mm (dương = xuống dưới, âm = lên trên).
            auto_center: Tự động căn giữa ảnh vào khổ giấy trước khi áp dụng shift.
        """
        try:
            from PIL import Image
        except ImportError:
            raise ImportError(
                "Thư viện 'pillow' chưa được cài đặt. Vui lòng cài đặt qua 'pip install pillow>=10.0.0' "
                "hoặc 'pip install core_kit[devices]'."
            )

        if rotate not in (0, 90, 180, 270):
            raise ValueError(f"Góc xoay không hợp lệ: {rotate}. Chỉ hỗ trợ các góc 0, 90, 180, 270 độ.")

        if isinstance(scale, (tuple, list)):
            if len(scale) != 2:
                raise ValueError(f"scale dạng tuple/list phải có đúng 2 phần tử (scale_x, scale_y), nhận được: {scale}")
            scale_x, scale_y = float(scale[0]), float(scale[1])
        else:
            scale_x = scale_y = float(scale)

        if scale_x <= 0 or scale_y <= 0:
            raise ValueError(f"Hệ số co giãn (scale) phải lớn hơn 0, nhận được: scale_x={scale_x}, scale_y={scale_y}")

        # Nạp ảnh từ các định dạng đầu vào hỗ trợ
        if isinstance(image, (str, Path)):
            img = Image.open(image)
        elif hasattr(image, "copy") and hasattr(image, "resize"):
            img = image.copy()
        elif isinstance(image, (bytes, bytearray)):
            img = Image.open(io.BytesIO(image))
        else:
            raise TypeError(f"Kiểu dữ liệu ảnh không được hỗ trợ: {type(image)}")

        # 1. Xoay ảnh theo tray feed orientation
        if rotate != 0:
            img = img.rotate(-rotate if hasattr(Image, "Transpose") else rotate, expand=True)

        # 2. Co giãn tỷ lệ (Scale)
        if scale_x != 1.0 or scale_y != 1.0:
            new_w = max(1, int(round(img.width * scale_x)))
            new_h = max(1, int(round(img.height * scale_y)))
            resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.BICUBIC)
            img = img.resize((new_w, new_h), resample=resample)

        # 3. Chuyển đổi sang ảnh đơn sắc 1-bit (Monochrome)
        if img.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        if img.mode != "1":
            img = img.convert("L").point(lambda p: 255 if p > 128 else 0, mode="1")

        # 4. Căn chỉnh vị trí trên khổ giấy vật lý
        canvas = Image.new("1", (self.canvas_width_px, self.canvas_height_px), 1)  # 1 = Trắng
        shift_x_px = int(round(shift_x_mm * self.dpi / 25.4))
        shift_y_px = int(round(shift_y_mm * self.dpi / 25.4))

        if auto_center:
            pos_x = (self.canvas_width_px - img.width) // 2 + shift_x_px
            pos_y = (self.canvas_height_px - img.height) // 2 + shift_y_px
        else:
            pos_x = shift_x_px
            pos_y = shift_y_px

        canvas.paste(img, (pos_x, pos_y))

        # 5. Đóng gói raster scanline PCL 5 kèm nghịch đảo bit (Bitwise Inversion)
        raw_bytes = canvas.tobytes()
        row_len = (self.canvas_width_px + 7) // 8
        rem_bits = self.canvas_width_px % 8
        last_byte_mask = ((0xFF << (8 - rem_bits)) & 0xFF) if rem_bits != 0 else 0xFF

        page_buffer = bytearray()
        # Khởi tạo trang PCL: thiết lập nguồn cấp giấy, khổ trang, triệt tiêu lề mặc định và đặt con trỏ tại (0,0)

        # Chọn nguồn cấp giấy PCL 5 (Paper Source - ESC & l <n> H) theo chuẩn LJ4
        tray_upper = self.tray.upper().strip() if self.tray else ""
        if tray_upper in ("TRAY1", "CASSETTE1", "TRAY 1", "DRAWER1"):
            page_buffer.extend(b"\x1b&l1H")       # Tray 1 / Khay gầm chính chuẩn LJ4
        elif tray_upper in ("TRAY2", "CASSETTE2", "TRAY 2", "DRAWER2"):
            page_buffer.extend(b"\x1b&l5H")       # Tray 2 / Khay phụ mở rộng
        elif tray_upper in ("MPFEEDER", "MP", "BYPASS", "MANUAL", "MULTI-PURPOSE", "MPTRAY"):
            page_buffer.extend(b"\x1b&l2H")       # MP Tray / Khay đa năng Bypass
        elif tray_upper in ("AUTO", "AUTOSEL"):
            page_buffer.extend(b"\x1b&l7H")       # Auto Select
        elif tray_upper.isdigit():
            page_buffer.extend(f"\x1b&l{tray_upper}H".encode("latin1"))

        if self.paper_size == "CUSTOM":
            page_buffer.extend(b"\x1b&l101A")     # Paper size: Custom (101A trong PCL 5)
        elif self.paper_size == "A4":
            page_buffer.extend(b"\x1b&l26A")
        elif self.paper_size == "A5":
            page_buffer.extend(b"\x1b&l25A")
        elif self.paper_size == "LETTER":
            page_buffer.extend(b"\x1b&l2A")
        elif self.paper_size == "LEGAL":
            page_buffer.extend(b"\x1b&l3A")
        elif self.paper_size == "EXECUTIVE":
            page_buffer.extend(b"\x1b&l1A")

        page_buffer.extend(b"\x1b&l0O")           # Orientation: Portrait
        page_buffer.extend(b"\x1b&l0E")           # Top margin: 0 lines
        page_buffer.extend(b"\x1b&l0L")           # Perforation skip: disable (không tự thụt lề 1/2-3/4 inch)
        page_buffer.extend(b"\x1b*p0x0Y")         # Di chuyển con trỏ in về tuyệt đối tọa độ gốc (0, 0)
        page_buffer.extend(f"\x1b*t{self.dpi}R".encode("latin1"))  # Thiết lập độ phân giải DPI
        page_buffer.extend(b"\x1b*r1A")           # Bắt đầu đồ họa raster tại vị trí con trỏ

        for y in range(self.canvas_height_px):
            row = raw_bytes[y * row_len : (y + 1) * row_len]
            # Nghịch đảo bit: 0 (trắng) trong PIL thành 0 (không phun mực) trong PCL
            # 1 (đen) trong PIL thành 1 (phun hạt mực toner) trong PCL
            inverted_row = bytearray(b ^ 0xFF for b in row)
            if rem_bits != 0:
                inverted_row[-1] &= last_byte_mask

            # Ghi dòng raster: ESC * b <len> W <data>
            page_buffer.extend(f"\x1b*b{len(inverted_row)}W".encode("latin1"))
            page_buffer.extend(inverted_row)

        # Kết thúc đồ họa raster và đẩy trang (Form Feed)
        page_buffer.extend(b"\x1b*rB")
        page_buffer.extend(b"\x0c")

        self.pages_pcl_data.append(bytes(page_buffer))
        return self

    def build(self) -> bytes:
        """
        Biên dịch toàn bộ công việc in thành luồng byte nhị phân sẵn sàng gửi qua RAW socket.
        Bao gồm header cấu hình PJL, khối thân dữ liệu đồ họa PCL 5 và footer kết thúc PJL.
        """
        # Header PJL
        header_lines = [
            "\x1b%-12345X@PJL",
            f'@PJL JOB NAME = "{self.job_name}"',
            "@PJL SET DUPLEX = OFF",
        ]

        if self.tray:
            header_lines.append(f"@PJL SET PAPERSOURCE = {self.tray}")
            header_lines.append(f"@PJL SET MEDIASOURCE = {self.tray}")

        if self.paper_size == "CUSTOM":
            width_decipoints = int(round(self.width_mm * 720.0 / 25.4))
            height_decipoints = int(round(self.height_mm * 720.0 / 25.4))
            w_mm = int(round(self.width_mm))
            h_mm = int(round(self.height_mm))

            header_lines.append("@PJL SET PAPER = CUSTOM")
            # Cú pháp chuẩn HP LaserJet (decipoints: 1/720 inch)
            header_lines.append(f"@PJL SET PAPERWIDTH = {width_decipoints}")
            header_lines.append(f"@PJL SET PAPERLENGTH = {height_decipoints}")
            # Cú pháp chuẩn Fujifilm ApeosPort / Lexmark engine (Millimeters & Custom dimensions)
            header_lines.append("@PJL SET LCUSTOMPAPERUNITS = MILLIMETERS")
            header_lines.append(f"@PJL SET LCUSTOMPAPERWIDTH = {w_mm}")
            header_lines.append(f"@PJL SET LCUSTOMPAPERHEIGHT = {h_mm}")
            if self.feed_direction in ("SHORTEDGEFEED", "SHORTEDGE") or not self.feed_direction:
                header_lines.append("@PJL SET LCUSTOMPAPERFEED = SHORTEDGE")
            elif self.feed_direction in ("LONGEDGEFEED", "LONGEDGE"):
                header_lines.append("@PJL SET LCUSTOMPAPERFEED = LONGEDGE")
        else:
            header_lines.append(f"@PJL SET PAPER = {self.paper_size}")

        if self.feed_direction == "SHORTEDGEFEED":
            header_lines.append("@PJL SET SHORTEDGEFEED = ON")
            header_lines.append("@PJL SET FEEDDIR = SHORTEDGEFEED")
        elif self.feed_direction == "LONGEDGEFEED":
            header_lines.append("@PJL SET SHORTEDGEFEED = OFF")
            header_lines.append("@PJL SET FEEDDIR = LONGEDGEFEED")
        elif self.feed_direction:
            header_lines.append(f"@PJL SET FEEDDIR = {self.feed_direction}")

        header_lines.append("@PJL ENTER LANGUAGE = PCL")
        header_bytes = ("\r\n".join(header_lines) + "\r\n").encode("latin1")

        # Thân trang PCL
        body_bytes = b"".join(self.pages_pcl_data)

        # Footer PJL kết thúc tác vụ (EOJ) và thoát UEL
        footer_lines = [
            "\x1b%-12345X@PJL EOJ",
            "\x1b%-12345X",
        ]
        footer_bytes = "\r\n".join(footer_lines).encode("latin1")

        return header_bytes + body_bytes + footer_bytes


class PCLXLRasterBuilder:
    """
    Trình dựng tác vụ in raster PCL XL (PCL 6) bọc trong PJL.
    Khổ giấy luôn được khai báo qua `CustomMediaSize` (mm), cách duy nhất đã kiểm chứng
    trên cả Printer Family Lexmark (4020SD) và Brother (4620 SDW).
    """

    UEL = b"\x1b%-12345X"

    # Khổ chuẩn (mm, dọc) — mọi khổ đều được gửi qua CustomMediaSize, không dùng enum MediaSize.
    STANDARD_PAPER_SIZES: dict[str, tuple[float, float]] = {
        **PCL5RasterBuilder.STANDARD_PAPER_SIZES,
        "A6": (105.0, 148.0),
    }

    def __init__(
        self,
        paper_size: str = "CUSTOM",
        width_mm: Optional[float] = None,
        height_mm: Optional[float] = None,
        tray: Optional[str] = None,
        dpi: int = 300,
        job_name: str = "PCLXL_PRINT_JOB",
    ):
        self.paper_size = paper_size.upper()
        if self.paper_size == "CUSTOM":
            if width_mm is None or height_mm is None:
                raise ValueError("paper_size='CUSTOM' bắt buộc phải có cả width_mm và height_mm.")
            self.width_mm, self.height_mm = float(width_mm), float(height_mm)
        elif self.paper_size in self.STANDARD_PAPER_SIZES:
            self.width_mm, self.height_mm = self.STANDARD_PAPER_SIZES[self.paper_size]
        else:
            supported = ", ".join(["CUSTOM", *self.STANDARD_PAPER_SIZES])
            raise ValueError(f"Khổ giấy không hỗ trợ: {paper_size}. Hỗ trợ: {supported}.")
        self.tray = tray
        self.dpi = dpi
        self.job_name = job_name
        self.pages: list[bytes] = []

        self.canvas_width_px = int(round(self.width_mm * self.dpi / 25.4))
        self.canvas_height_px = int(round(self.height_mm * self.dpi / 25.4))

    def reset(self) -> "PCLXLRasterBuilder":
        """Xóa toàn bộ các trang đã thêm."""
        self.pages.clear()
        return self

    def add_page(
        self,
        image: Any,
        rotate: int = 0,
        scale: float | tuple[float, float] = 1.0,
        shift_x_mm: float = 0.0,
        shift_y_mm: float = 0.0,
        auto_center: bool = True,
    ) -> "PCLXLRasterBuilder":
        """
        Nạp một trang ảnh vào tác vụ in PCL XL.

        Args:
            image: Ảnh Pillow bất kỳ chế độ màu; được chuyển sang 1-bit.
            rotate: Góc xoay theo chiều kim đồng hồ (0, 90, 180, 270).
            scale: Hệ số co giãn đồng nhất hoặc (scale_x, scale_y). Mặc định 1.0 (không bù trừ).
            shift_x_mm: Dịch ngang theo mm (dương = sang phải).
            shift_y_mm: Dịch dọc theo mm (dương = xuống dưới).
            auto_center: Căn giữa ảnh trên khổ giấy trước khi áp dụng shift.
        """
        from PIL import Image

        if rotate not in (0, 90, 180, 270):
            raise ValueError(f"Góc xoay không hợp lệ: {rotate}. Chỉ hỗ trợ các góc 0, 90, 180, 270 độ.")
        if isinstance(scale, (tuple, list)):
            if len(scale) != 2:
                raise ValueError(f"scale dạng tuple/list phải có đúng 2 phần tử (scale_x, scale_y), nhận được: {scale}")
            scale_x, scale_y = float(scale[0]), float(scale[1])
        else:
            scale_x = scale_y = float(scale)
        if scale_x <= 0 or scale_y <= 0:
            raise ValueError(f"Hệ số co giãn (scale) phải lớn hơn 0, nhận được: scale_x={scale_x}, scale_y={scale_y}")

        img = image.copy()
        if rotate != 0:
            img = img.rotate(-rotate, expand=True)
        if scale_x != 1.0 or scale_y != 1.0:
            new_size = (max(1, int(round(img.width * scale_x))), max(1, int(round(img.height * scale_y))))
            img = img.resize(new_size, resample=Image.Resampling.LANCZOS)
        if img.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        if img.mode != "1":
            img = img.convert("L").point(lambda p: 255 if p > 128 else 0, mode="1")

        canvas = Image.new("1", (self.canvas_width_px, self.canvas_height_px), 1)  # 1 = Trắng
        shift_x_px = int(round(shift_x_mm * self.dpi / 25.4))
        shift_y_px = int(round(shift_y_mm * self.dpi / 25.4))
        if auto_center:
            pos_x = (self.canvas_width_px - img.width) // 2 + shift_x_px
            pos_y = (self.canvas_height_px - img.height) // 2 + shift_y_px
        else:
            pos_x, pos_y = shift_x_px, shift_y_px
        canvas.paste(img, (pos_x, pos_y))
        self.pages.append(self._encode_page(canvas))
        return self

    # --- Mã hóa thuộc tính PCL XL (binding little-endian) ---
    @staticmethod
    def _ubyte(value: int, attr_id: int) -> bytes:
        return bytes([0xC0, value, 0xF8, attr_id])

    @staticmethod
    def _uint16(value: int, attr_id: int) -> bytes:
        return b"\xc1" + struct.pack("<H", value) + bytes([0xF8, attr_id])

    @staticmethod
    def _uint16_xy(x: int, y: int, attr_id: int) -> bytes:
        return b"\xd1" + struct.pack("<HH", x, y) + bytes([0xF8, attr_id])

    @staticmethod
    def _real32_xy(x: float, y: float, attr_id: int) -> bytes:
        return b"\xd5" + struct.pack("<ff", x, y) + bytes([0xF8, attr_id])

    def _encode_page(self, canvas: Any) -> bytes:
        """Mã hóa một trang: BeginPage (CustomMediaSize mm) + toàn bộ khung trang dạng ảnh xám 1-bit."""
        width, height = canvas.width, canvas.height
        b = bytearray()
        # BeginPage: Orientation=ePortrait, MediaSource=eDefaultSource, CustomMediaSize (mm), eMillimeter
        b += self._ubyte(0, 0x28) + self._ubyte(0, 0x26)
        b += self._real32_xy(self.width_mm, self.height_mm, 0x2F) + self._ubyte(1, 0x30) + b"\x43"
        # SetColorSpace eGray
        b += self._ubyte(1, 0x03) + b"\x6a"
        # SetCursor (0, 0)
        b += self._uint16_xy(0, 0, 0x4C) + b"\x6b"
        # BeginImage: eDirectPixel, e1Bit, SourceWidth, SourceHeight, DestinationSize
        b += self._ubyte(0, 0x64) + self._ubyte(0, 0x62) + self._uint16(width, 0x6C)
        b += self._uint16(height, 0x6B) + self._uint16_xy(width, height, 0x67) + b"\xb0"
        # ReadImage: mỗi dòng đệm byte trắng (0xFF) tới biên 4 byte; 0 = đen, 1 = trắng (khớp PIL '1')
        stride = (width + 7) // 8
        padded = (stride + 3) // 4 * 4
        raw = canvas.tobytes()
        pad = b"\xff" * (padded - stride)
        data = b"".join(raw[r * stride:(r + 1) * stride] + pad for r in range(height))
        b += self._uint16(0, 0x6D) + self._uint16(height, 0x63) + self._ubyte(0, 0x65) + b"\xb1"
        b += b"\xfa" + struct.pack("<I", len(data)) + data
        b += b"\xb2"  # EndImage
        b += self._uint16(1, 0x31) + b"\x44"  # EndPage PageCopies=1
        return bytes(b)

    def _pjl_header(self) -> bytes:
        lines = [f'@PJL JOB NAME = "{self.job_name}"']
        if self.tray:
            lines.append(f"@PJL SET MEDIASOURCE = {self.tray}")
        lines.append("@PJL ENTER LANGUAGE = PCLXL")
        return self.UEL + b"@PJL\r\n" + "".join(line + "\r\n" for line in lines).encode("latin1")

    def _pjl_footer(self) -> bytes:
        return self.UEL + f'@PJL EOJ NAME = "{self.job_name}"\r\n'.encode("latin1") + self.UEL

    def build(self) -> bytes:
        """Biên dịch tác vụ in (PJL + PCL XL) thành bytes; thuần logic, không I/O."""
        if not self.pages:
            raise ValueError("Chưa có trang nào để in. Hãy gọi add_page() trước khi build().")
        stream = bytearray(b") HP-PCL XL;2;0;Comment core_kit PCLXLRasterBuilder\n")
        # BeginSession: UnitsPerMeasure=(dpi, dpi), Measure=eInch, ErrorReport=eErrorPage
        stream += self._uint16_xy(self.dpi, self.dpi, 0x89) + self._ubyte(0, 0x86) + self._ubyte(2, 0x8F) + b"\x41"
        # OpenDataSource: SourceType=eDefaultDataSource, DataOrg=eBinaryLowByteFirst
        stream += self._ubyte(0, 0x88) + self._ubyte(1, 0x82) + b"\x48"
        stream += b"".join(self.pages)
        stream += b"\x49\x42"  # CloseDataSource, EndSession
        return self._pjl_header() + bytes(stream) + self._pjl_footer()


from core_kit.devices.printer_raw import (
    PrinterStatus,
    RawSocketPrinter,
    PJLStatusProbe,
    SocketTransport,
)


class PCLNetworkPrinter(RawSocketPrinter):
    """
    [DEPRECATED] Lớp giao tiếp máy in mạng PCL cũ.
    Vui lòng sử dụng 'RawSocketPrinter' từ 'core_kit.devices' cho các dự án mới.
    """

    def __init__(
        self,
        host: str,
        port: int = 9100,
        timeout: float = 5.0,
        transport: Optional[SocketTransport] = None,
    ):
        warnings.warn(
            "PCLNetworkPrinter đã lỗi thời và sẽ bị loại bỏ trong phiên bản tương lai. "
            "Vui lòng chuyển sang sử dụng 'RawSocketPrinter'.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(host=host, port=port, timeout=timeout, transport=transport)

    def send(self, payload: bytes, verify_ready: bool = False) -> bool:
        """Gửi luồng byte dữ liệu in (PCL/PJL) tới máy in."""
        return super().send(payload=payload, verify_ready=verify_ready, probe=PJLStatusProbe())

    def get_status(self) -> PrinterStatus:
        """Truy vấn thông tin trạng thái phần cứng của máy in qua lệnh @PJL INFO STATUS."""
        return super().get_status(probe=PJLStatusProbe())

