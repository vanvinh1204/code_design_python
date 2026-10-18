"""
Module điều khiển máy in laser mạng qua chuẩn PCL 5 Raster và Printer Job Language (PJL).
Cung cấp khả năng in trực tiếp qua RAW TCP Socket (cổng 9100) mà không cần cài đặt driver OS.
"""

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union


@dataclass
class PrinterStatus:
    """Trạng thái thiết bị máy in từ truy vấn PJL INFO STATUS."""
    is_online: bool = False
    is_ready: bool = False
    display: str = ""
    raw: str = ""

    @classmethod
    def from_raw(cls, raw_status: str) -> "PrinterStatus":
        """Phân tích chuỗi phản hồi thô từ lệnh @PJL INFO STATUS."""
        raise NotImplementedError


class PCL5RasterBuilder:
    """
    Trình dựng lệnh và đồ họa raster PCL 5 kèm header/footer PJL.
    Hỗ trợ cả kích thước trang tiêu chuẩn (A4, Letter) và kích thước tùy chỉnh (Custom mm).
    Tự động chuẩn hóa ảnh (xoay, co giãn tránh lề cơ khí, căn giữa, dịch chuyển mm).
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
        scale: float = 0.94,
        shift_x_mm: float = 0.0,
        shift_y_mm: float = 0.0,
        auto_center: bool = True,
    ) -> "PCL5RasterBuilder":
        """
        Nạp một trang ảnh vào tác vụ in PCL 5.

        Args:
            image: Đối tượng PIL.Image.Image, đường dẫn file (str/Path) hoặc dữ liệu bytes ảnh.
            rotate: Góc xoay theo chiều kim đồng hồ (0, 90, 180, 270).
            scale: Hệ số tỷ lệ co giãn (mặc định 0.94 để bù trừ lề chết cơ khí 3.5mm của máy in).
            shift_x_mm: Độ dịch chuyển ngang theo mm (dương = sang phải, âm = sang trái).
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

        if scale <= 0:
            raise ValueError(f"Hệ số co giãn (scale) phải lớn hơn 0, nhận được: {scale}")

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
        if scale != 1.0:
            new_w = max(1, int(round(img.width * scale)))
            new_h = max(1, int(round(img.height * scale)))
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
        # Lệnh khởi tạo PCL và bắt đầu Raster Graphics tại lề trái
        page_buffer.extend(b"\x1bE")
        page_buffer.extend(f"\x1b*t{self.dpi}R".encode("latin1"))
        page_buffer.extend(b"\x1b*r1A")

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

        # Kết thúc đồ họa raster, đẩy trang (Form Feed) và Reset PCL
        page_buffer.extend(b"\x1b*rB")
        page_buffer.extend(b"\x0c")
        page_buffer.extend(b"\x1bE")

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

        if self.paper_size == "CUSTOM":
            width_decipoints = int(round(self.width_mm * 720.0 / 25.4))
            height_decipoints = int(round(self.height_mm * 720.0 / 25.4))
            header_lines.append("@PJL SET PAPER = CUSTOM")
            header_lines.append(f"@PJL SET PAPERWIDTH = {width_decipoints}")
            header_lines.append(f"@PJL SET PAPERLENGTH = {height_decipoints}")
        else:
            header_lines.append(f"@PJL SET PAPER = {self.paper_size}")

        if self.tray:
            header_lines.append(f"@PJL SET MEDIASOURCE = {self.tray}")

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


class PCLNetworkPrinter:
    """Giao tiếp máy in mạng qua RAW TCP Socket."""
    pass
