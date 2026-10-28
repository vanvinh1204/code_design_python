"""
Module vận chuyển in ấn RAW Socket (RAW Socket Printing Transport) qua chuẩn TCP cổng 9100.
Che giấu toàn bộ chi tiết socket, timeout, graceful shutdown và cung cấp Seam kiểm thử in-memory.
"""

import re
import socket
import logging
import warnings
from dataclasses import dataclass
from typing import Optional, Protocol, Tuple, Union, runtime_checkable

logger = logging.getLogger(__name__)


class PrinterConnectionError(Exception):
    """
    Lỗi không thiết lập được kết nối hoặc truy vấn tới máy in (timeout, bị từ chối kết nối...).
    Transport ném lỗi này thay vì trả về chuỗi lỗi để không bị nhầm là phản hồi của máy in.
    """


@dataclass
class PrinterStatus:
    """
    Trạng thái thiết bị máy in từ truy vấn phần cứng.
    """
    is_online: bool = False
    is_ready: bool = False
    display: str = ""
    code: Optional[int] = None
    raw: str = ""

    @classmethod
    def offline(cls, reason: str) -> "PrinterStatus":
        """Tạo trạng thái Printer Offline: không kết nối được máy in, lý do nằm trong display."""
        return cls(is_online=False, is_ready=False, display=reason)

    @classmethod
    def from_raw(cls, raw_status: str) -> "PrinterStatus":
        """
        [DEPRECATED] Phân tích chuỗi phản hồi thô từ lệnh trạng thái.
        Vui lòng sử dụng 'PJLStatusProbe().parse_response(raw)'.
        """
        warnings.warn(
            "PrinterStatus.from_raw đã lỗi thời và sẽ bị loại bỏ trong phiên bản tương lai. "
            "Vui lòng chuyển sang sử dụng 'PJLStatusProbe().parse_response'.",
            DeprecationWarning,
            stacklevel=2,
        )
        return PJLStatusProbe().parse_response(raw_status)


@runtime_checkable
class StatusProbe(Protocol):
    """Giao thức thăm dò trạng thái phần cứng máy in."""
    query_bytes: bytes

    def parse_response(self, raw_response: str) -> PrinterStatus:
        ...


class PJLStatusProbe:
    """Đầu dò trạng thái máy in laser chuẩn PJL (@PJL INFO STATUS)."""
    query_bytes: bytes = b"\x1b%-12345X@PJL\r\n@PJL INFO STATUS\r\n\x1b%-12345X"

    def parse_response(self, raw_response: str) -> PrinterStatus:
        """Phân tích chuỗi phản hồi thô của lệnh @PJL INFO STATUS thành PrinterStatus."""
        raw_text = raw_response.strip() if raw_response else ""
        if not raw_text:
            return PrinterStatus(is_online=False, is_ready=False, display="Unknown", raw="")

        code: Optional[int] = None
        code_match = re.search(r"\bCODE\s*=\s*(\d+)", raw_text, re.IGNORECASE)
        if code_match:
            try:
                code = int(code_match.group(1))
            except ValueError:
                code = None

        display: str = ""
        disp_match = re.search(r'\bDISPLAY\s*=\s*"([^"]*)"', raw_text, re.IGNORECASE)
        if not disp_match:
            disp_match = re.search(r'\bDISPLAY\s*=\s*([^\r\n]+)', raw_text, re.IGNORECASE)

        if disp_match:
            display = disp_match.group(1).strip()
        elif "@PJL" not in raw_text.upper():
            display = raw_text

        is_online: bool = True
        online_match = re.search(r'\bONLINE\s*=\s*([A-Za-z0-9]+)', raw_text, re.IGNORECASE)
        if not online_match:
            online_match = re.search(r'\bSTA\s*=\s*([A-Za-z0-9]+)', raw_text, re.IGNORECASE)

        if online_match:
            val = online_match.group(1).upper()
            is_online = val in ("TRUE", "ON", "1")
        elif "OFFLINE" in raw_text.upper():
            is_online = False

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
            is_ready = True

        return PrinterStatus(
            is_online=is_online,
            is_ready=is_ready,
            display=display,
            code=code,
            raw=raw_response,
        )


@runtime_checkable
class SocketTransport(Protocol):
    """Giao thức trừu tượng hóa kết nối socket mạng tại Seam kiểm thử."""
    def send(self, host: str, port: int, payload: bytes, timeout: float) -> bool:
        ...

    def query(self, host: str, port: int, query_payload: bytes, timeout: float) -> str:
        """Gửi lệnh truy vấn và trả về phản hồi đã giải mã; ném PrinterConnectionError nếu không kết nối được."""
        ...


class TcpSocketAdapter:
    """Adapter socket mạng TCP thật kết nối qua cổng 9100."""
    def send(self, host: str, port: int, payload: bytes, timeout: float) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout) as sock:
                sock.sendall(payload)
                # Graceful teardown: đóng chiều ghi để máy in đẩy trang in
                try:
                    sock.shutdown(socket.SHUT_WR)
                except Exception:
                    pass
            return True
        except Exception as exc:
            logger.error(f"[SOCKET_ERROR] Không thể gửi dữ liệu tới {host}:{port}: {exc}")
            return False

    def query(self, host: str, port: int, query_payload: bytes, timeout: float) -> str:
        response_chunks: list[bytes] = []
        try:
            with socket.create_connection((host, port), timeout=timeout) as sock:
                sock.sendall(query_payload)
                sock.settimeout(timeout)
                while True:
                    try:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        response_chunks.append(chunk)
                        if b"\x0c" in chunk or b"\x1b%-12345X" in chunk:
                            break
                    except socket.timeout:
                        break
            return b"".join(response_chunks).decode("latin1", errors="replace")
        except Exception as exc:
            logger.warning(f"[SOCKET_WARN] Truy vấn trạng thái {host}:{port} thất bại: {exc}")
            raise PrinterConnectionError(f"Không kết nối được máy in {host}:{port}: {exc}") from exc


class FakeSocketTransport:
    """Adapter giả lập trong bộ nhớ phục vụ unit test không cần kết nối mạng."""
    def __init__(
        self,
        should_fail: bool = False,
        simulated_query_response: str = "",
    ):
        self.should_fail = should_fail
        self.simulated_query_response = simulated_query_response
        self.sent_payloads: list[bytes] = []
        self.last_destination: Optional[Tuple[str, int]] = None

    def send(self, host: str, port: int, payload: bytes, timeout: float) -> bool:
        if self.should_fail:
            return False
        self.last_destination = (host, port)
        self.sent_payloads.append(payload)
        return True

    def query(self, host: str, port: int, query_payload: bytes, timeout: float) -> str:
        if self.should_fail:
            raise PrinterConnectionError(f"Không kết nối được máy in {host}:{port}: Simulated Failure")
        self.last_destination = (host, port)
        return self.simulated_query_response


class RawSocketPrinter:
    """
    Module sâu điều khiển giao tiếp máy in mạng qua RAW TCP Socket (cổng 9100).
    Hỗ trợ mọi định dạng payload in (PCL 5, TSPL, ESC/POS, ZPL) và cho phép hoán đổi Seam test.
    """

    def __init__(
        self,
        host: str,
        port: int = 9100,
        timeout: float = 5.0,
        transport: Optional[SocketTransport] = None,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.transport: SocketTransport = transport if transport is not None else TcpSocketAdapter()

    def send(
        self,
        payload: Union[bytes, str],
        encoding: str = "utf-8",
        verify_ready: bool = False,
        probe: Optional[StatusProbe] = None,
    ) -> bool:
        """
        Gửi dữ liệu in tới máy in mạng.

        Args:
            payload: Luồng byte nhị phân hoặc chuỗi lệnh text.
            encoding: Bảng mã dùng để encode nếu payload là str (mặc định utf-8).
            verify_ready: Nếu True, kiểm tra trạng thái máy in trước khi gửi.
            probe: Đầu dò trạng thái sử dụng khi verify_ready=True.
        """
        if verify_ready:
            active_probe = probe if probe is not None else PJLStatusProbe()
            status = self.get_status(probe=active_probe)
            if not status.is_ready:
                logger.warning(f"[PRINT_ABORT] Máy in {self.host}:{self.port} chưa sẵn sàng: {status.display}")
                return False

        if isinstance(payload, str):
            payload_bytes = payload.encode(encoding)
        else:
            payload_bytes = bytes(payload)

        return self.transport.send(self.host, self.port, payload_bytes, self.timeout)

    def get_status(self, probe: Optional[StatusProbe] = None) -> PrinterStatus:
        """
        Truy vấn trạng thái thiết bị máy in qua đầu dò chỉ định.
        Không bao giờ ném lỗi khi mất kết nối: trả về trạng thái Printer Offline kèm lý do.
        """
        active_probe = probe if probe is not None else PJLStatusProbe()
        try:
            raw_response = self.transport.query(self.host, self.port, active_probe.query_bytes, self.timeout)
        except PrinterConnectionError as exc:
            return PrinterStatus.offline(str(exc))
        return active_probe.parse_response(raw_response)
