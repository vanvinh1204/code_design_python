"""
Module điều khiển máy in laser mạng qua chuẩn PCL 5 Raster và Printer Job Language (PJL).
Cung cấp khả năng in trực tiếp qua RAW TCP Socket (cổng 9100) mà không cần cài đặt driver OS.
"""

import io
import re
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union


@dataclass
class PrinterStatus:
    """
    Trạng thái thiết bị máy in từ truy vấn PJL INFO STATUS.
    """
    is_online: bool = False
    is_ready: bool = False
    display: str = ""
    code: Optional[int] = None
    raw: str = ""

    @classmethod
    def from_raw(cls, raw_status: str) -> "PrinterStatus":
        """
        Phân tích chuỗi phản hồi thô từ lệnh @PJL INFO STATUS hoặc chuỗi trạng thái ngắn.

        Hỗ trợ:
        - Chuỗi đầy đủ theo chuẩn PJL: CODE=10001, DISPLAY="00 READY", ONLINE=TRUE
        - Chuỗi trạng thái ngắn trực tiếp: "Ready", "Paper Jam", "Load Tray 1"
        """
        raw_text = raw_status.strip() if raw_status else ""
        if not raw_text:
            return cls(is_online=False, is_ready=False, display="Unknown", raw="")

        code: Optional[int] = None
        code_match = re.search(r"\bCODE\s*=\s*(\d+)", raw_text, re.IGNORECASE)
        if code_match:
            try:
                code = int(code_match.group(1))
            except ValueError:
                code = None

        # Trích xuất DISPLAY
        display: str = ""
        disp_match = re.search(r'\bDISPLAY\s*=\s*"([^"]*)"', raw_text, re.IGNORECASE)
        if not disp_match:
            disp_match = re.search(r'\bDISPLAY\s*=\s*([^\r\n]+)', raw_text, re.IGNORECASE)

        if disp_match:
            display = disp_match.group(1).strip()
        elif "@PJL" not in raw_text.upper():
            # Nếu không có từ khóa PJL, chuỗi đầu vào chính là chuỗi thông điệp trực tiếp
            display = raw_text

        # Xác định ONLINE
        is_online: bool = True
        online_match = re.search(r'\bONLINE\s*=\s*([A-Za-z0-9]+)', raw_text, re.IGNORECASE)
        if not online_match:
            online_match = re.search(r'\bSTA\s*=\s*([A-Za-z0-9]+)', raw_text, re.IGNORECASE)

        if online_match:
            val = online_match.group(1).upper()
            is_online = val in ("TRUE", "ON", "1")
        elif "OFFLINE" in raw_text.upper():
            is_online = False

        # Xác định tính sẵn sàng (is_ready)
        # Các từ khóa thể hiện máy in đang bận, kẹt giấy, hết giấy hoặc mở cửa
        unready_keywords = [
            "JAM",
            "DOOR OPEN",
            "COVER OPEN",
            "LOAD",
            "EMPTY",
            "OUT OF PAPER",
            "OFFLINE",
            "ERROR",
            "WARMING UP",
            "BUSY",
            "PAUSED",
            "FAULT",
        ]
        display_upper = display.upper()
        raw_upper = raw_text.upper()

        has_error = any(kw in display_upper or kw in raw_upper for kw in unready_keywords)

        if not is_online:
            is_ready = False
        elif has_error:
            is_ready = False
        elif any(ready_kw in display_upper for ready_kw in ("READY", "IDLE", "SLEEP", "STANDBY")):
            is_ready = True
        else:
            # Nếu trực tuyến và không phát hiện lỗi nào
            is_ready = True

        return cls(
            is_online=is_online,
            is_ready=is_ready,
            display=display,
            code=code,
            raw=raw_status,
        )


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


class PCLNetworkPrinter:
    """
    Giao tiếp máy in mạng qua RAW TCP Socket (cổng 9100).
    Cung cấp khả năng truy vấn trạng thái phần cứng máy in và gửi luồng dữ liệu in PCL.
    """

    def __init__(self, host: str, port: int = 9100, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def get_status(self) -> PrinterStatus:
        """
        Truy vấn thông tin trạng thái phần cứng của máy in qua lệnh @PJL INFO STATUS.
        Trả về đối tượng PrinterStatus chứa thông tin trực tuyến, sẵn sàng và thông điệp LCD.
        """
        query = b"\x1b%-12345X@PJL\r\n@PJL INFO STATUS\r\n\x1b%-12345X"
        response_chunks: list[bytes] = []

        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.sendall(query)
                sock.settimeout(self.timeout)
                while True:
                    try:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        response_chunks.append(chunk)
                        # Dấu hiệu hoàn tất phản hồi PJL (ký tự FormFeed 0x0c hoặc UEL)
                        if b"\x0c" in chunk or b"\x1b%-12345X" in chunk:
                            break
                    except socket.timeout:
                        break

            raw_text = b"".join(response_chunks).decode("latin1", errors="replace")
            return PrinterStatus.from_raw(raw_text)
        except Exception as exc:
            return PrinterStatus(
                is_online=False,
                is_ready=False,
                display=f"Connection Error: {exc}",
                raw=str(exc),
            )

    def send(self, payload: bytes, verify_ready: bool = False) -> bool:
        """
        Gửi luồng byte dữ liệu in (PCL/PJL) tới máy in qua socket mạng.

        Args:
            payload: Chuỗi bytes dữ liệu in (tạo từ PCL5RasterBuilder.build()).
            verify_ready: Nếu True, kiểm tra trạng thái máy in (is_ready) trước khi gửi.

        Returns:
            True nếu gửi thành công và socket được đóng nhẹ nhàng (graceful teardown),
            False nếu máy in không sẵn sàng hoặc xảy ra lỗi kết nối mạng.
        """
        if verify_ready:
            status = self.get_status()
            if not status.is_ready:
                return False

        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.sendall(payload)
                # Graceful socket shutdown: thông báo cho máy in đã hoàn tất truyền dữ liệu ghi
                try:
                    sock.shutdown(socket.SHUT_WR)
                except Exception:
                    pass
            return True
        except Exception:
            return False
