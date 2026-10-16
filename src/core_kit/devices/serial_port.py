import threading
from typing import Callable, Optional


class SerialScannerReader:
    """
    Quản lý luồng lắng nghe dữ liệu từ máy quét mã vạch qua cổng Serial/COM port.
    Thích hợp chạy nền trong PySide6 desktop app để nhận barcode khi công nhân quét.
    """

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._serial = None

    def start_listening(self, on_barcode_scanned: Callable[[str], None]):
        """Khởi động luồng đọc nền từ cổng COM và gọi callback khi có mã vạch mới."""
        import serial

        if self._running:
            return

        self._running = True
        self._serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)

        def _worker():
            buffer = ""
            while self._running and self._serial and self._serial.is_open:
                try:
                    line = self._serial.readline()
                    if line:
                        decoded = line.decode("utf-8", errors="ignore").strip()
                        if decoded:
                            on_barcode_scanned(decoded)
                except Exception:
                    break

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()

    def stop_listening(self):
        """Dừng luồng lắng nghe và giải phóng cổng COM."""
        self._running = False
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
