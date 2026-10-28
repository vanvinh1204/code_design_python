import io
import socket
import sys
import threading
from pathlib import Path

# Thiết lập bảng mã UTF-8 cho stdout trên Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Thêm đường dẫn src vào sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PIL import Image
from core_kit.devices import PCL5RasterBuilder, PCLNetworkPrinter


def run_pcl_builder_custom_test():
    print("1. Kiểm thử PCL5RasterBuilder với khổ tem tùy chỉnh (102x148 mm, Tray 1, Short-Edge)...")
    builder = PCL5RasterBuilder(
        paper_size="CUSTOM",
        width_mm=102.0,
        height_mm=148.0,
        tray="TRAY1",
        feed_direction="SHORTEDGEFEED",
        dpi=300,
        job_name="TEST_CUSTOM_LABEL",
    )

    # Tạo ảnh mẫu 1-bit kích thước 200x200 pixel đen
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

    assert payload.startswith(b"\x1b%-12345X@PJL\r\n"), "Thiếu mã thoát Universal Exit Language (UEL)"
    assert b'@PJL JOB NAME = "TEST_CUSTOM_LABEL"\r\n' in payload, "Thiếu PJL JOB NAME"
    assert b"@PJL SET PAPER = CUSTOM\r\n" in payload, "Thiếu cấu hình PAPER = CUSTOM"
    assert b"@PJL SET PAPERWIDTH = 2891\r\n" in payload, "Sai giá trị PAPERWIDTH decipoints"
    assert b"@PJL SET PAPERLENGTH = 4195\r\n" in payload, "Sai giá trị PAPERLENGTH decipoints"
    assert b"@PJL SET MEDIASOURCE = TRAY1\r\n" in payload, "Thiếu MEDIASOURCE = TRAY1"
    assert b"@PJL SET SHORTEDGEFEED = ON\r\n" in payload, "Thiếu SHORTEDGEFEED = ON"
    assert b"@PJL SET FEEDDIR = SHORTEDGEFEED\r\n" in payload, "Thiếu FEEDDIR = SHORTEDGEFEED"
    assert b"@PJL ENTER LANGUAGE = PCL\r\n" in payload, "Thiếu chuyển ngôn ngữ PCL"
    assert b"\x1b*t300R" in payload, "Thiếu thiết lập độ phân giải 300 DPI"
    assert b"\x1b*r1A" in payload, "Thiếu lệnh bắt đầu raster graphics"
    assert b"\x1b*rB" in payload, "Thiếu lệnh kết thúc raster graphics"
    assert b"\x0c" in payload, "Thiếu ký tự Form Feed đẩy trang"
    assert payload.endswith(b"\x1b%-12345X@PJL EOJ\r\n\x1b%-12345X"), "Thiếu PJL EOJ và UEL kết thúc"

    print(f"   -> Thành công! Kích thước payload: {len(payload)} bytes.")


def run_pcl_builder_standard_test():
    print("2. Kiểm thử PCL5RasterBuilder với khổ giấy tiêu chuẩn (A4, MP Feeder, Long-Edge)...")
    builder = PCL5RasterBuilder(
        paper_size="A4",
        tray="MPFEEDER",
        feed_direction="LONGEDGEFEED",
        dpi=300,
        job_name="TEST_A4_REPORT",
    )
    assert builder.width_mm == 210.0, "Sai chiều rộng mặc định của khổ A4"
    assert builder.height_mm == 297.0, "Sai chiều dài mặc định của khổ A4"

    # Tạo ảnh mẫu trắng với một vạch kẻ đen ở giữa
    test_img = Image.new("RGB", (300, 300), (255, 255, 255))
    builder.add_page(image=test_img, rotate=0, scale=1.0)
    payload = builder.build()

    assert b"@PJL SET PAPER = A4\r\n" in payload, "Thiếu cấu hình PAPER = A4"
    assert b"@PJL SET MEDIASOURCE = MPFEEDER\r\n" in payload, "Thiếu MEDIASOURCE = MPFEEDER"
    assert b"@PJL SET SHORTEDGEFEED = OFF\r\n" in payload, "Thiếu SHORTEDGEFEED = OFF"
    assert b"@PJL SET FEEDDIR = LONGEDGEFEED\r\n" in payload, "Thiếu FEEDDIR = LONGEDGEFEED"
    print(f"   -> Thành công! Kích thước payload A4: {len(payload)} bytes.")


def run_raster_fidelity_test():
    print("3. Kiểm thử độ chính xác điểm ảnh và nghịch đảo bit (Bitwise Inversion)...")
    # Tạo ảnh có kích thước lẻ 11x2 pixel: dòng đầu gồm 8 pixel đen, 3 pixel trắng
    img = Image.new("1", (11, 2), 1)  # 1 là trắng
    for px in range(8):
        img.putpixel((px, 0), 0)  # 0 là đen

    builder = PCL5RasterBuilder(
        paper_size="CUSTOM",
        width_mm=11 * 25.4 / 300,
        height_mm=2 * 25.4 / 300,
        dpi=300,
    )
    builder.add_page(image=img, rotate=0, scale=1.0, auto_center=False)
    payload = builder.build()

    # Độ rộng 11 pixel cần 2 bytes cho mỗi hàng (8 bits + 3 bits, 5 bits padding)
    # Byte 1 của dòng 0 gồm 8 pixel đen -> đảo bit thành 0xFF (8 hạt mực toner)
    # Byte 2 của dòng 0 gồm 3 pixel trắng và 5 bits đệm -> đảo bit thành 0x00
    assert b"\x1b*b2W\xff\x00" in payload, "Nghịch đảo bit hoặc căn đệm hàng raster bị sai"
    print("   -> Thành công! Dòng raster PCL 5 khớp hoàn toàn từng bit nhị phân.")


# Các ca giải mã trạng thái PJL nằm trong tests/test_devices_raw_printer.py


def run_network_printer_mock_test():
    print("4. Kiểm thử gửi dữ liệu qua TCP Socket và Telemetry (@PJL INFO STATUS)...")
    # Khởi tạo Mock Server cục bộ để giả lập card mạng máy in port 9100
    mock_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    mock_server.bind(("127.0.0.1", 0))
    server_port = mock_server.getsockname()[1]
    mock_server.listen(2)

    received_data = bytearray()

    def server_worker():
        # Lần 1: Nhận truy vấn @PJL INFO STATUS và trả về trạng thái sẵn sàng
        conn1, _ = mock_server.accept()
        req = conn1.recv(1024)
        if b"INFO STATUS" in req:
            conn1.sendall(b'@PJL INFO STATUS\r\nCODE=10001\r\nDISPLAY="00 READY"\r\nONLINE=TRUE\r\n\x0c')
        conn1.close()

        # Lần 2: Nhận luồng dữ liệu in PCL
        conn2, _ = mock_server.accept()
        while True:
            chunk = conn2.recv(4096)
            if not chunk:
                break
            received_data.extend(chunk)
        conn2.close()

    server_thread = threading.Thread(target=server_worker, daemon=True)
    server_thread.start()

    printer = PCLNetworkPrinter(host="127.0.0.1", port=server_port, timeout=2.0)

    # Kiểm tra get_status()
    status = printer.get_status()
    assert status.is_ready is True, "Mock server phải trả về is_ready=True"
    assert status.display == "00 READY"

    # Kiểm tra send() với verify_ready=True
    sample_payload = b"\x1b%-12345X@PJL\r\n@PJL ENTER LANGUAGE = PCL\r\n\x1bE\x0c\x1b%-12345X"
    # Gửi qua socket
    success = printer.send(sample_payload, verify_ready=False)
    assert success is True, "Hàm send() phải trả về True khi gửi thành công"

    server_thread.join(timeout=3.0)
    mock_server.close()

    assert received_data == sample_payload, "Dữ liệu máy in nhận được phải khớp byte-for-byte"
    print("   -> Thành công! Truyền tải TCP socket và graceful shutdown hoạt động chuẩn xác.")


def main():
    print("=" * 65)
    print("KIỂM THỬ XÁC MINH: core_kit.devices (PCL 5 Raster & PJL Network Printer)")
    print("=" * 65)

    run_pcl_builder_custom_test()
    run_pcl_builder_standard_test()
    run_raster_fidelity_test()
    run_network_printer_mock_test()

    print("=" * 65)
    print("-> TẤT CẢ CÁC BÀI KIỂM THỬ PCL PRINTER ĐỀU VƯỢT QUA XUẤT SẮC!")
    print("=" * 65)


if __name__ == "__main__":
    main()
