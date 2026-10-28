from typing import List, Optional


class TSPLBuilder:
    """
    Trình dựng lệnh điều khiển máy in tem nhãn theo chuẩn TSPL (TSC Printer Language).
    Hỗ trợ sinh mã lệnh in văn bản, mã vạch (Barcode 128), mã DataMatrix/QR Code.
    """

    def __init__(self, width_mm: float = 80, height_mm: float = 50):
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.commands: List[str] = []
        self.reset()

    def reset(self) -> "TSPLBuilder":
        """Khởi tạo lại buffer lệnh với kích thước nhãn và xóa dữ liệu đệm cũ."""
        self.commands = [
            f"SIZE {self.width_mm} mm, {self.height_mm} mm",
            "GAP 3 mm, 0 mm",
            "DIRECTION 1",
            "CLS"
        ]
        return self

    def text(
        self,
        x: int,
        y: int,
        content: str,
        font: str = "TSS24.BF2",
        x_multi: int = 1,
        y_multi: int = 1
    ) -> "TSPLBuilder":
        """In chuỗi văn bản tại tọa độ (x, y) với kích thước phóng to."""
        escaped_content = content.replace('"', '\\"')
        self.commands.append(f'TEXT {x},{y},"{font}",0,{x_multi},{y_multi},"{escaped_content}"')
        return self

    def barcode(
        self,
        x: int,
        y: int,
        code: str,
        code_type: str = "128",
        height: int = 60,
        readable: int = 1
    ) -> "TSPLBuilder":
        """In mã vạch 1D (mặc định Code 128) với chiều cao và có hiển thị số đọc hay không."""
        self.commands.append(f'BARCODE {x},{y},"{code_type}",{height},{readable},0,2,2,"{code}"')
        return self

    def dmatrix(self, x: int, y: int, content: str, size: int = 6) -> "TSPLBuilder":
        """In mã ma trận 2D DataMatrix."""
        escaped_content = content.replace('"', '\\"')
        self.commands.append(f'DMATRIX {x},{y},{size},{size},"{escaped_content}"')
        return self

    def qrcode(self, x: int, y: int, content: str, cell_width: int = 4) -> "TSPLBuilder":
        """In mã ma trận 2D QR Code."""
        escaped_content = content.replace('"', '\\"')
        self.commands.append(f'QRCODE {x},{y},H,{cell_width},A,0,"{escaped_content}"')
        return self

    def line(self, x: int, y: int, width: int, height: int) -> "TSPLBuilder":
        """Vẽ đường kẻ / khối đặc (BAR)."""
        self.commands.append(f"BAR {x},{y},{width},{height}")
        return self

    def print(self, copies: int = 1) -> str:
        """Kết thúc và sinh toàn bộ chuỗi lệnh TSPL để gửi tới máy in."""
        self.commands.append(f"PRINT {copies},1")
        return "\r\n".join(self.commands) + "\r\n"


from core_kit.devices.printer_raw import RawSocketPrinter, SocketTransport
import warnings


class TSPLNetworkPrinter(RawSocketPrinter):
    """
    [DEPRECATED] Gửi lệnh TSPL trực tiếp đến máy in qua mạng LAN/TCP Socket.
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
            "TSPLNetworkPrinter đã lỗi thời và sẽ bị loại bỏ trong phiên bản tương lai. "
            "Vui lòng chuyển sang sử dụng 'RawSocketPrinter'.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(host=host, port=port, timeout=timeout, transport=transport)

    def send_raw(self, tspl_data: str, encoding: str = "utf-8") -> bool:
        """Gửi chuỗi lệnh TSPL tới máy in qua socket."""
        return super().send(payload=tspl_data, encoding=encoding, verify_ready=False)

